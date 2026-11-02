
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

# Base séparée de celle de src (data/qdrant_db)
QDRANT_PATH = PROJECT_ROOT / "data" / "qdrant_db_src3"

COLLECTION_NAME = "pdf_pages_src3"

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


def check_one_chunk_per_page(chunks):
    """
    Vérifie que chaque PDF a exactement 1 chunk par page :
    pages 1 à N, sans doublon ni trou.
    """
    pages_per_file = {}

    for chunk in chunks:
        file_name = chunk["metadata"]["file_name"]
        pages_per_file.setdefault(file_name, []).append(chunk["metadata"]["page"])

    for file_name, pages in pages_per_file.items():

        if sorted(pages) != list(range(1, len(pages) + 1)):
            raise ValueError(
                f"{file_name} : pages en double, manquantes ou invalides."
            )

        print(f"{file_name} : {len(pages)} pages")


def index_chunks(chunks, vector_store):

    check_one_chunk_per_page(chunks)

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
        PROJECT_ROOT / "data" / "processed" / "src3" / "chunks.json"
    )

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print("Chunks chargés :", len(chunks))

    vector_store = create_vector_store(api_key)

    try:
        index_chunks(
            chunks=chunks,
            vector_store=vector_store
        )
    finally:
        vector_store.client.close()


if __name__ == "__main__":
    main()