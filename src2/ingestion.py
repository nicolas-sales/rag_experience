from pathlib import Path
import pymupdf
import json

from src.image_analysis import classify_images, run_deplot, finalize_deplot

from src2.layout import extract_lines, find_repeated_lines, is_in_margin, merge_same_row, order_elements

from src2.markdown_converter import build_page_markdowns, build_chunks, export_pages_markdown, export_blocks_markdown



# --------------------------------------------------
# Chemins du projet
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Plan_stratégique_Impact.pdf"
)


# --------------------------------------------------
# Initialisation des pages
# --------------------------------------------------

def initialize_pages(doc, document_id):

    pages_document = []

    for page_index, page in enumerate(doc):

        page_structure = {
            "document_id": document_id,
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "elements": []
        }

        pages_document.append(page_structure)

    return pages_document


# --------------------------------------------------
# Extraction des tableaux
# --------------------------------------------------

def extract_tables(doc, pages_document):

    total_tables = 0

    for page_index, page in enumerate(doc):

        table_result = page.find_tables()

        for table_index, table in enumerate(table_result.tables):

            data_table = table.extract()

            if not data_table:
                continue

            columns = data_table[0]
            rows = data_table[1:]

            # Une table doit avoir au moins 2 colonnes
            if len(columns) < 2:
                continue

            # Une table doit avoir au moins une ligne de données
            if len(rows) < 1:
                continue

            table_element = {
                "type": "table",
                "table_index": table_index,
                "bbox": list(table.bbox),
                "columns": columns,
                "rows": rows
            }

            pages_document[page_index]["elements"].append(table_element)

            total_tables += 1

    return total_tables


# --------------------------------------------------
# Nettoyage du texte
# --------------------------------------------------

def remove_consecutive_duplicate_lines(text):

    lines = text.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if (
            cleaned_lines
            and line == cleaned_lines[-1]
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# --------------------------------------------------
# Extraction des lignes de texte
# --------------------------------------------------
# On extrait ligne par ligne (et non par bloc PyMuPDF) :
# les lignes sont regroupées en blocs plus tard,
# dans order_page_elements, selon leur zone sur la page.

def extract_text(doc, pages_document):

    total_text_lines = 0

    # Menus et pieds de page répétés sur les pages
    repeated_lines = find_repeated_lines(doc)

    for page_index, page in enumerate(doc):

        table_elements = [
            element
            for element in pages_document[page_index]["elements"]
            if element["type"] == "table"
        ]

        lines = []

        for line in extract_lines(page):

            if line["content"] in repeated_lines and is_in_margin(line, page):
                continue

            text_rectangle = pymupdf.Rect(line["bbox"])

            inside_table = False

            for table_element in table_elements:

                table_rectangle = pymupdf.Rect(
                    table_element["bbox"]
                )

                if table_rectangle.intersects(text_rectangle):
                    inside_table = True
                    break

            if inside_table:
                continue

            lines.append(line)

        # Cellules de tableau sans bordures, menus, puces
        lines = merge_same_row(lines)

        pages_document[page_index]["elements"].extend(lines)

        total_text_lines += len(lines)

    return total_text_lines


# --------------------------------------------------
# Extraction des images et de leurs positions
# --------------------------------------------------

def find_repeated_images(doc):

    # Images présentes sur au moins un tiers des pages
    # (logo de l'entreprise, bandeau) : décoratives
    counts = {}

    for page in doc:
        for xref in {image[0] for image in page.get_images()}:
            counts[xref] = counts.get(xref, 0) + 1

    return {
        xref
        for xref, count in counts.items()
        if count >= max(3, len(doc) / 3)
    }


def extract_images(doc, pages_document, document_id):

    total_occurrences = 0

    repeated_images = find_repeated_images(doc)

    for page_index, page in enumerate(doc):

        page_images = page.get_images(full=True)

        for image_index, image_info in enumerate(page_images):

            xref = image_info[0]
            width = image_info[2]
            height = image_info[3]

            if xref in repeated_images:
                continue

            image_positions = page.get_image_rects(xref)

            for occurrence_index, position in enumerate(image_positions):

                # Trop petite : barre décorative, puce dessinée
                if position.width < 12 or position.height < 12:
                    continue

                image_id = (
                    f"{document_id}_page_{page_index + 1}"
                    f"_image_{image_index}"
                    f"_occurrence_{occurrence_index}"
                )

                image_element = {
                    "type": "image",
                    "image_id": image_id,
                    "image_index": image_index,
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "bbox": list(position)
                }

                pages_document[page_index]["elements"].append(
                    image_element
                )

                total_occurrences += 1

    return total_occurrences


# --------------------------------------------------
# Création de la banque d'images
# --------------------------------------------------

def create_image_bank(doc, pages_document, document_id):

    image_bank_root = PROJECT_ROOT / "image_bank"
    image_bank_root.mkdir(parents=True, exist_ok=True)

    image_bank = []
    saved_assets = {}

    for page in pages_document:

        page_number = page["page"]

        page_folder = (
            image_bank_root
            / document_id
            / f"page_{page_number}"
        )

        for element in page["elements"]:

            if element["type"] != "image":
                continue

            asset_id = (
                f"{document_id}_page_{page_number}"
                f"_image_{element['image_index']}"
            )

            element["asset_id"] = asset_id

            # Si l'image a déjà été sauvegardée,
            # on réutilise son chemin.
            if asset_id in saved_assets:

                element["storage_path"] = saved_assets[asset_id]
                continue

            extracted_image = doc.extract_image(
                element["xref"]
            )

            extension = extracted_image["ext"]

            file_name = (
                f"image_{element['image_index']}.{extension}"
            )

            page_folder.mkdir(
                parents=True,
                exist_ok=True
            )

            file_path = page_folder / file_name

            file_path.write_bytes(
                extracted_image["image"]
            )

            # Chemin relatif à la racine du projet
            storage_path = file_path.relative_to(
                PROJECT_ROOT
            ).as_posix()

            element["storage_path"] = storage_path

            image_record = {
                "asset_id": asset_id,
                "document_id": document_id,
                "page": page_number,
                "image_index": element["image_index"],
                "xref": element["xref"],
                "width": element["width"],
                "height": element["height"],
                "extension": extension,
                "storage_path": storage_path
            }

            image_bank.append(image_record)

            saved_assets[asset_id] = storage_path

    return image_bank


# --------------------------------------------------
# Ordre de lecture et agrégation des blocs
# --------------------------------------------------
# Un simple tri (y0, x0) mélange les colonnes :
# sur une page en cartes, les puces de 3 cartes différentes
# se retrouvaient entrelacées. On découpe la page en zones (XY-cut),
# puis les lignes de texte d'une même zone deviennent un seul bloc.

def order_page_elements(pages_document):

    for page in pages_document:

        page["elements"] = order_elements(page["elements"])


# --------------------------------------------------
# Pipeline principal d'ingestion
# --------------------------------------------------

def main():

    document_id = PDF_PATH.stem

    print(f"PDF : {PDF_PATH}")

    # Sorties séparées de celles de src/
    (PROJECT_ROOT / "data" / "processed" / "src2").mkdir(
        parents=True,
        exist_ok=True
    )

    with pymupdf.open(PDF_PATH) as doc:

        # 1. Initialisation des pages
        pages_document = initialize_pages(
            doc,
            document_id
        )

        # 2. Extraction des tableaux
        total_tables = extract_tables(
            doc,
            pages_document
        )

        # 3. Extraction des textes
        total_text_lines = extract_text(
            doc,
            pages_document
        )

        # 4. Extraction des images
        total_images = extract_images(
            doc,
            pages_document,
            document_id
        )

        # 5. Sauvegarde des images
        image_bank = create_image_bank(
            doc,
            pages_document,
            document_id
        )

    # 6. Ordre de lecture et agrégation des blocs
    order_page_elements(pages_document)

    total_text_blocks = sum(
        1
        for page in pages_document
        for element in page["elements"]
        if element["type"] == "text"
    )

    print("Tableaux :", total_tables)
    print("Lignes de texte :", total_text_lines)
    print("Blocs de texte :", total_text_blocks)
    print("Occurrences d'images :", total_images)

    # 7. Classification CLIP
    clip_calls = classify_images(
        pages_document,
        image_bank
    )

    # 8. Analyse DePlot
    deplot_calls = run_deplot(
        pages_document
    )

    # 9. Validation des résultats DePlot
    finalize_deplot(pages_document)

    # 10. Conversion Markdown
    page_markdowns = build_page_markdowns(
        pages_document
    )

    # 11. Export Markdown pour inspection
    markdown_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed" / "src2"
        / "pages_markdown.md"
    )

    export_pages_markdown(
        page_markdowns,
        markdown_output_path
    )

    # 12. Export Markdown par blocks

    blocks_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed" / "src2"
        / "blocks_diagnostic.md"
    )

    export_blocks_markdown(
        pages_document,
        blocks_output_path
    )

    # 13. Construction des chunks
    chunks = build_chunks(
        pages_document=pages_document,
        page_markdowns=page_markdowns,
        document_id=document_id,
        pdf_path=PDF_PATH
    )

    
# --------------------------------------------------
# Export des éléments sources pour le surlignage PDF
# --------------------------------------------------

    source_elements_v3 = {}

    for page_data in pages_document:

        page_number = page_data["page"]

        source_elements_v3[str(page_number)] = []

        for element in page_data["elements"]:

            source_element = {
                "type": element["type"],
                "bbox": element["bbox"]
            }

            if element["type"] == "text":
                source_element["content"] = element.get(
                    "content", ""
                )

            elif element["type"] == "table":
                source_element["content"] = (
                    "Colonnes : "
                    + str(element.get("columns", []))
                    + "\nLignes : "
                    + str(element.get("rows", []))
                )

            elif element["type"] == "image":
                source_element["is_chart"] = element.get(
                    "is_chart", False
                )
                source_element["deplot_clean"] = element.get(
                    "deplot_clean", ""
                )
                source_element["image_category"] = element.get(
                    "image_category", ""
                )

            source_elements_v3[str(page_number)].append(
                source_element
            )

    source_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed" / "src2"
        / "source_elements_v3.json"
    )

    with open(source_output_path, "w", encoding="utf-8") as f:
        json.dump(
            source_elements_v3,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Sources v3 exportées : {source_output_path}")



    # 13. Export des chunks JSON
    chunks_output_path = (
        PROJECT_ROOT
        / "data"
        / "processed" / "src2"
        / "chunks.json"
    )

    chunks_output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chunks_output_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Chunks exportés : {chunks_output_path}")

    # 14. Vérifications
    print("\n=== RÉSULTATS ===")
    print("Pages :", len(pages_document))
    print("Chunks :", len(chunks))
    print("CLIP (nouvelles analyses) :", clip_calls)
    print("DePlot (nouvelles analyses) :", deplot_calls)

    print("\n=== APERÇU PAGE 16 ===")

    if len(chunks) >= 16:
        print(chunks[15]["page_content"][:1500])


if __name__ == "__main__":
    main()









