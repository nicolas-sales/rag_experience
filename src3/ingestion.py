"""
Ingestion des PDF de data/raw/ (version src3).

Chaque PDF est transformé en Markdown, 1 chunk par page, en gardant la position
des textes, tableaux et images. Étapes pour un PDF (voir `ingest_pdf`) :

    1. Tableaux  : détectés avec PyMuPDF (`find_tables`).
    2. Textes    : extraits ligne par ligne puis regroupés par zone
                   (zones détectées par le modèle de layout de pymupdf4llm).
    3. Images    : position de chaque image, puis sauvegarde dans `image_bank/`.
    4. Ordre de lecture des éléments de chaque page (XY-cut).
    5. Analyse des images : CLIP (graphique / logo / autre) puis OCR.
    6. Markdown de chaque page et chunks.

Sorties (dans data/processed/src3/) :
    - chunks.json             : les chunks de tous les PDF (lu par indexing.py) ;
    - source_elements_v3.json : les éléments de chaque page de chaque PDF,
                                {nom du fichier: {page: [éléments]}} (surlignage) ;
    - <nom du PDF>/pages_markdown.md et blocks_diagnostic.md : pour inspection.

Lancement depuis la racine du projet :
    venvrag\\python.exe -m src3.ingestion
"""

import json
from pathlib import Path

import pymupdf

from src3.chart_ocr import run_chart_ocr
from src3.image_analysis import classify_images
from src3.layout import (
    extract_lines,
    find_repeated_headers,
    get_zones,
    group_lines_by_zone,
    is_header_candidate,
    order_elements,
)
from src3.markdown_converter import (
    build_chunks,
    build_page_markdowns,
    export_blocks_markdown,
    export_pages_markdown,
)


# --------------------------------------------------
# Chemins et paramètres
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Tous les PDF de ce dossier sont ingérés
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Sorties séparées de celles de src/ et src2/
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "src3"

IMAGE_BANK_DIR = PROJECT_ROOT / "image_bank"

# En dessous de cette taille (en points), une image est décorative
# (barre, puce dessinée) et on l'ignore.
MIN_IMAGE_SIZE = 12


# --------------------------------------------------
# Initialisation des pages
# --------------------------------------------------

def initialize_pages(doc, document_id):
    """
    Crée la structure vide de chaque page du PDF.

    Chaque page est un dictionnaire avec son numéro (à partir de 1),
    ses dimensions et une liste "elements" que les étapes suivantes
    remplissent (tableaux, blocs de texte, images).

    Retourne la liste des pages.
    """
    return [
        {
            "document_id": document_id,
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "elements": [],
        }
        for page_index, page in enumerate(doc)
    ]


# --------------------------------------------------
# Tableaux
# --------------------------------------------------

def extract_tables(doc, pages_document):
    """
    Détecte les tableaux de chaque page et les ajoute aux éléments de la page.

    La première ligne du tableau sert d'en-têtes de colonnes. On ne garde
    que les vrais tableaux : au moins 2 colonnes et au moins 1 ligne de données.

    Retourne le nombre total de tableaux gardés.
    """
    total_tables = 0

    for page_index, page in enumerate(doc):

        # use_layout=False : sinon find_tables utilise le modèle de
        # pymupdf4llm (activé dès son import) et plante.
        table_result = page.find_tables(use_layout=False)

        for table_index, table in enumerate(table_result.tables):

            data_table = table.extract()

            if not data_table:
                continue

            columns = data_table[0]
            rows = data_table[1:]

            if len(columns) < 2 or len(rows) < 1:
                continue

            pages_document[page_index]["elements"].append({
                "type": "table",
                "table_index": table_index,
                "bbox": list(table.bbox),
                "columns": columns,
                "rows": rows,
            })

            total_tables += 1

    return total_tables


# --------------------------------------------------
# Textes
# --------------------------------------------------
# On extrait ligne par ligne (et non par bloc PyMuPDF),
# puis les lignes d'une même zone (détectée par le modèle
# de pymupdf4llm) sont regroupées en un bloc.

def is_inside_table(line, table_elements):
    """
    Indique si une ligne de texte touche un des tableaux de la page.

    Le texte des tableaux est déjà dans l'élément "table" : on ne veut
    pas le garder une deuxième fois comme bloc de texte.
    """
    line_rect = pymupdf.Rect(line["bbox"])

    return any(
        pymupdf.Rect(table["bbox"]).intersects(line_rect)
        for table in table_elements
    )


def extract_text(doc, pages_document):
    """
    Extrait le texte de chaque page et l'ajoute sous forme de blocs.

    Pour chaque page :
      - on récupère les zones du modèle de layout (titre, liste, image...) ;
      - on retire les en-têtes / pieds de page répétés sur plusieurs pages
        et les lignes situées dans un tableau ;
      - on regroupe les lignes restantes en un bloc par zone.

    Les zones sont gardées dans la page (clé "zones") car l'ordre de
    lecture en a besoin (voir `order_page_elements`).

    À appeler après `extract_tables`. Retourne le nombre de lignes gardées.
    """
    total_text_lines = 0

    all_zones = get_zones(doc)
    repeated_headers = find_repeated_headers(doc, all_zones)

    for page_index, page in enumerate(doc):

        page_data = pages_document[page_index]
        zones = all_zones[page_index]
        page_data["zones"] = zones

        table_elements = [
            element
            for element in page_data["elements"]
            if element["type"] == "table"
        ]

        lines = []

        for line in extract_lines(page):

            is_repeated_header = (
                line["content"] in repeated_headers
                and is_header_candidate(line, page, zones)
            )

            if is_repeated_header or is_inside_table(line, table_elements):
                continue

            lines.append(line)

        total_text_lines += len(lines)

        page_data["elements"].extend(group_lines_by_zone(lines, zones))

    return total_text_lines


# --------------------------------------------------
# Images
# --------------------------------------------------

def find_repeated_images(doc):
    """
    Trouve les images présentes sur beaucoup de pages (logo, bandeau...).

    Une image est considérée comme décorative si elle apparaît sur au moins
    un tiers des pages (et au moins 3 pages).

    Retourne l'ensemble de leurs xref (identifiants PyMuPDF des images).
    """
    counts = {}

    for page in doc:
        for xref in {image[0] for image in page.get_images()}:
            counts[xref] = counts.get(xref, 0) + 1

    min_pages = max(3, len(doc) / 3)

    return {xref for xref, count in counts.items() if count >= min_pages}


def extract_images(doc, pages_document, document_id):
    """
    Ajoute chaque image de chaque page aux éléments de la page, avec sa position.

    Une même image peut apparaître plusieurs fois sur une page : on crée un
    élément par apparition (occurrence). On ignore les images répétées sur
    beaucoup de pages et celles trop petites.

    Retourne le nombre total d'images gardées.
    """
    total_occurrences = 0

    repeated_images = find_repeated_images(doc)

    for page_index, page in enumerate(doc):

        page_number = page_index + 1

        for image_index, image_info in enumerate(page.get_images(full=True)):

            xref, _, width, height = image_info[:4]

            if xref in repeated_images:
                continue

            for occurrence_index, position in enumerate(page.get_image_rects(xref)):

                if position.width < MIN_IMAGE_SIZE or position.height < MIN_IMAGE_SIZE:
                    continue

                image_id = (
                    f"{document_id}_page_{page_number}"
                    f"_image_{image_index}_occurrence_{occurrence_index}"
                )

                pages_document[page_index]["elements"].append({
                    "type": "image",
                    "image_id": image_id,
                    "image_index": image_index,
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "bbox": list(position),
                })

                total_occurrences += 1

    return total_occurrences


def create_image_bank(doc, pages_document, document_id):
    """
    Sauvegarde les images sur le disque, dans image_bank/<document>/page_<n>/.

    Chaque image n'est écrite qu'une fois par page, même si elle y apparaît
    plusieurs fois. Chaque élément image reçoit son "asset_id" et son
    "storage_path" (chemin relatif à la racine du projet).

    Retourne la liste des images sauvegardées (une fiche par fichier),
    utilisée ensuite par CLIP.
    """
    image_bank = []
    saved_paths = {}  # asset_id -> storage_path

    for page_data in pages_document:

        page_number = page_data["page"]
        page_folder = IMAGE_BANK_DIR / document_id / f"page_{page_number}"

        for element in page_data["elements"]:

            if element["type"] != "image":
                continue

            asset_id = f"{document_id}_page_{page_number}_image_{element['image_index']}"
            element["asset_id"] = asset_id

            # Déjà sauvegardée : on réutilise le même fichier
            if asset_id in saved_paths:
                element["storage_path"] = saved_paths[asset_id]
                continue

            extracted_image = doc.extract_image(element["xref"])
            extension = extracted_image["ext"]

            page_folder.mkdir(parents=True, exist_ok=True)
            file_path = page_folder / f"image_{element['image_index']}.{extension}"
            file_path.write_bytes(extracted_image["image"])

            storage_path = file_path.relative_to(PROJECT_ROOT).as_posix()
            element["storage_path"] = storage_path
            saved_paths[asset_id] = storage_path

            image_bank.append({
                "asset_id": asset_id,
                "document_id": document_id,
                "page": page_number,
                "image_index": element["image_index"],
                "xref": element["xref"],
                "width": element["width"],
                "height": element["height"],
                "extension": extension,
                "storage_path": storage_path,
            })

    return image_bank


# --------------------------------------------------
# Ordre de lecture et agrégation des blocs
# --------------------------------------------------
# Un simple tri (y0, x0) mélange les colonnes :
# sur une page en cartes, les puces de 3 cartes différentes
# se retrouvaient entrelacées. On découpe la page en zones (XY-cut)
# pour ranger les blocs, images et tableaux dans l'ordre de lecture.

def order_page_elements(pages_document):
    """
    Trie les éléments de chaque page dans l'ordre de lecture.

    Utilise les zones gardées par `extract_text`, puis les retire de la
    page (elles ne servent plus après).
    """
    for page_data in pages_document:
        page_data["elements"] = order_elements(
            page_data["elements"],
            page_data.pop("zones"),
        )


# --------------------------------------------------
# Exports
# --------------------------------------------------

def build_source_elements(pages_document):
    """
    Prépare la liste des éléments de chaque page pour le surlignage dans le PDF.

    Pour chaque élément on garde son type, sa position (bbox) et son contenu :
    le texte, le contenu du tableau, ou les infos de l'image (graphique,
    OCR, nom du logo, catégorie).

    Retourne un dictionnaire {numéro de page (str): liste d'éléments}.
    """
    source_elements = {}

    for page_data in pages_document:

        page_elements = []

        for element in page_data["elements"]:

            source_element = {
                "type": element["type"],
                "bbox": element["bbox"],
            }

            if element["type"] == "text":
                source_element["content"] = element.get("content", "")

            elif element["type"] == "table":
                source_element["content"] = (
                    "Colonnes : " + str(element.get("columns", []))
                    + "\nLignes : " + str(element.get("rows", []))
                )

            elif element["type"] == "image":
                source_element["is_chart"] = element.get("is_chart", False)
                source_element["ocr_positions"] = element.get("ocr_positions", "")
                source_element["logo_name"] = element.get("logo_name", "")
                source_element["image_category"] = element.get("image_category", "")

            page_elements.append(source_element)

        source_elements[str(page_data["page"])] = page_elements

    return source_elements


def save_json(data, path):
    """Écrit `data` dans un fichier JSON lisible (UTF-8, indenté)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --------------------------------------------------
# Ingestion d'un PDF
# --------------------------------------------------

def ingest_pdf(pdf_path):
    """
    Lance toutes les étapes pour un PDF.

    Écrit pages_markdown.md et blocks_diagnostic.md dans
    OUTPUT_DIR/<nom du PDF>/ (pour inspection).

    Retourne (chunks, source_elements) : les chunks du PDF (1 par page)
    et ses éléments par page (voir `build_source_elements`).
    """
    document_id = pdf_path.stem
    print(f"\n=== PDF : {pdf_path.name} ===")

    with pymupdf.open(pdf_path) as doc:

        # 1. Structure vide de chaque page
        pages_document = initialize_pages(doc, document_id)

        # 2. Tableaux (avant le texte, pour retirer le texte des tableaux)
        total_tables = extract_tables(doc, pages_document)

        # 3. Textes, regroupés en blocs
        total_text_lines = extract_text(doc, pages_document)

        # 4. Images et sauvegarde sur le disque
        total_images = extract_images(doc, pages_document, document_id)
        image_bank = create_image_bank(doc, pages_document, document_id)

    # 5. Ordre de lecture
    order_page_elements(pages_document)

    # 6. Classification des images avec CLIP (graphique / logo / autre)
    clip_calls = classify_images(pages_document, image_bank)

    # 7. OCR des graphiques (chaque chiffre avec son année) et des logos.
    #    Pas de DePlot : il devine des valeurs qui ne sont pas écrites.
    #    On rouvre le PDF : après l'extraction, le rendu des pages change
    #    légèrement et l'image ne serait plus retrouvée dans le cache OCR.
    with pymupdf.open(pdf_path) as doc:
        ocr_calls = run_chart_ocr(doc, pages_document)

    # 8. Markdown de chaque page, exporté pour inspection
    page_markdowns = build_page_markdowns(pages_document)

    document_dir = OUTPUT_DIR / document_id
    export_pages_markdown(page_markdowns, document_dir / "pages_markdown.md")
    export_blocks_markdown(pages_document, document_dir / "blocks_diagnostic.md")

    # 9. Chunks (1 par page)
    chunks = build_chunks(
        pages_document=pages_document,
        page_markdowns=page_markdowns,
        document_id=document_id,
        pdf_path=pdf_path,
    )

    # 10. Résumé
    total_text_blocks = sum(
        1
        for page_data in pages_document
        for element in page_data["elements"]
        if element["type"] == "text"
    )

    print("Pages :", len(pages_document))
    print("Tableaux :", total_tables)
    print("Lignes de texte :", total_text_lines)
    print("Blocs de texte :", total_text_blocks)
    print("Images :", total_images)
    print("CLIP (nouvelles analyses) :", clip_calls)
    print("OCR (nouvelles analyses) :", ocr_calls)

    return chunks, build_source_elements(pages_document)


# --------------------------------------------------
# Pipeline principal
# --------------------------------------------------

def main():
    """
    Ingère tous les PDF de RAW_DIR et écrit dans OUTPUT_DIR :
    chunks.json (tous les PDF) et source_elements_v3.json
    ({nom du fichier: {page: [éléments]}}).
    """
    pdf_paths = sorted(RAW_DIR.glob("*.pdf"))

    if not pdf_paths:
        raise FileNotFoundError(f"Aucun PDF dans {RAW_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    all_source_elements = {}

    for pdf_path in pdf_paths:
        chunks, source_elements = ingest_pdf(pdf_path)
        all_chunks.extend(chunks)
        all_source_elements[pdf_path.name] = source_elements

    source_path = OUTPUT_DIR / "source_elements_v3.json"
    save_json(all_source_elements, source_path)

    chunks_path = OUTPUT_DIR / "chunks.json"
    save_json(all_chunks, chunks_path)

    print("\n=== RÉSULTATS ===")
    print("PDF :", len(pdf_paths))
    print("Chunks :", len(all_chunks))
    print(f"Sources exportées : {source_path}")
    print(f"Chunks exportés : {chunks_path}")


if __name__ == "__main__":
    main()
