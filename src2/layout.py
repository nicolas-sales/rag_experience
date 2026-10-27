"""
Mise en page : remettre les éléments d'une page dans l'ordre de lecture.

Étapes :
    1. extract_lines        : lignes de texte visibles, avec leur position
    2. get_zones            : zones de chaque page détectées par le modèle de
                              pymupdf4llm (titre, paragraphe, liste, image...)
       find_repeated_headers: menus / pieds de page répétés, à retirer
    3. merge_same_row       : cellules d'un tableau et puces recollées sur une ligne
    4. group_lines_by_zone  : les lignes d'une même zone = un bloc
       order_elements       : ordre de lecture (ce qui est sur une même image
                              reste groupé) ; listes et tableaux recollés
    5. xy_cut               : découpage de la page le long des espaces vides
"""

import pymupdf
import pymupdf4llm


# --------------------------------------------------
# 1. Lignes de texte visibles
# --------------------------------------------------

# PyMuPDF ajoute de lui-même un espace quand deux lettres sont un peu
# écartées : les titres aux lettres espacées donnaient "Le m ot du CEO".
# On lui demande de ne pas en ajouter (TEXT_INHIBIT_SPACES) et on décide
# nous-mêmes : un espace si le trou entre deux lettres dépasse
# 0,2 x la taille de la police.
SPACE_RATIO = 0.2


def join_chars(spans):

    text = ""
    previous = None

    for span in spans:
        for char in span["chars"]:
            gap = char["bbox"][0] - previous["bbox"][2] if previous else 0
            if gap > SPACE_RATIO * span["size"] and char["c"] != " ":
                text += " "
            text += char["c"]
            previous = char

    return text


def extract_lines(page):

    lines = []
    flags = pymupdf.TEXTFLAGS_RAWDICT | pymupdf.TEXT_INHIBIT_SPACES

    for block in page.get_text("rawdict", flags=flags)["blocks"]:

        if block["type"] != 0:  # 0 = texte, 1 = image
            continue

        for line in block["lines"]:

            # alpha == 0 : texte invisible (zones de survol PowerPoint)
            spans = [
                s for s in line["spans"]
                if s["alpha"] > 0 and "".join(c["c"] for c in s["chars"]).strip()
            ]

            if not spans:
                continue

            # On recolle les lettres de la ligne, avec nos espaces
            text = join_chars(spans)

            # Position de la ligne = rectangle qui englobe ses morceaux
            bbox = pymupdf.Rect(spans[0]["bbox"])
            for span in spans[1:]:
                bbox |= span["bbox"]

            lines.append({
                "type": "text",
                "bbox": list(bbox),
                "content": " ".join(text.split()),
                "size": min(span["size"] for span in spans)
            })

    return lines


# --------------------------------------------------
# 2. Zones détectées par le modèle de pymupdf4llm
# --------------------------------------------------
# Le modèle (sur CPU) découpe chaque page en zones :
# "title", "section-header", "text", "list-item", "picture",
# "table", "page-header", "page-footer"...

def get_zones(doc):

    # Un seul appel pour tout le PDF ; on ne garde que les zones
    chunks = pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)

    return [
        [{"class": box["class"], "bbox": pymupdf.Rect(box["bbox"])} for box in chunk["page_boxes"]]
        for chunk in chunks
    ]


def find_zone(line, zones):

    # La plus petite zone qui contient le centre de la ligne (None si aucune)
    rect = pymupdf.Rect(line["bbox"])
    center = pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)

    containing = [zone for zone in zones if center in zone["bbox"]]

    return min(containing, key=lambda z: z["bbox"].get_area()) if containing else None


def is_in_margin(line, page):
    # Tout en haut (12 % de la hauteur) ou tout en bas (10 %) de la page
    height = page.rect.height
    return line["bbox"][3] < 0.12 * height or line["bbox"][1] > 0.90 * height


def is_header_candidate(line, page, zones):

    # Peut-être un en-tête / pied de page : en marge, ou dans une zone
    # "page-header" du modèle. Jamais un titre reconnu par le modèle,
    # ni un texte de moins de 3 lettres (chiffres, puces).
    zone = find_zone(line, zones)
    zone_class = zone["class"] if zone else None

    in_header_area = is_in_margin(line, page) or zone_class == "page-header"
    is_title = zone_class in ("section-header", "title")
    has_letters = sum(c.isalpha() for c in line["content"]) >= 3

    return in_header_area and not is_title and has_letters


def find_repeated_headers(doc, all_zones):

    # Pour chaque texte en position d'en-tête : sur quelles pages il apparaît
    pages_per_text = {}

    for page in doc:
        for line in extract_lines(page):
            if is_header_candidate(line, page, all_zones[page.number]):
                pages_per_text.setdefault(line["content"], set()).add(page.number)

    # Répété sur au moins 3 pages : c'est un menu, un bandeau ou un pied de page
    return {text for text, pages in pages_per_text.items() if len(pages) >= 3}


# --------------------------------------------------
# 3. Textes courts sur une même ligne -> une seule ligne
# --------------------------------------------------
# "Global", "693", "30 %"  ->  "Global | 693 | 30 %"
# "•", "Bilan carbone..."  ->  "- Bilan carbone..."

def merge_same_row(lines):

    # a) On range les lignes par ligne visuelle (hauts alignés à 3 points près)
    rows = []
    for line in sorted(lines, key=lambda l: l["bbox"][1]):
        if rows and abs(rows[-1][0]["bbox"][1] - line["bbox"][1]) < 3:
            rows[-1].append(line)
        else:
            rows.append([line])

    # b) Dans chaque ligne visuelle, de gauche à droite, on recolle
    #    un texte à son voisin de gauche s'il est proche
    merged = []

    for row in rows:

        row.sort(key=lambda l: l["bbox"][0])
        merged.append(row[0])

        for line in row[1:]:

            previous = merged[-1]
            close = line["bbox"][0] - previous["bbox"][2] < 150

            if close and len(previous["content"]) == 1 and not previous["content"].isalnum():
                previous["content"] = "- " + line["content"]  # puce
            elif close and len(previous["content"].split(" | ")[-1]) <= 25 and len(line["content"]) <= 25:
                previous["content"] += " | " + line["content"]  # cellule de tableau
            else:
                merged.append(line)
                continue

            previous["bbox"] = list(pymupdf.Rect(previous["bbox"]) | line["bbox"])

    return merged


# --------------------------------------------------
# 5. Ordre de lecture : on coupe la page le long du plus grand
#    espace vide, puis on recommence dans chaque morceau
# --------------------------------------------------

def largest_gap(elements, axis):
    """
    axis = 0 : espace vide entre deux colonnes
    axis = 1 : espace vide entre deux lignes
    Retourne (taille de l'espace, position où couper).
    """

    intervals = sorted((e["bbox"][axis], e["bbox"][axis + 2]) for e in elements)

    best_size, best_position = 0, None
    end = intervals[0][1]

    for start, stop in intervals[1:]:
        if start - end > best_size:
            best_size, best_position = start - end, (start + end) / 2
        end = max(end, stop)

    return best_size, best_position


def xy_cut(elements):

    if len(elements) <= 1:
        return [elements]

    gap_x, cut_x = largest_gap(elements, 0)
    gap_y, cut_y = largest_gap(elements, 1)

    # Plus aucun espace vide : cette zone est un bloc
    if gap_x < 3 and gap_y < 1.5:
        return [elements]

    # On coupe là où l'espace vide est le plus grand
    if gap_y >= gap_x:
        axis, cut = 1, cut_y
    else:
        axis, cut = 0, cut_x

    first = [e for e in elements if e["bbox"][axis + 2] <= cut]
    second = [e for e in elements if e["bbox"][axis + 2] > cut]

    return xy_cut(first) + xy_cut(second)


# --------------------------------------------------
# 4. Une zone du modèle -> un bloc
# --------------------------------------------------

def is_list_or_table(text):
    # Chaque ligne est une puce ou une ligne de tableau
    return all(line.startswith("- ") or " | " in line for line in text.split("\n"))


def make_block(lines):

    # Les lignes d'un paragraphe sont recollées avec un espace ;
    # les puces et les lignes de tableau gardent chacune leur ligne.
    text = lines[0]["content"]

    for line in lines[1:]:
        if is_list_or_table(line["content"]) or " | " in text.split("\n")[-1]:
            text += "\n" + line["content"]
        else:
            text += " " + line["content"]

    bbox = pymupdf.Rect(lines[0]["bbox"])
    for line in lines[1:]:
        bbox |= line["bbox"]

    return {
        "type": "text",
        "bbox": list(bbox),
        "content": text,
        "size": min(line["size"] for line in lines)
    }


def group_lines_by_zone(lines, zones):

    # Chaque ligne va dans sa zone
    lines_per_zone = {id(zone): [] for zone in zones}
    loose_lines = []

    for line in lines:
        zone = find_zone(line, zones)
        if zone is None:
            loose_lines.append(line)
        else:
            lines_per_zone[id(zone)].append(line)

    # Les lignes d'une zone deviennent un bloc
    blocks = []

    for zone in zones:

        zone_lines = lines_per_zone[id(zone)]

        if not zone_lines:
            continue

        block = make_block(merge_same_row(zone_lines))

        if zone["class"] == "list-item" and not block["content"].startswith("- "):
            block["content"] = "- " + block["content"]

        block["is_heading"] = zone["class"] in ("section-header", "title")

        blocks.append(block)

    # Lignes hors de toute zone : gardées telles quelles
    return blocks + merge_same_row(loose_lines)


def group_by_picture(elements, zones):

    # Tout ce qui est posé sur une même zone "image" du modèle
    # (titre du graphique, image, ligne "TOTAL : 52 78 87 99")
    # devient un seul groupe : le XY-cut ne peut pas les séparer.
    pictures = [zone for zone in zones if zone["class"] == "picture"]

    members_per_picture = {}
    others = []

    for element in elements:
        picture = find_zone(element, pictures)
        if picture is None:
            others.append(element)
        else:
            members_per_picture.setdefault(id(picture), []).append(element)

    for members in members_per_picture.values():

        bbox = pymupdf.Rect(members[0]["bbox"])
        for member in members[1:]:
            bbox |= member["bbox"]

        others.append({"type": "group", "bbox": list(bbox), "members": members})

    return others


def reading_order(elements):

    # Dans chaque morceau du XY-cut : de haut en bas, puis de gauche à droite
    ordered = []

    for zone in xy_cut(elements):
        ordered += sorted(zone, key=lambda e: (e["bbox"][1], e["bbox"][0]))

    return ordered


def order_elements(elements, zones):

    if not elements:
        return []

    ordered = []

    for element in reading_order(group_by_picture(elements, zones)):
        if element["type"] == "group":
            ordered += reading_order(element["members"])  # on rouvre le groupe
        else:
            ordered.append(element)

    return merge_lists_and_tables(ordered)


def merge_lists_and_tables(elements):

    # Chaque puce et chaque ligne de tableau peut être une zone
    # à part. On recolle deux blocs qui se suivent s'ils sont l'un sous
    # l'autre (et pas côte à côte, pour ne pas mélanger deux colonnes).
    merged = []

    for element in elements:

        previous = merged[-1] if merged else None

        if (
            previous is not None
            and previous["type"] == "text" and element["type"] == "text"
            and is_list_or_table(previous["content"])
            and is_list_or_table(element["content"])
            and element["bbox"][0] < previous["bbox"][2]   # se chevauchent
            and previous["bbox"][0] < element["bbox"][2]   # horizontalement
            and element["bbox"][1] - previous["bbox"][3] < 15
        ):
            previous["content"] += "\n" + element["content"]
            previous["bbox"] = list(pymupdf.Rect(previous["bbox"]) | element["bbox"])
        else:
            merged.append(element)

    return merged

