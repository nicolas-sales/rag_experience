import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ELEMENTS_PATH = PROJECT_ROOT / "data" / "processed" / "src3" / "source_elements_v3.json"


def load_source_elements():
    """Charge source_elements_v3.json : {nom du fichier: {page: [éléments]}}."""
    with open(SOURCE_ELEMENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_elements(file_name, page_number):
    """Retourne les éléments d'une page d'un PDF (liste vide si inconnue)."""
    source_data = load_source_elements()

    # Les numéros de pages sont des chaînes dans le JSON
    return source_data.get(file_name, {}).get(str(page_number), [])


def get_page_elements(file_name, page_number):
    """
    Retourne les éléments d'une page qui ont du contenu, pour le LLM.

    Chaque élément : {"element_id", "type", "content"}. L'element_id est
    la position de l'élément dans la page ; il sert ensuite à retrouver
    sa bbox (voir `get_source_bboxes`).
    """
    page_elements = []

    for element_id, element in enumerate(get_elements(file_name, page_number)):

        element_type = element.get("type", "")

        if element_type in ("text", "table"):
            content = element.get("content", "")

        elif element_type == "image":
            # Ce que l'OCR a lu dans l'image (chiffres du graphique,
            # nom du logo)
            content = (
                element.get("ocr_positions")
                or element.get("logo_name")
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


def get_source_bboxes(file_name, page_number: int, element_ids: list[int]):
    """Retourne les bbox des éléments demandés d'une page d'un PDF."""
    elements = get_elements(file_name, page_number)

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
