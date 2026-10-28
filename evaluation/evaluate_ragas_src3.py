# Version src3 de evaluate_ragas.py : mêmes métriques, sur les réponses de src3

import os
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from datasets import Dataset

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness

########################################################
# Changement d'environnement : venveval
########################################################


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dataset à évaluer : "dataset", "dataset_mots_pdf" ou "dataset_simple"
DATASET_NAME = "dataset"

INPUT_PATH = PROJECT_ROOT / "evaluation" / "results" / f"rag_outputs_src3_{DATASET_NAME}.csv"
OUTPUT_PATH = PROJECT_ROOT / "evaluation" / "results" / f"ragas_scores_src3_{DATASET_NAME}.csv"


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY manquante.")

    # Charger les résultats déjà générés par le RAG
    df = pd.read_csv(INPUT_PATH)

    # Reconvertir les contextes JSON en listes Python
    df["retrieved_contexts"] = df["retrieved_contexts"].apply(json.loads)

    # Préparer le format attendu par RAGAS 0.2.15
    dataset = Dataset.from_dict({
        "question": df["question"].tolist(),
        "answer": df["response"].tolist(),
        "contexts": df["retrieved_contexts"].tolist(),
        "ground_truth": df["reference"].tolist(),
    })

    # Modèles utilisés pour juger les réponses
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) # gpt-4o-mini pour compatibilité avec ragas
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            # Compare la réponse du RAG à la réponse de référence
            answer_correctness,
        ],
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=True,
    )

    # Convertir les résultats en DataFrame Pandas
    scores_df = results.to_pandas()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    scores_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig"
    )


    print(f"\nRésultats enregistrés : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
