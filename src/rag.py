from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Tu es un assistant qui répond à partir de documents fournis.

Utilise uniquement les informations présentes dans les sources.
Si les sources ne permettent pas de répondre, indique que l'information n'a pas été trouvée.
Indique le nom du fichier et le numéro de page utilisés.
Réponds en français de manière claire et concise.
""".strip()
        ),
        (
            "human",
            """
Question :
{question}

Sources :
{context}
""".strip()
        )
    ]
)


def rag_answer(question: str, retriever, api_key: str):

    retrieved_documents = retriever.invoke(question)

    context_parts = []

    for document in retrieved_documents:

        file_name = document.metadata.get("file_name")
        page_number = document.metadata.get("page")

        context_parts.append(
            f"[Source: {file_name}, page {page_number}]\n"
            f"{document.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    llm = ChatOpenAI(
        model="gpt-5-mini",
        api_key=api_key
    )

    chain = prompt_template | llm

    response = chain.invoke(
        {
            "question": question,
            "context": context
        }
    )

    return response.content