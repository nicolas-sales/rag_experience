import pymupdf
from pathlib import Path
import math

PROJECT_ROOT = Path(__file__).resolve().parent

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "test_pdf.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extraction_visuelle.md"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def table_to_text(rows):
    """Convertit un tableau PDF en tableau avec des |."""
    if not rows:
        return ""

    rows = [
        [str(cell or "").replace("\n", " ") for cell in row]
        for row in rows
    ]

    nb_cols = max(len(row) for row in rows)

    for row in rows:
        row.extend([""] * (nb_cols - len(row)))

    widths = [
        max(len(row[i]) for row in rows)
        for i in range(nb_cols)
    ]

    def format_row(row):
        cells = [
            row[i].ljust(widths[i])
            for i in range(nb_cols)
        ]
        return "| " + " | ".join(cells) + " |"

    lines = [format_row(rows[0])]

    # Séparateur Markdown après l'en-tête
    lines.append(
        "| " + " | ".join("-" * max(3, w) for w in widths) + " |"
    )

    for row in rows[1:]:
        lines.append(format_row(row))

    return "\n".join(lines)


def overlaps_table(bbox, table_bboxes):
    rect = pymupdf.Rect(bbox)

    for table_bbox in table_bboxes:
        intersection = rect & pymupdf.Rect(table_bbox)

        if intersection.is_empty:
            continue

        area = rect.width * rect.height

        if area > 0:
            overlap = intersection.width * intersection.height

            if overlap / area > 0.5:
                return True

    return False


def extract_elements(page):
    elements = []
    table_bboxes = []

    # Extraction des tableaux
    tables = page.find_tables()

    for table in tables.tables:
        bbox = tuple(table.bbox)
        table_bboxes.append(bbox)

        rows = table.extract()

        if rows:
            elements.append({
                "type": "table",
                "bbox": bbox,
                "content": table_to_text(rows),
            })

    # Extraction des paragraphes
    for block in page.get_text("blocks"):
        if len(block) < 7 or block[6] != 0:
            continue

        bbox = tuple(block[:4])
        content = block[4].strip()

        if not content:
            continue

        if overlaps_table(bbox, table_bboxes):
            continue

        elements.append({
            "type": "text",
            "bbox": bbox,
            "content": content,
        })

    return elements


def build_visual_markdown(page, elements, page_number):
    """
    Place les blocs sur une grille monospace.
    Les coordonnées sont calculées automatiquement depuis les bbox.
    """

    # Taille d'une cellule de la grille, en points PDF
    char_width = 3.5
    line_height = 10

    grid_width = math.ceil(page.rect.width / char_width) + 2
    grid_height = math.ceil(page.rect.height / line_height) + 2

    grid = [[" "] * grid_width for _ in range(grid_height)]

    # On positionne les blocs selon leur bbox
    for element in elements:
        x0, y0, x1, y1 = element["bbox"]

        start_col = round(x0 / char_width)
        start_row = round(y0 / line_height)

        lines = element["content"].splitlines()

        for i, line in enumerate(lines):
            row = start_row + i

            if row >= grid_height:
                break

            for j, char in enumerate(line):
                col = start_col + j

                if col >= grid_width:
                    break

                # Ne pas écraser les caractères déjà placés
                if grid[row][col] == " ":
                    grid[row][col] = char

    # Suppression des espaces en fin de ligne
    result = "\n".join(
        "".join(row).rstrip()
        for row in grid
    )

    return f"## Page {page_number}\n\n```text\n{result}\n```\n"


markdown = ["# Reconstruction visuelle du PDF\n"]

with pymupdf.open(PDF_PATH) as doc:
    for page_number, page in enumerate(doc, start=1):
        elements = extract_elements(page)

        markdown.append(
            build_visual_markdown(page, elements, page_number)
        )

OUTPUT_PATH.write_text(
    "\n".join(markdown),
    encoding="utf-8"
)

print(f"Fichier créé : {OUTPUT_PATH}")