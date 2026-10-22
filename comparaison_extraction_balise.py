import pymupdf
from pathlib import Path
from html import escape

PROJECT_ROOT = Path(__file__).resolve().parent
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "test_pdf.pdf"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "extraction_spatiale.html"

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def overlaps_table(bbox, table_bboxes):
    rect = pymupdf.Rect(bbox)

    for table_bbox in table_bboxes:
        intersection = rect & pymupdf.Rect(table_bbox)

        if not intersection.is_empty:
            # On ignore uniquement si la majorité du bloc
            # appartient à un tableau
            area = rect.width * rect.height

            if area > 0:
                overlap = intersection.width * intersection.height
                if overlap / area > 0.5:
                    return True

    return False


def table_to_html(rows):
    result = ['<table style="border-collapse:collapse;width:100%;">']

    for i, row in enumerate(rows):
        result.append("<tr>")
        tag = "th" if i == 0 else "td"

        for cell in row:
            value = escape(str(cell or ""))
            result.append(
                f'<{tag} style="border:1px solid #555;padding:3px;">'
                f"{value}</{tag}>"
            )

        result.append("</tr>")

    result.append("</table>")
    return "\n".join(result)


def extract_elements(page):
    elements = []

    # Tableaux
    tables = page.find_tables()
    table_bboxes = []

    for table in tables.tables:
        bbox = tuple(table.bbox)
        table_bboxes.append(bbox)

        rows = table.extract()

        if rows:
            elements.append({
                "type": "table",
                "bbox": bbox,
                "content": table_to_html(rows),
            })

    # Paragraphes / blocs de texte
    for block in page.get_text("blocks"):
        if len(block) < 7 or block[6] != 0:
            continue

        bbox = tuple(block[:4])
        text = block[4].strip()

        if not text or overlaps_table(bbox, table_bboxes):
            continue

        elements.append({
            "type": "text",
            "bbox": bbox,
            "content": text,
        })

    return elements


def build_spatial_markdown(page, elements, page_number):
    width = page.rect.width
    height = page.rect.height

    lines = [
        f"<h2>Page {page_number}</h2>",
        "",
        '<div style="'
        'position:relative;'
        f'width:{width:.1f}px;'
        f'height:{height:.1f}px;'
        'background:white;'
        'color:black;'
        'border:1px solid #ddd;'
        '">',
    ]

    for element in elements:
        x0, y0, x1, y1 = element["bbox"]

        if element["type"] == "text":
            content = escape(element["content"]).replace("\n", "<br>")
        else:
            content = element["content"]

        lines.append(
            '<div style="'
            'position:absolute;'
            f'left:{x0:.1f}px;'
            f'top:{y0:.1f}px;'
            f'width:{x1 - x0:.1f}px;'
            'font-size:10px;'
            'line-height:1.2;'
            'overflow-wrap:break-word;'
            '">'
            f'{content}'
            '</div>'
        )

    lines.append("</div>")
    lines.append("")

    return "\n".join(lines)


# Traitement du PDF
markdown_pages = [
    "<!DOCTYPE html>",
    '<html lang="fr">',
    "<head>",
    '<meta charset="UTF-8">',
    "</head>",
    "<body>",
    "<h1>Reconstruction spatiale du PDF</h1>",
]

with pymupdf.open(PDF_PATH) as doc:
    for page_number, page in enumerate(doc, start=1):
        elements = extract_elements(page)

        markdown_pages.append(
            build_spatial_markdown(page, elements, page_number)
        )

# AJOUTE ICI la fermeture du HTML
markdown_pages.append("</body>")
markdown_pages.append("</html>")

# Enregistrement
OUTPUT_PATH.write_text(
    "\n".join(markdown_pages),
    encoding="utf-8"
)

print(f"Fichier créé : {OUTPUT_PATH}")