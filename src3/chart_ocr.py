"""
OCR des graphiques et des logos (EasyOCR, sur CPU).

Pour chaque image classée "graphique" par CLIP :
    1. on lit les textes de la zone du graphique sur la page (EasyOCR),
       chaque texte avec sa position
    2. chaque chiffre est associé au texte placé sous lui
       (l'année sous la barre) : "2023 : 122"

Pour chaque image classée "logo" par CLIP :
    on garde le nom lu, s'il est lu avec assez de confiance : "DECATHLON"

Les textes lus sont gardés en cache : l'OCR ne tourne qu'une fois par image.
"""

import hashlib

import pymupdf

from src3.image_cache import load_image_cache, save_image_cache


# 150 dpi ne suffit pas : les petits nombres ("60", "87") ne sont pas lus
OCR_DPI = 300

# En dessous, le nom du logo est souvent mal lu ("Loraconaac")
MIN_LOGO_CONFIDENCE = 0.5

# Au-delà, ce n'est pas un logo mais un visuel plein de texte (couverture)
MAX_LOGO_LENGTH = 40


# --------------------------------------------------
# 1. Lecture de l'image
# --------------------------------------------------

def read_texts(reader, image):

    # EasyOCR renvoie, pour chaque texte : (4 coins, texte, confiance)
    texts = []

    for corners, text, confidence in reader.readtext(image):
        xs = [float(point[0]) for point in corners]
        ys = [float(point[1]) for point in corners]
        texts.append({
            "text": text,
            "confidence": float(confidence),
            "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)
        })

    return texts


# --------------------------------------------------
# 2. Chaque chiffre avec le texte placé sous lui
# --------------------------------------------------

def is_number(text):
    return any(c.isdigit() for c in text) and all(c.isdigit() or c in " .,%" for c in text)


def ocr_with_positions(texts):

    # a) Pour chaque chiffre : le texte le plus proche sous lui,
    #    dans la même colonne (l'année sous la barre).
    #    Pas le plus bas : la légende est souvent sous l'axe.
    pairs = {}

    for index, value in enumerate(texts):

        if not is_number(value["text"]):
            continue

        center = (value["x0"] + value["x1"]) / 2

        below = [
            other_index
            for other_index, other in enumerate(texts)
            if other_index != index
            and other["y0"] > value["y1"]
            and other["x0"] - 10 <= center <= other["x1"] + 10
        ]

        if below:
            pairs[index] = min(below, key=lambda other_index: texts[other_index]["y0"])

    # b) Un texte qui sert d'étiquette ("2022") n'est pas une valeur
    labels = set(pairs.values())
    pairs = {value: label for value, label in pairs.items() if value not in labels}

    # De gauche à droite, comme sur le graphique
    lines = [
        f"{texts[label]['text']} : {texts[value]['text']}"
        for value, label in sorted(pairs.items(), key=lambda pair: texts[pair[0]]["x0"])
    ]

    # Aucun chiffre avec son étiquette : pas un graphique lisible
    # (schéma, carte...). On n'écrit rien plutôt que du texte mal lu.
    if not lines:
        return ""

    paired = set(pairs) | set(pairs.values())
    others = [text["text"] for index, text in enumerate(texts) if index not in paired]
    if others:
        lines.append("Autres textes : " + " | ".join(others))

    return "\n".join(lines)


# --------------------------------------------------
# 3. Nom lu dans un logo
# --------------------------------------------------

def logo_name(texts):

    # Textes lus avec assez de confiance, de gauche à droite
    sure_texts = sorted(
        (text for text in texts if text["confidence"] >= MIN_LOGO_CONFIDENCE),
        key=lambda text: text["x0"]
    )

    name = " ".join(text["text"] for text in sure_texts)

    return name if len(name) <= MAX_LOGO_LENGTH else ""


# --------------------------------------------------
# OCR de tous les graphiques et logos du document
# --------------------------------------------------

def run_chart_ocr(doc, pages_document):

    cache = load_image_cache()
    reader = None
    ocr_calls = 0

    for page_data in pages_document:

        page = doc[page_data["page"] - 1]

        for element in page_data["elements"]:

            if element["type"] != "image":
                continue

            is_chart = element.get("is_chart", False)
            is_logo = "logo" in element.get("image_category", "")

            if not is_chart and not is_logo:
                continue

            # On lit la zone de la page (et pas seulement l'image) :
            # les chiffres écrits par-dessus le graphique sont aussi lus
            image = page.get_pixmap(clip=pymupdf.Rect(element["bbox"]), dpi=OCR_DPI).tobytes("png")
            cache_key = hashlib.sha256(image).hexdigest()

            if cache_key not in cache["ocr"]:

                # EasyOCR n'est chargé que s'il y a une image à lire
                if reader is None:
                    import easyocr
                    reader = easyocr.Reader(["fr", "en"], gpu=False)

                cache["ocr"][cache_key] = read_texts(reader, image)
                save_image_cache(cache)
                ocr_calls += 1

            texts = cache["ocr"][cache_key]

            if is_chart:
                element["ocr_positions"] = ocr_with_positions(texts)
            else:
                element["logo_name"] = logo_name(texts)

    remove_repeated_logos(pages_document)

    return ocr_calls


def remove_repeated_logos(pages_document):

    # Un logo présent sur au moins 3 pages est celui de l'entreprise
    # (comme le menu répété en haut des pages) : il n'apprend rien
    pages_per_name = {}

    for page_data in pages_document:
        for element in page_data["elements"]:
            if element.get("logo_name"):
                pages_per_name.setdefault(element["logo_name"], set()).add(page_data["page"])

    for page_data in pages_document:
        for element in page_data["elements"]:
            if len(pages_per_name.get(element.get("logo_name"), ())) >= 3:
                element["logo_name"] = ""
