"""
Comparaison OCR / DePlot / hybride sur les graphiques du PDF.

Pour chaque graphique :
    1. on lit le graphique avec l'OCR (EasyOCR, sur CPU), en version simple
       et en version "positions" (chaque chiffre associé à l'année sous lui)
    2. on récupère la sortie DePlot (déjà calculée par src2/ingestion.py)
    3. on pose une question dont on connaît la réponse au LLM,
       avec le texte de la page + OCR, + DePlot, ou + les deux
"""

import json
from pathlib import Path

import easyocr
import pymupdf
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parent

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "Plan_stratégique_Impact.pdf"
SOURCE_ELEMENTS_PATH = PROJECT_ROOT / "data" / "processed" / "src2" / "source_elements_v3.json"
PAGES_MARKDOWN_PATH = PROJECT_ROOT / "data" / "processed" / "src2" / "pages_markdown.md"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "comparaison_ocr_deplot.md"

# (page, numéro du graphique dans la page, question, bonne réponse lue sur l'image)
TESTS = [
    (14, 1, "Quel est le stock actif de missions ODD en 2023 ?", "122"),
    (14, 2, "Quel est le CA annuel associé aux missions ODD en 2024, en k€ ?", "25 183"),
    (14, 0, "Combien de nouvelles missions ODD au total en 2024 ?", "87"),
    (14, 0, "Combien de nouvelles missions (C2 ; M2) en 2023 ?", "24 (lu sur la courbe, pas écrit)"),
    (45, 0, "Quelles étaient les émissions Scope 1 et 2 en 2023 ?", "936 tCO2e"),
    (45, 1, "Quelles étaient les émissions du Scope 3 en 2024 ?", "6 476 tCO2e"),
    (5, 1, "Quelle part de l'activité représente l'offre Networks ?", "non indiqué (aucun chiffre sur l'image)"),
]

PROMPT = """Réponds à la question uniquement à partir du contexte ci-dessous.
Si l'information n'est pas dans le contexte, réponds "non trouvé".
Réponds en une phrase courte, avec le chiffre.

Contexte :
{context}

Question : {question}"""


# --------------------------------------------------
# Récupération des graphiques, de l'OCR et de DePlot
# --------------------------------------------------

def get_charts(page_number):
    """Images de la page analysées par DePlot (dans l'ordre du JSON)."""
    source_elements = json.loads(SOURCE_ELEMENTS_PATH.read_text(encoding="utf-8"))
    return [
        element
        for element in source_elements[str(page_number)]
        if element["type"] == "image" and element.get("deplot_clean")
    ]


def get_page_text(page_number):
    """Texte de la page (markdown de src2), sans les références d'images."""
    markdown = PAGES_MARKDOWN_PATH.read_text(encoding="utf-8")
    page_text = markdown.split(f"# Page {page_number}\n")[1].split("\n---\n")[0]
    return "\n".join(line for line in page_text.splitlines() if not line.startswith("!["))


def run_ocr(reader, doc, page_number, bbox):
    """OCR de la zone du graphique. Chaque texte lu garde sa position."""
    image = doc[page_number - 1].get_pixmap(clip=pymupdf.Rect(bbox), dpi=150).tobytes("png")

    texts = []
    for corners, text, _ in reader.readtext(image):
        xs = [point[0] for point in corners]
        ys = [point[1] for point in corners]
        texts.append({"text": text, "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)})

    return texts


def ocr_as_text(texts):
    """Version simple : les textes à la suite, de haut en bas (positions perdues)."""
    texts = sorted(texts, key=lambda t: (round(t["y0"] / 15), t["x0"]))
    return " | ".join(t["text"] for t in texts)


def is_number(text):
    return any(c.isdigit() for c in text) and all(c.isdigit() or c in " .,%" for c in text)


def ocr_with_positions(texts):
    """
    Version avec positions : un chiffre est associé au texte le plus bas
    placé sous lui, à la même position horizontale (l'année sous la barre).
    """
    lines = []
    paired = set()

    for value in texts:

        if not is_number(value["text"]):
            continue

        center = (value["x0"] + value["x1"]) / 2

        # Textes situés en dessous du chiffre, dans la même colonne
        below = [
            t for t in texts
            if t is not value
            and t["y0"] > value["y1"]
            and t["x0"] - 10 <= center <= t["x1"] + 10
        ]

        if below:
            label = max(below, key=lambda t: t["y0"])  # le plus bas : l'axe
            lines.append(f"{label['text']} : {value['text']}")
            paired.add(id(value))
            paired.add(id(label))

    others = [t["text"] for t in texts if id(t) not in paired]
    if others:
        lines.append("Autres textes : " + " | ".join(others))

    return "\n".join(lines)


def clean_deplot(text):
    # DePlot sépare ses lignes par "<0x0A>"
    return text.replace("<0x0A>", "\n").strip()


# --------------------------------------------------

def main():
    load_dotenv(PROJECT_ROOT / ".env")
    llm = ChatOpenAI(model="gpt-5-mini")
    reader = easyocr.Reader(["fr", "en"], gpu=False)

    report = ["# Comparaison OCR / DePlot / hybride\n"]
    summary = [
        "| Page | Question | Bonne réponse | OCR | OCR + positions | DePlot | Hybride |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    details = []

    with pymupdf.open(PDF_PATH) as doc:
        for page_number, chart_index, question, expected in TESTS:

            chart = get_charts(page_number)[chart_index]
            page_text = get_page_text(page_number)
            ocr_texts = run_ocr(reader, doc, page_number, chart["bbox"])
            ocr_text = ocr_as_text(ocr_texts)
            ocr_positions = ocr_with_positions(ocr_texts)
            deplot_text = clean_deplot(chart["deplot_clean"])

            contexts = {
                "OCR": f"{page_text}\n\nTexte lu dans le graphique (OCR) :\n{ocr_text}",
                "OCR + positions": f"{page_text}\n\nTexte lu dans le graphique (OCR) :\n{ocr_positions}",
                "DePlot": f"{page_text}\n\nDonnées du graphique (DePlot) :\n{deplot_text}",
                "Hybride": (
                    f"{page_text}\n\nTexte lu dans le graphique (OCR) :\n{ocr_text}"
                    f"\n\nDonnées du graphique (DePlot) :\n{deplot_text}"
                ),
            }

            answers = {}
            for name, context in contexts.items():
                response = llm.invoke(PROMPT.format(context=context, question=question))
                answers[name] = response.content.strip().replace("\n", " ")

            print(f"\nPage {page_number} — {question}  (attendu : {expected})")
            for name, answer in answers.items():
                print(f"  {name:16}: {answer}")

            summary.append(
                f"| {page_number} | {question} | {expected} | {answers['OCR']} | {answers['OCR + positions']} "
                f"| {answers['DePlot']} | {answers['Hybride']} |"
            )
            details.append(
                f"## Page {page_number} — {question}\n\n"
                f"**OCR :**\n\n```text\n{ocr_text}\n```\n\n"
                f"**OCR + positions :**\n\n```text\n{ocr_positions}\n```\n\n"
                f"**DePlot :**\n\n```text\n{deplot_text}\n```\n"
            )

    report += ["## Résultats\n", "\n".join(summary), "\n## Sorties brutes\n"] + details
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"\nFichier créé : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
