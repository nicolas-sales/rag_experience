
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
from src.source_locator import find_relevant_bbox


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
# Fonction : afficher une source PDF
# --------------------------------------------------

def display_pdf_source(pdf_url: str, page_number: int):
    
    st.markdown(
        f'<a href="{pdf_url}" target="_blank" rel="noopener noreferrer">'
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

            source_url = message.get("source_url")
            source_page = message.get("source_page")

            if source_url and source_page is not None:
                display_pdf_source(source_url, source_page)


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

            # 1. Recherche Qdrant
            retrieved_documents = retriever.invoke(question)

            source_page = None
            source_url = None

            if retrieved_documents:

                # 2. Page la plus pertinente
                source_page = retrieved_documents[0].metadata.get("page")

                if source_page is not None:

                    # 3. Identification automatique de la zone pertinente
                    bbox = find_relevant_bbox(
                        question=question,
                        page_number=source_page,
                        api_key=st.session_state["openai_api_key"]
                    )

                    print("Page source :", source_page)
                    print("BBOX sélectionnée :", bbox)

                    # 4. Génération du PDF annoté
                    source_url = prepare_pdf_source(
                        page_number=source_page,
                        bbox=bbox
                    )

            # 5. Génération de la réponse GPT-5-mini
            answer = rag_answer(
                question=question,
                retriever=retriever,
                api_key=st.session_state["openai_api_key"]
            )

        # 6. Enregistrer la réponse et son lien PDF
        st.session_state["messages"].append({
            "role": "assistant",
            "content": answer,
            "source_page": source_page,
            "source_url": source_url
        })

        # 7. Afficher la réponse
        with st.chat_message("assistant"):

            st.markdown(answer)

            if source_url is not None:
                display_pdf_source(source_url, source_page)

    except Exception as e:
        st.error(f"Erreur lors de la génération : {e}")
