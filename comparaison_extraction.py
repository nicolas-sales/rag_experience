
import pymupdf
from pathlib import Path

# Racine du projet rag_pdf
PROJECT_ROOT = Path(__file__).resolve().parent

# Chemin vers le PDF
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "test_pdf.pdf"

# Fichier de sortie
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extraction_classique_test.md"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Extraction classique 
with pymupdf.open(PDF_PATH) as doc:
    page = doc[0] # Première page du PDF

    texte = page.get_text("text", sort=True)

    OUTPUT_PATH.write_text(
        "# Page 1 — Extraction classique PyMuPDF\n\n" + texte,
        encoding="utf-8"
    )

    blocks = page.get_text("blocks", sort=True)

    for block in blocks:
        x0, y0, x1, y1 = block[:4]
        texte = block[4]

        print(f"BBOX : ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
        print(texte)
        print("-" * 50)

print(f"Fichier créé : {OUTPUT_PATH}")

