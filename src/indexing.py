
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
import os
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent

QDRANT_PATH = PROJECT_ROOT / "notebooks" / "qdrant_db"

COLLECTION_NAME = "pdf_pages_v3"

EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_SIZE = 1536


def create_vector_store(api_key: str):

    embedding_model = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key
    )

    qdrant_client = QdrantClient(
        path=str(QDRANT_PATH)
    )

    if not qdrant_client.collection_exists(COLLECTION_NAME):

        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_SIZE,
                distance=Distance.COSINE
            )
        )

        print(f"Collection créée : {COLLECTION_NAME}")

    else:

        print(f"Collection existante : {COLLECTION_NAME}")

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embedding_model
    )

    return vector_store


def index_chunks(chunks, vector_store, total_pages):

    pages = [
        chunk["metadata"]["page"]
        for chunk in chunks
    ]

    # Vérifier : un chunk par page
    if len(chunks) != total_pages:
        raise ValueError(
            f"{total_pages} chunks attendus, "
            f"{len(chunks)} reçus."
        )

    # Vérifier qu'aucune page n'est en double
    if len(set(pages)) != len(pages):
        raise ValueError(
            "Certaines pages sont présentes plusieurs fois."
        )

    # Vérifier que toutes les pages sont présentes
    if set(pages) != set(range(1, total_pages + 1)):
        raise ValueError(
            "Certaines pages sont manquantes ou invalides."
        )

    # Éviter les indexations répétées
    existing_points = vector_store.client.count(
        collection_name=COLLECTION_NAME,
        exact=True
    ).count

    if existing_points > 0:
        raise RuntimeError(
            f"La collection contient déjà "
            f"{existing_points} points. "
            "Indexation annulée pour éviter les doublons."
        )

    documents = [
        Document(
            page_content=chunk["page_content"],
            metadata=chunk["metadata"]
        )
        for chunk in chunks
    ]

    vector_store.add_documents(documents=documents)

    print(f"{len(documents)} documents indexés.")


def inspect_collection():

    client = QdrantClient(path=str(QDRANT_PATH))

    try:
        collections = client.get_collections().collections

        for collection in collections:
            print("Collection trouvée :", collection.name)

            count = client.count(
                collection_name=collection.name,
                exact=True
            ).count

            print("Nombre de points :", count)

    finally:
        client.close()


def main():

    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante.")

    chunks_path = (
        PROJECT_ROOT / "data" / "processed" / "chunks.json"
    )

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print("Chunks chargés :", len(chunks))

    total_pages = len(chunks)

    vector_store = create_vector_store(api_key)

    try:
        index_chunks(
            chunks=chunks,
            vector_store=vector_store,
            total_pages=total_pages
        )
    finally:
        vector_store.client.close()


if __name__ == "__main__":
    main()