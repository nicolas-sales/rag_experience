from pathlib import Path
import pymupdf
import json

from src.image_analysis import classify_images, run_deplot, finalize_deplot

from src.markdown_converter import build_page_markdowns, build_chunks, export_pages_markdown, export_blocks_markdown



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
# Extraction des blocs de texte
# --------------------------------------------------

def extract_text(doc, pages_document):

    total_text_blocks = 0

    for page_index, page in enumerate(doc):

        text_blocks = page.get_text("blocks", sort=True)

        table_elements = [
            element
            for element in pages_document[page_index]["elements"]
            if element["type"] == "table"
        ]

        for block in text_blocks:

            x0, y0, x1, y1, text, block_number, block_type = block

            if block_type != 0:
                continue

            text = text.strip()

            text = remove_consecutive_duplicate_lines(text)

            if not text:
                continue

            text_bbox = [x0, y0, x1, y1]

            text_rectangle = pymupdf.Rect(text_bbox)

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

            text_element = {
                "type": "text",
                "block_number": block_number,
                "bbox": text_bbox,
                "content": text
            }

            pages_document[page_index]["elements"].append(
                text_element
            )

            total_text_blocks += 1

    return total_text_blocks


# --------------------------------------------------
# Extraction des images et de leurs positions
# --------------------------------------------------

def extract_images(doc, pages_document, document_id):

    total_occurrences = 0

    for page_index, page in enumerate(doc):

        page_images = page.get_images(full=True)

        for image_index, image_info in enumerate(page_images):

            xref = image_info[0]
            width = image_info[2]
            height = image_info[3]

            image_positions = page.get_image_rects(xref)

            for occurrence_index, position in enumerate(image_positions):

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
# Tri des éléments selon leur position sur la page
# --------------------------------------------------

def sort_page_elements(pages_document):

    for page in pages_document:

        page["elements"] = sorted(
            page["elements"],
            key=lambda element: (
                element["bbox"][1],  # y0 : de haut en bas
                element["bbox"][0]   # x0 : de gauche à droite
            )
        )


# --------------------------------------------------
# Pipeline principal d'ingestion
# --------------------------------------------------

def main():

    document_id = PDF_PATH.stem

    print(f"PDF : {PDF_PATH}")

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
        total_text_blocks = extract_text(
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

    # 6. Tri des éléments
    sort_page_elements(pages_document)

    print("Tableaux :", total_tables)
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
        / "processed"
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
        / "processed"
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
        / "processed"
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
        / "processed"
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









