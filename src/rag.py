import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

from src.source_locator import get_page_elements


prompt_template = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content="""
Tu es un assistant qui répond à partir de documents PDF.

Tu reçois une question, des pages retrouvées par Qdrant
et les éléments individuels de ces pages.

Règles :
- Utilise uniquement les informations présentes dans les sources.
- Si les sources ne permettent pas de répondre, indique-le.
- Réponds en français de manière claire et concise.
- Indique le nom du fichier et le numéro de page.
- Sélectionne les éléments qui justifient réellement ta réponse.
- Pour les données numériques, vérifie la valeur et l'année.
- Pour une synthèse, sélectionne plusieurs éléments si nécessaire.
- Ne sélectionne pas un titre seul lorsque la preuve est ailleurs.
- N'invente jamais d'identifiant d'élément.
- Si aucun élément ne justifie la réponse, retourne une liste vide.

Réponds uniquement avec un objet JSON :

{
    "answer": "Réponse en français",
    "sources": [
        {
            "page": 14,
            "element_id": 3
        }
    ]
}
""".strip()
        ),
        (
            "human",
            """
Question :
{question}

Pages retrouvées :
{context}

Éléments disponibles :
{elements_context}
""".strip()
        )
    ]
)


def rag_answer(question: str, retriever, api_key: str):

    # Une seule recherche Qdrant
    retrieved_documents = retriever.invoke(question)

    context_parts = []
    elements_parts = []

    # Pour vérifier les identifiants retournés par GPT
    valid_element_ids = {}

    for document in retrieved_documents:

        file_name = document.metadata.get("file_name")
        page_number = document.metadata.get("page")

        if page_number is None:
            continue

        page_number = int(page_number)

        context_parts.append(
            f"[Source: {file_name}, page {page_number}]\n"
            f"{document.page_content}"
        )

        # Éléments extraits de cette page
        page_elements = get_page_elements(page_number)

        valid_element_ids[page_number] = {
            element["element_id"]
            for element in page_elements
        }

        elements_parts.append(
            json.dumps(
                {
                    "file_name": file_name,
                    "page": page_number,
                    "elements": page_elements
                },
                ensure_ascii=False
            )
        )

    context = "\n\n---\n\n".join(context_parts)
    elements_context = "\n\n".join(elements_parts)

    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=api_key
    )

    # On demande une réponse JSON
    chain = prompt_template | llm.bind(
        response_format={"type": "json_object"}
    )

    response = chain.invoke(
        {
            "question": question,
            "context": context,
            "elements_context": elements_context
        }
    )

    result = json.loads(response.content)

    answer = result.get("answer", "")
    proposed_sources = result.get("sources", [])

    verified_sources = []
    seen = set()

    for source in proposed_sources:

        if not isinstance(source, dict):
            continue

        try:
            page_number = int(source["page"])
            element_id = int(source["element_id"])

        except (KeyError, TypeError, ValueError):
            continue

        if element_id not in valid_element_ids.get(page_number, set()):
            continue

        source_key = (page_number, element_id)

        if source_key in seen:
            continue

        seen.add(source_key)

        verified_sources.append({
            "page": page_number,
            "element_id": element_id
        })

    return {
        "answer": answer,
        "sources": verified_sources
    }
        