import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ELEMENTS_PATH = PROJECT_ROOT / "data" / "processed" / "source_elements.json"


def load_source_elements():
    with open(SOURCE_ELEMENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_page_elements(page_number: int):
    data = load_source_elements()
    elements = data.get(str(page_number), [])

    result = []

    for element_id, element in enumerate(elements):
        content = (
            element.get("deplot_clean")
            if element.get("type") == "image"
            else element.get("text")
        )

        if not content or not content.strip():
            continue

        result.append({
            "element_id": element_id,
            "type": element.get("type"),
            "content": content
        })

    return result


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