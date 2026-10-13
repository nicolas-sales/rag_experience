import streamlit as st
from openai import OpenAI

import sys
from pathlib import Path

# Permet d'importer les modules du dossier src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import create_retriever
from src.rag import rag_answer
from src.pdf_viewer import prepare_pdf_source
from src.source_locator import get_source_bboxes


# --------------------------------------------------
# Configuration Streamlit
# --------------------------------------------------

st.set_page_config(
    page_title="Assistant RAG Davidson",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Assistant RAG Davidson")
st.caption("Posez vos questions sur le document stratégique.")


# --------------------------------------------------
# Sidebar : clé API OpenAI
# --------------------------------------------------

with st.sidebar:

    st.header("⚙️ Configuration")

    api_key = st.text_input(
        "Clé API OpenAI",
        type="password",
        placeholder="sk-..."
    )

    if st.button("Valider la clé", use_container_width=True):

        if not api_key:
            st.error("Veuillez saisir une clé API.")

        else:
            try:
                client = OpenAI(api_key=api_key)

                # Vérifie que la clé fonctionne
                client.models.list()

                # Si la clé change, on libère l'ancien retriever
                if st.session_state.get("openai_api_key") != api_key:
                    st.session_state.pop("retriever", None)

                st.session_state["openai_api_key"] = api_key

                st.success("Clé API validée.")

            except Exception:
                st.session_state.pop("openai_api_key", None)
                st.error(
                    "Impossible de valider la clé API. "
                    "Vérifiez votre clé et votre accès à l'API."
                )

    if "openai_api_key" in st.session_state:
        st.success("Clé OpenAI configurée")


# --------------------------------------------------
# Vérification de la clé API
# --------------------------------------------------

if "openai_api_key" not in st.session_state:

    st.info(
        "Veuillez renseigner et valider votre clé OpenAI "
        "dans le menu de gauche pour utiliser l'assistant."
    )

    st.stop()


# --------------------------------------------------
# Chargement du retriever Qdrant
# --------------------------------------------------

try:

    if "retriever" not in st.session_state:

        with st.spinner("Connexion à Qdrant..."):

            st.session_state["retriever"] = create_retriever(
                st.session_state["openai_api_key"]
            )

    retriever = st.session_state["retriever"]

    st.sidebar.success("Qdrant connecté")

except Exception as e:

    st.error(f"Erreur de connexion à Qdrant : {e}")
    st.stop()


# --------------------------------------------------
# Initialisation de l'historique
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state["messages"] = []


# --------------------------------------------------
# Fonction : afficher les sources PDF
# --------------------------------------------------

def display_pdf_sources(source_links: list):

    for source in source_links:

        pdf_url = source["url"]
        page_number = source["page"]

        st.markdown(
            f'<a href="{pdf_url}" target="_blank" '
            f'rel="noopener noreferrer">'
            f'📄 Voir la source — page {page_number} ↗'
            f'</a>',
            unsafe_allow_html=True
        )


# --------------------------------------------------
# Historique de conversation
# --------------------------------------------------

st.subheader("💬 Discussion avec le document")

for index, message in enumerate(st.session_state["messages"]):

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message["role"] == "assistant":

            source_links = message.get("source_links", [])

            display_pdf_sources(source_links)


# --------------------------------------------------
# Champ de saisie
# --------------------------------------------------

question = st.chat_input(
    "Posez votre question sur le document..."
)


# --------------------------------------------------
# Traitement d'une nouvelle question
# --------------------------------------------------

if question:

    # Enregistrer la question
    st.session_state["messages"].append({
        "role": "user",
        "content": question
    })

    # Afficher la question
    with st.chat_message("user"):
        st.markdown(question)

    try:

        with st.spinner("Recherche et génération de la réponse..."):

            # 1. Une seule recherche Qdrant, effectuée
            #    directement dans rag_answer()
            #
            #    GPT retourne :
            #    - la réponse
            #    - les pages sources
            #    - les identifiants des éléments

            result = rag_answer(
                question=question,
                retriever=retriever,
                api_key=st.session_state["openai_api_key"]
            )

            answer = result["answer"]
            sources = result["sources"]

            print("=== SOURCES IDENTIFIÉES ===")
            print(sources)

            # 2. Regrouper les éléments par page
            sources_by_page = {}

            for source in sources:

                page_number = source["page"]
                element_id = source["element_id"]

                sources_by_page.setdefault(
                    page_number, []
                ).append(element_id)

            # 3. Récupérer les bbox et créer les PDF annotés
            source_links = []

            for page_number, element_ids in sources_by_page.items():

                bboxes = get_source_bboxes(
                    page_number=page_number,
                    element_ids=element_ids
                )

                print("Page source :", page_number)
                print("BBOX sélectionnées :", bboxes)

                if not bboxes:
                    continue

                source_url = prepare_pdf_source(
                    page_number=page_number,
                    bboxes=bboxes
                )

                source_links.append({
                    "page": page_number,
                    "url": source_url
                })

        # 4. Enregistrer la réponse et ses liens PDF
        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "source_links": source_links
        })

        # 5. Afficher la réponse
        with st.chat_message("assistant"):

            st.markdown(answer)

            display_pdf_sources(source_links)

    except Exception as e:
        st.error(f"Erreur lors de la génération : {e}")