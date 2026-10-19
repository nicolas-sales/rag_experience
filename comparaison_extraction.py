
import pymupdf
from pathlib import Path

# Racine du projet rag_pdf
PROJECT_ROOT = Path(__file__).resolve().parent

# Chemin vers le PDF
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "Plan_stratégique_Impact.pdf"

# Fichier de sortie
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extraction_classique_page16.md"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Extraction classique de la page 16
with pymupdf.open(PDF_PATH) as doc:
    page = doc[15]  # La page 16 correspond à l'index 15

    texte = page.get_text("text", sort=True)

    OUTPUT_PATH.write_text(
        "# Page 16 — Extraction classique PyMuPDF\n\n" + texte,
        encoding="utf-8"
    )

print(f"Fichier créé : {OUTPUT_PATH}")
