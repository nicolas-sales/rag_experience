
# --------------------------------------------------
# Conversion des tableaux PyMuPDF en Markdown
# --------------------------------------------------

def table_to_markdown(table_element):

    columns = table_element["columns"]
    rows = table_element["rows"]

    markdown_lines = []

    column_values = [
        str(value).replace("\n", " ").replace("|", "\\|")
        if value is not None else ""
        for value in columns
    ]

    header_line = "| " + " | ".join(column_values) + " |"
    markdown_lines.append(header_line)

    separator_values = ["---"] * len(column_values)
    separator_line = "| " + " | ".join(separator_values) + " |"
    markdown_lines.append(separator_line)

    for row in rows:

        row_values = [
            str(value).replace("\n", " ").replace("|", "\\|")
            if value is not None else ""
            for value in row
        ]

        # Garantir le même nombre de cellules que de colonnes
        row_values = (
            row_values[:len(column_values)]
            + [""] * max(0, len(column_values) - len(row_values))
        )

        row_line = "| " + " | ".join(row_values) + " |"
        markdown_lines.append(row_line)

    return "\n".join(markdown_lines)


# --------------------------------------------------
# Conversion du texte
# --------------------------------------------------

def text_to_markdown(text_element):

    return text_element["content"]


# --------------------------------------------------
# Conversion des graphiques DePlot
# --------------------------------------------------

def chart_to_markdown(image_element):

    chart_data = image_element["deplot_parsed"]

    title = chart_data["title"]
    columns = chart_data["columns"]
    rows = chart_data["rows"]

    temporary_table = {
        "columns": columns,
        "rows": rows
    }

    chart_table_markdown = table_to_markdown(
        temporary_table
    )

    if title:
        return (
            f"### Graphique : {title}\n\n"
            f"{chart_table_markdown}"
        )

    return (
        f"### Graphique\n\n"
        f"{chart_table_markdown}"
    )


# --------------------------------------------------
# Conversion des images
# --------------------------------------------------

def image_to_markdown(image_element):

    asset_id = image_element["asset_id"]

    image_category = image_element.get(
        "image_category",
        "image"
    )

    # Exclure les éléments décoratifs
    if image_category == "a logo or decorative graphic":
        return ""

    image_reference = (
        f"![{image_category}]"
        f"(asset://{asset_id})"
    )

    if (
        image_element.get("is_chart", False)
        and image_element.get("deplot_valid", False)
        and image_element.get("deplot_parsed") is not None
    ):

        chart_markdown = chart_to_markdown(image_element)

        return (
            f"{image_reference}\n\n"
            f"{chart_markdown}"
        )

    return image_reference


# --------------------------------------------------
# Conversion d'un élément
# --------------------------------------------------

def element_to_markdown(element):

    element_type = element["type"]

    if element_type == "text":
        return text_to_markdown(element)

    if element_type == "table":
        return table_to_markdown(element)

    if element_type == "image":
        return image_to_markdown(element)

    return ""


# --------------------------------------------------
# Conversion de toutes les pages
# --------------------------------------------------

def build_page_markdowns(pages_document):

    page_markdowns = []

    for page_data in pages_document:

        markdown_parts = []

        # Les éléments ont déjà été triés dans ingestion.py
        for element in page_data["elements"]:

            element_markdown = element_to_markdown(element)

            if element_markdown:
                markdown_parts.append(element_markdown)

        page_markdown = "\n\n".join(markdown_parts)

        page_markdowns.append(page_markdown)

    return page_markdowns


# --------------------------------------------------
# Construction des chunks : 1 chunk par page
# --------------------------------------------------

def build_chunks(pages_document, page_markdowns, document_id, pdf_path):

    chunks = []

    for page_index, page_data in enumerate(pages_document):

        elements = page_data["elements"]

        element_types = list(
            dict.fromkeys(
                element["type"]
                for element in elements
            )
        )

        image_ids = list(
            dict.fromkeys(
                element["asset_id"]
                for element in elements
                if element["type"] == "image"
            )
        )

        image_categories = list(
            dict.fromkeys(
                element.get("image_category", "image")
                for element in elements
                if element["type"] == "image"
            )
        )

        has_valid_chart = any(
            element["type"] == "image"
            and element.get("deplot_valid", False)
            for element in elements
        )

        source_elements = []

        for element_index, element in enumerate(elements):

            source_element = {
                "element_id": (
                    f"{document_id}"
                    f"_page_{page_data['page']}"
                    f"_element_{element_index}"
                ),
                "type": element["type"],
                "bbox": element["bbox"]
            }

            if element["type"] == "image":

                source_element["asset_id"] = element["asset_id"]

                source_element["image_category"] = (
                    element.get("image_category", "image")
                )

                if element.get("deplot_valid", False):
                    source_element["deplot_valid"] = True

            source_elements.append(source_element)

        chunk_id = (
            f"{document_id}_page_{page_data['page']}"
        )

        chunk = {
            "chunk_id": chunk_id,

            "page_content": page_markdowns[page_index],

            "metadata": {
                "chunk_id": chunk_id,
                "file_name": pdf_path.name,
                "document_id": document_id,
                "page": page_data["page"],
                "page_width": page_data["width"],
                "page_height": page_data["height"],
                "element_types": element_types,
                "image_categories": image_categories,
                "has_images": len(image_ids) > 0,
                "has_valid_chart": has_valid_chart,
                "image_ids": image_ids
            },

            "source_elements": source_elements
        }

        chunks.append(chunk)

    return chunks


from pathlib import Path


def export_pages_markdown(page_markdowns, output_path):

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:

        for page_number, page_markdown in enumerate(
            page_markdowns,
            start=1
        ):

            file.write(f"# Page {page_number}\n\n")
            file.write(page_markdown)
            file.write("\n\n---\n\n")

    print(f"Markdown exporté : {output_path}")