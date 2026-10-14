import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ELEMENTS_PATH = PROJECT_ROOT / "data" / "processed" / "source_elements_v3.json"


def load_source_elements():
    with open(SOURCE_ELEMENTS_PATH, encoding="utf-8") as f:
        return json.load(f)



def get_page_elements(page_number):

    source_data = load_source_elements()

    # Les numéros de pages sont des chaînes dans le JSON
    elements = source_data.get(str(page_number), [])

    page_elements = []

    for element_id, element in enumerate(elements):

        element_type = element.get("type", "")

        if element_type == "text":
            content = element.get("content", "")

        elif element_type == "table":
            content = element.get("content", "")

        elif element_type == "image":
            content = (
                element.get("deplot_clean")
                or element.get("content")
                or ""
            )

        else:
            continue

        if not isinstance(content, str):
            content = str(content)

        if not content.strip():
            continue

        page_elements.append({
            "element_id": element_id,
            "type": element_type,
            "content": content
        })

    return page_elements



def get_source_bboxes(page_number: int, element_ids: list[int]):
    data = load_source_elements()
    elements = data.get(str(page_number), [])

    bboxes = []

    for element_id in element_ids:
        if not isinstance(element_id, int):
            continue

        if not 0 <= element_id < len(elements):
            continue

        bbox = elements[element_id].get("bbox")

        if bbox and len(bbox) == 4:
            bboxes.append(bbox)

    return bboxes