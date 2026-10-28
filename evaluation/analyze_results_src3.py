# Version src3 de analyze_results.py

from pathlib import Path
import pandas as pd

# Dataset à analyser : "dataset", "dataset_mots_pdf" ou "dataset_simple"
DATASET_NAME = "dataset"

RESULTS_PATH = (
    Path(__file__).resolve().parent
    / "results"
    / f"ragas_scores_src3_{DATASET_NAME}.csv"
)

df = pd.read_csv(RESULTS_PATH)

print("Colonnes disponibles :", df.columns.tolist())
print("Nombre de questions :", len(df))

metrics = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
]

print("\nScores moyens :")
print(df[metrics].mean().round(3))

print("\nScores minimums :")
print(df[metrics].min().round(3))

# Si la question n'est pas présente dans le CSV RAGAS,
# on la récupère dans rag_outputs.csv.
if "question" not in df.columns:
    outputs_path = RESULTS_PATH.parent / f"rag_outputs_src3_{DATASET_NAME}.csv"
    outputs_df = pd.read_csv(outputs_path)

    if len(df) != len(outputs_df):
        raise ValueError(
            "Les deux fichiers n'ont pas le même nombre de lignes."
        )

    df["question"] = outputs_df["question"].values

print("\n5 questions avec la fidélité la plus faible :")
print(
    df[
        ["question", "faithfulness", "answer_relevancy"]
    ]
    .sort_values("faithfulness")
    .head(5)
    .to_string(index=False)
)

print("\n5 questions avec la pertinence la plus faible :")
print(
    df[
        ["question", "answer_relevancy", "context_recall"]
    ]
    .sort_values("answer_relevancy")
    .head(5)
    .to_string(index=False)
)


print("\n5 questions avec la justesse la plus faible :")
print(
    df[
        ["question", "answer_correctness", "context_recall"]
    ]
    .sort_values("answer_correctness")
    .head(5)
    .to_string(index=False)
)


print("\nDétail des 5 réponses les moins justes :")

worst = df.nsmallest(5, "answer_correctness")

for _, row in worst.iterrows():
    print("\n" + "=" * 70)
    print("QUESTION :", row["user_input"])
    print("RÉFÉRENCE :", row["reference"])
    print("RÉPONSE RAG :", row["response"])
    print("FAITHFULNESS :", row["faithfulness"])
    print("ANSWER RELEVANCY :", row["answer_relevancy"])
    print("CONTEXT RECALL :", row["context_recall"])
    print("ANSWER CORRECTNESS :", row["answer_correctness"])




# Faithfulness -> Fidélité aux sources
# Answer Relevancy -> Pertinence des réponses
# Context Precision -> Pertinence du retrieval
# Context Recall -> Couverture des informations
# Answer Correctness -> Justesse de la réponse par rapport à la référence
