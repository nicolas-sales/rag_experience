
import os
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.retrieval import create_retriever
from src.rag import rag_answer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "evaluation" / "dataset.csv"
RESULTS_PATH = PROJECT_ROOT / "evaluation" / "results" / "rag_outputs.csv"


def main():

    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante.")

    df = pd.read_csv(DATASET_PATH)

    required_columns = {"question", "reference", "reference_pages"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Colonnes manquantes dans dataset.csv")

    # Adapter ce nom si la fonction de retrieval est différente
    retriever = create_retriever(api_key)

    results = []

    try:
        for index, row in df.iterrows():

            question = str(row["question"])

            print(f"\nQuestion {index + 1}/{len(df)} : {question}")

            result = rag_answer(
                question=question,
                retriever=retriever,
                api_key=api_key
            )

            results.append({
                "question": question,
                "reference": row["reference"],
                "reference_pages": row["reference_pages"],
                "response": result["answer"],
                "retrieved_contexts": json.dumps(
                    result["retrieved_contexts"],
                    ensure_ascii=False
                ),
                "retrieved_pages": json.dumps(
                    result["retrieved_pages"]
                )
            })

    finally:
        # Fermer Qdrant local si le retriever expose son client
        vector_store = getattr(retriever, "vectorstore", None)
        client = getattr(vector_store, "client", None)

        if client is not None:
            client.close()

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    results_df = pd.DataFrame(results)

    results_df.to_csv(
        RESULTS_PATH,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"\nRésultats enregistrés : {RESULTS_PATH}")


if __name__ == "__main__":
    main()
