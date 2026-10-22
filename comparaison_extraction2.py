import pymupdf
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "test_pdf.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extraction_classique_test.md"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with pymupdf.open(PDF_PATH) as doc:
    page = doc[0]

    # 1. Extraire les tableaux
    tables = page.find_tables()
    elements = []

    for table in tables.tables:
        rows = table.extract()

        if not rows:
            continue

        # Conversion en tableau Markdown
        markdown_table = ""

        for i, row in enumerate(rows):
            cells = [str(cell or "").replace("|", "\\|") for cell in row]
            markdown_table += "| " + " | ".join(cells) + " |\n"

            if i == 0:
                markdown_table += "| " + " | ".join(["---"] * len(cells)) + " |\n"

        elements.append((table.bbox[1], table.bbox[0], markdown_table))

    # 2. Extraire les blocs de texte
    blocks = page.get_text("blocks", sort=True)

    for block in blocks:
        bbox = pymupdf.Rect(block[:4])
        texte = block[4].strip()

        if not texte:
            continue

        # Ignorer les blocs appartenant aux tableaux
        if any(bbox.intersects(pymupdf.Rect(t.bbox)) for t in tables.tables):
            continue

        elements.append((bbox.y0, bbox.x0, texte))

        print(f"BBOX : {tuple(bbox)}")
        print(texte)
        print("-" * 50)

    # 3. Trier les éléments verticalement et horizontalement
    elements.sort(key=lambda e: (e[0], e[1]))

    # 4. Générer le Markdown
    contenu = "# Page 1 — Extraction PyMuPDF\n\n"
    contenu += "\n\n".join(element[2] for element in elements)

    OUTPUT_PATH.write_text(contenu, encoding="utf-8")

print(f"Nombre de tableaux détectés : {len(tables.tables)}")
print(f"Fichier créé : {OUTPUT_PATH}")