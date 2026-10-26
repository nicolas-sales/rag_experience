import math
from pathlib import Path

import pymupdf

PROJECT_ROOT = Path(__file__).resolve().parent

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "Plan_stratégique_Impact.pdf"
PAGES = [16, 24]  # None pour traiter tout le PDF

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
IMAGE_DIR = OUTPUT_DIR / "images_v4" / PDF_PATH.stem


# ---------------------------------------------------------------------------
# 1. Extraction des éléments : chaque élément a un type, une bbox et un contenu
# ---------------------------------------------------------------------------

def join_spans(spans):
    """Recolle les spans d'une ligne, en ajoutant l'espace manquant entre deux spans éloignés."""
    text = spans[0]["text"]

    for previous, span in zip(spans, spans[1:]):
        if span["bbox"][0] - previous["bbox"][2] > 0.15 * span["size"]:
            text += " "
        text += span["text"]

    return " ".join(text.split())


def extract_lines(page):
    """Lignes de texte visibles, chacune avec sa propre bbox."""
    lines = []

    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue

        for line in block["lines"]:
            # alpha == 0 : texte invisible (zones de survol PowerPoint...)
            spans = [s for s in line["spans"] if s["alpha"] > 0 and s["text"].strip()]

            if not spans:
                continue

            # bbox calculée sur les spans visibles uniquement
            bbox = pymupdf.Rect(spans[0]["bbox"])
            for s in spans[1:]:
                bbox |= s["bbox"]

            lines.append({
                "type": "text",
                "bbox": bbox,
                "text": join_spans(spans),
                "size": max(s["size"] for s in spans),
            })

    return lines


def merge_same_row(lines):
    """
    Fusionne les textes courts alignés sur la même ligne visuelle
    (cellules d'un tableau sans bordures, menu, puce + texte).
    Exemple : "Global", "693", "30 %" -> "Global | 693 | 30 %"
    """
    # Regroupement en lignes visuelles (y0 à moins de 3 points), triées de gauche à droite
    rows = []
    for line in sorted(lines, key=lambda l: l["bbox"].y0):
        if rows and abs(rows[-1][0]["bbox"].y0 - line["bbox"].y0) < 3:
            rows[-1].append(line)
        else:
            rows.append([line])

    merged = []

    for row in rows:
        row.sort(key=lambda l: l["bbox"].x0)
        merged.append(row[0])

        for line in row[1:]:
            previous = merged[-1]
            close = line["bbox"].x0 - previous["bbox"].x1 < 150
            last_cell = previous["text"].split(" | ")[-1]
            is_bullet = len(previous["text"]) == 1 and not previous["text"].isalnum()

            if close and is_bullet:
                # Une puce seule devient "- " devant le texte
                previous["text"] = "- " + line["text"]
            elif close and len(last_cell) <= 25 and len(line["text"]) <= 25:
                previous["text"] += " | " + line["text"]
            else:
                merged.append(line)
                continue

            previous["bbox"] |= line["bbox"]

    return merged


def find_repeated_images(doc):
    """Images présentes sur au moins un tiers des pages (logo, bandeau) : à ignorer."""
    counts = {}
    for page in doc:
        for xref in {img[0] for img in page.get_images()}:
            counts[xref] = counts.get(xref, 0) + 1

    return {xref for xref, n in counts.items() if n >= max(3, len(doc) / 3)}


def extract_images(page, repeated_images):
    """Images de la page, enregistrées en PNG. On ignore les petites (décor, puces) et les logos répétés."""
    images = []

    for info in page.get_image_info(xrefs=True):
        bbox = pymupdf.Rect(info["bbox"]) & page.rect

        if bbox.width < 12 or bbox.height < 12 or info["xref"] in repeated_images:
            continue

        path = IMAGE_DIR / f"p{page.number + 1}_img{len(images) + 1}.png"
        page.get_pixmap(clip=bbox, dpi=150).save(path)

        images.append({"type": "image", "bbox": bbox, "path": path})

    return images


def extract_tables(page):
    """Tableaux avec bordures. On rejette ceux qui couvrent plus de la moitié de la page."""
    tables = []

    for table in page.find_tables().tables:
        bbox = pymupdf.Rect(table.bbox)

        if bbox.get_area() > 0.5 * page.rect.get_area():
            continue

        rows = [[str(cell or "").replace("\n", " ") for cell in row] for row in table.extract()]

        if len(rows) < 2:
            continue

        lines = ["| " + " | ".join(rows[0]) + " |"]
        lines.append("|" + " --- |" * len(rows[0]))
        lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]

        tables.append({"type": "table", "bbox": bbox, "text": "\n".join(lines)})

    return tables


def extract_elements(page, repeated_images):
    tables = extract_tables(page)

    # On retire les lignes qui sont déjà dans un tableau
    lines = [
        line for line in extract_lines(page)
        if not any(line["bbox"] in table["bbox"] for table in tables)
    ]

    return merge_same_row(lines) + extract_images(page, repeated_images) + tables


# ---------------------------------------------------------------------------
# 2. Ordre de lecture : on coupe la page le long du plus grand espace vide,
#    puis on recommence dans chaque morceau (algorithme "XY-cut")
# ---------------------------------------------------------------------------

def largest_gap(elements, axis):
    """
    Plus grand espace vide entre les éléments.
    axis = 0 : espace vertical entre colonnes (sur l'axe x)
    axis = 1 : espace horizontal entre lignes (sur l'axe y)
    Retourne (taille de l'espace, position de la coupe).
    """
    intervals = sorted((e["bbox"][axis], e["bbox"][axis + 2]) for e in elements)

    best_size, best_pos = 0, None
    end = intervals[0][1]

    for start, stop in intervals[1:]:
        if start - end > best_size:
            best_size, best_pos = start - end, (start + end) / 2
        end = max(end, stop)

    return best_size, best_pos


def xy_cut(elements):
    """Renvoie une liste de groupes d'éléments, dans l'ordre de lecture."""
    if len(elements) <= 1:
        return [elements]

    gap_x, cut_x = largest_gap(elements, 0)
    gap_y, cut_y = largest_gap(elements, 1)

    if gap_x < 3 and gap_y < 1.5:
        return [elements]  # plus rien à couper : c'est un bloc

    # On coupe là où l'espace vide est le plus grand
    if gap_y >= gap_x:
        axis, cut = 1, cut_y
    else:
        axis, cut = 0, cut_x

    first = [e for e in elements if e["bbox"][axis + 2] <= cut]
    second = [e for e in elements if e["bbox"][axis + 2] > cut]

    return xy_cut(first) + xy_cut(second)


# ---------------------------------------------------------------------------
# 3. Markdown pour le RAG : ordre de lecture + position de chaque bloc
# ---------------------------------------------------------------------------

def render_group(group, body_size):
    parts = []
    paragraph = []

    for element in sorted(group, key=lambda e: (e["bbox"].y0, e["bbox"].x0)):
        if element["type"] == "text":
            paragraph.append(element)
            continue

        if element["type"] == "image":
            parts.append(f"![image]({element['path'].relative_to(OUTPUT_DIR).as_posix()})")
        else:
            parts.append(element["text"])

    if paragraph:
        # On recolle les lignes d'un paragraphe, sauf les puces et les lignes de tableau
        # qui gardent leur propre ligne
        out = []
        for line in paragraph:
            text = line["text"]
            new_line = text.startswith("- ") or " | " in text or (out and " | " in out[-1])
            if out and not new_line:
                out[-1] += " " + text
            else:
                out.append(text)
        text = "\n".join(out)

        # Titre : police nettement plus grande que le texte courant
        if max(line["size"] for line in paragraph) >= 1.4 * body_size:
            text = "### " + text

        parts.insert(0, text)

    return "\n\n".join(parts)


def build_rag_markdown(elements, page_number):
    sizes = [e["size"] for e in elements if e["type"] == "text"]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 10

    markdown = [f"## Page {page_number}"]

    for group in xy_cut(elements):
        bbox = pymupdf.Rect(group[0]["bbox"])
        for element in group[1:]:
            bbox |= element["bbox"]

        markdown.append(
            f"<!-- page={page_number} bbox={bbox.x0:.0f},{bbox.y0:.0f},{bbox.x1:.0f},{bbox.y1:.0f} -->\n"
            + render_group(group, body_size)
        )

    return "\n\n".join(markdown) + "\n"


# ---------------------------------------------------------------------------
# 4. Grille monospace : reconstruction visuelle pour vérifier à l'oeil
# ---------------------------------------------------------------------------

def build_visual_markdown(page, elements, page_number):
    texts = [e for e in elements if e["type"] == "text"]

    # Largeur d'un caractère calée sur les textes les plus serrés de la page,
    # pour qu'une ligne ne déborde pas sur la colonne voisine
    widths = sorted(e["bbox"].width / len(e["text"]) for e in texts if len(e["text"]) >= 5)
    char_width = max(widths[len(widths) // 10], 2.5) if widths else 3.5
    line_height = 9

    grid_width = math.ceil(page.rect.width / char_width) + 1
    grid_height = math.ceil(page.rect.height / line_height) + 1
    grid = [[" "] * grid_width for _ in range(grid_height)]

    for element in elements:
        if element["type"] == "image":
            lines = [f"[IMAGE {element['path'].name}]"]
        else:
            lines = element["text"].splitlines()

        start_col = round(element["bbox"].x0 / char_width)
        start_row = round(element["bbox"].y0 / line_height)

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

    result = "\n".join("".join(row).rstrip() for row in grid).strip("\n")

    return f"## Page {page_number}\n\n```text\n{result}\n```\n"


# ---------------------------------------------------------------------------

def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    rag_markdown = [f"# {PDF_PATH.stem}\n"]
    visual_markdown = [f"# Reconstruction visuelle : {PDF_PATH.stem}\n"]

    with pymupdf.open(PDF_PATH) as doc:
        repeated_images = find_repeated_images(doc)

        for page_number in PAGES or range(1, len(doc) + 1):
            page = doc[page_number - 1]
            elements = extract_elements(page, repeated_images)

            if not elements:
                rag_markdown.append(f"## Page {page_number}\n\n<!-- page sans texte : OCR nécessaire -->\n")
                continue

            rag_markdown.append(build_rag_markdown(elements, page_number))
            visual_markdown.append(build_visual_markdown(page, elements, page_number))

    rag_path = OUTPUT_DIR / f"{PDF_PATH.stem}_rag.md"
    visual_path = OUTPUT_DIR / f"{PDF_PATH.stem}_grille.md"

    rag_path.write_text("\n".join(rag_markdown), encoding="utf-8")
    visual_path.write_text("\n".join(visual_markdown), encoding="utf-8")

    print(f"Fichier créé : {rag_path}")
    print(f"Fichier créé : {visual_path}")


if __name__ == "__main__":
    main()
