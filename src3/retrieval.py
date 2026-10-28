from pathlib import Path

from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Base séparée de celle de src (data/qdrant_db)
QDRANT_PATH = PROJECT_ROOT / "data" / "qdrant_db_src3"

COLLECTION_NAME = "pdf_pages_src3"


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
        # 4 pages au lieu de 2 : la bonne page arrive souvent 3e
        search_kwargs={"k": 4}
    )

    return retriever