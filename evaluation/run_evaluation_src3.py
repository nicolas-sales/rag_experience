# Version src3 de run_evaluation.py : même script, pipeline src3 (OCR des graphiques et logos)

import os
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src3.retrieval import create_retriever
from src3.rag import rag_answer


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dataset à évaluer : "dataset", "dataset_mots_pdf" ou "dataset_simple"
DATASET_NAME = "dataset"

DATASET_PATH = PROJECT_ROOT / "evaluation" / f"{DATASET_NAME}.csv"
RESULTS_PATH = PROJECT_ROOT / "evaluation" / "results" / f"rag_outputs_src3_{DATASET_NAME}.csv"


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante.")

    df = pd.read_csv(DATASET_PATH)

    required_columns = {"question", "reference", "reference_pages"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Colonnes manquantes dans dataset.csv")

    retriever = create_retriever(api_key)

    results = []

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