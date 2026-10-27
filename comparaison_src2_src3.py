"""
Comparaison src2 (DePlot seul) / src3 (OCR + positions + DePlot) / src3 sans DePlot (OCR seul).

Pour chaque question dont on connaît la réponse :
    - contexte = le markdown de la page (1 chunk par page, comme dans le RAG)
    - on pose la question au LLM avec chaque markdown
    - chaque question est posée plusieurs fois (le LLM varie d'une fois à l'autre)
"""

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED = PROJECT_ROOT / "data" / "processed"

MARKDOWNS = {
    "src2": PROCESSED / "src2" / "pages_markdown.md",
    "src3": PROCESSED / "src3" / "pages_markdown.md",
    "src3 sans DePlot": PROCESSED / "src3" / "pages_markdown_sans_deplot.md",
}
OUTPUT_PATH = PROCESSED / "comparaison_src2_src3.md"

RUNS = 3

# (page, question, bonne réponse, texte attendu dans la réponse)
TESTS = [
    (14, "Quel est le stock actif de missions ODD en 2023 ?", "122", "122"),
    (14, "Quel est le CA annuel associé aux missions ODD en 2024, en k€ ?", "25 183", "25183"),
    (14, "Combien de nouvelles missions ODD au total en 2024 ?", "87", "87"),
    (14, "Combien de nouvelles missions (C2 ; M2) en 2023 ?", "24 (lu sur la courbe, pas écrit)", "24"),
    (45, "Quelles étaient les émissions Scope 1 et 2 en 2023 ?", "936 tCO2e", "936"),
    (45, "Quelles étaient les émissions du Scope 3 en 2024 ?", "6 476 tCO2e", "6476"),
    (5, "Quelle part de l'activité représente l'offre Networks ?", "non indiqué", "non trouvé"),
]

PROMPT = """Réponds à la question uniquement à partir du contexte ci-dessous.
Si l'information n'est pas dans le contexte, réponds "non trouvé".
Réponds en une phrase courte, avec le chiffre.

Contexte :
{context}

Question : {question}"""


def write_markdown_without_deplot():
    """Markdown de src3 sans les tableaux DePlot : il ne reste que l'OCR."""
    # Bloc DePlot = la ligne "Valeurs estimées...", une ligne vide, puis
    # son tableau. Le bloc s'arrête à la première ligne vide après le
    # tableau (un tableau PyMuPDF peut suivre juste après, on le garde).
    kept = []
    in_deplot = False
    in_table = False

    for line in MARKDOWNS["src3"].read_text(encoding="utf-8").split("\n"):
        if line.startswith("Valeurs estimées par DePlot"):
            in_deplot, in_table = True, False
        elif in_deplot and line.startswith("|"):
            in_table = True
        elif in_deplot and not line and not in_table:
            pass                                   # ligne vide avant le tableau
        elif in_deplot and not line:
            in_deplot = False                      # fin du tableau DePlot
        else:
            in_deplot = False
            kept.append(line)

    MARKDOWNS["src3 sans DePlot"].write_text("\n".join(kept), encoding="utf-8")


def get_page(markdown_path, page_number):
    markdown = markdown_path.read_text(encoding="utf-8")
    return markdown.split(f"# Page {page_number}\n")[1].split("\n---\n")[0]


def is_correct(answer, expected):
    # On enlève les espaces ("25 183" = "25183") et les majuscules
    clean = answer.lower().replace(" ", "").replace(" ", "").replace("\xa0", "")
    return expected.lower().replace(" ", "") in clean


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    llm = ChatOpenAI(model="gpt-5-mini")
    write_markdown_without_deplot()

    scores = {name: 0 for name in MARKDOWNS}
    summary = [
        "| Page | Question | Bonne réponse | " + " | ".join(f"{name} (sur {RUNS})" for name in MARKDOWNS) + " |",
        "| --- | --- | --- |" + " --- |" * len(MARKDOWNS),
    ]
    details = []

    for page_number, question, expected, expected_text in TESTS:

        results = {}

        for name, markdown_path in MARKDOWNS.items():
            context = get_page(markdown_path, page_number)
            answers = [
                llm.invoke(PROMPT.format(context=context, question=question)).content.strip().replace("\n", " ")
                for _ in range(RUNS)
            ]
            correct = sum(is_correct(answer, expected_text) for answer in answers)
            scores[name] += correct
            results[name] = (correct, answers)

        print(f"\nPage {page_number} — {question} (attendu : {expected})")
        for name, (correct, answers) in results.items():
            print(f"  {name} : {correct}/{RUNS}  {answers}")

        summary.append(
            f"| {page_number} | {question} | {expected} | "
            + " | ".join(f"{correct}/{RUNS}" for correct, _ in results.values()) + " |"
        )
        details.append(f"## Page {page_number} — {question}\n\nBonne réponse : {expected}\n")
        for name, (correct, answers) in results.items():
            details.append(f"**{name}** ({correct}/{RUNS}) :\n")
            details += [f"- {answer}" for answer in answers]
            details.append("")

    total = len(TESTS) * RUNS
    summary.append("| | **Total** | | " + " | ".join(f"**{score}/{total}**" for score in scores.values()) + " |")

    report = ["# Comparaison src2 / src3 / src3 sans DePlot\n", "## Résultats\n", "\n".join(summary), "\n## Réponses\n"] + details
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"\nFichier créé : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
