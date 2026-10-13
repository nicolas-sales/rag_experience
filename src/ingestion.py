from pathlib import Path
import pymupdf

from src.image_analysis import classify_images, run_deplot, finalize_deplot


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























def main():

    document_id = PDF_PATH.stem

    with pymupdf.open(PDF_PATH) as doc:

        # Étape 1 : initialisation
        pages_document = initialize_pages(
            doc=doc,
            document_id=document_id
        )

        # Étape 2 : tableaux
        total_tables = extract_tables(
            doc=doc,
            pages_document=pages_document
        )

        # Étape 3 : textes
        total_text_blocks = extract_text(
            doc=doc,
            pages_document=pages_document
        )

        # Extraction des images
        total_image_occurrences = extract_images(
            doc=doc,
            pages_document=pages_document,
            document_id=document_id
        )

        # Création de la banque d'images
        image_bank = create_image_bank(
            doc=doc,
            pages_document=pages_document,
            document_id=document_id
        )

        # Étape 6 : tri des éléments
        sort_page_elements(pages_document)


        print("\n=== ÉLÉMENTS TRIÉS — PAGE 16 ===")

        for element_id, element in enumerate(pages_document[15]["elements"][:10]):

            print(
                f"ID : {element_id} | "
                f"Type : {element['type']} | "
                f"Position : {element['bbox'][:2]}"
            )



if __name__=="__main__":
    main()