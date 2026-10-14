from pathlib import Path

from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parent.parent

QDRANT_PATH = PROJECT_ROOT / "notebooks" / "qdrant_db"

COLLECTION_NAME = "pdf_pages_v3"


def create_retriever(api_key: str):

    embedding_model = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        api_key=api_key
    )

    qdrant_client = QdrantClient(
        path=str(QDRANT_PATH)
    )

    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=COLLECTION_NAME,
        embedding=embedding_model
    )

    retriever = vector_store.as_retriever(
        search_kwargs={"k": 2}
    )

    return retriever