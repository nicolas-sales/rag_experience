"""
Mise en page : remettre les éléments d'une page dans l'ordre de lecture.

Étapes :
    1. extract_lines     : lignes de texte visibles, avec leur position
       find_repeated_lines : menus / pieds de page répétés, à retirer
    2. merge_same_row   : cellules d'un tableau et puces recollées sur une ligne
    3. xy_cut            : découpage de la page en zones (ordre de lecture)
    4. order_elements    : une zone de texte = un bloc ; listes et tableaux recollés
    5. mark_headings     : les blocs écrits en grand sont des titres
"""

import pymupdf


# --------------------------------------------------
# 1. Lignes de texte visibles
# --------------------------------------------------

def extract_lines(page):

    lines = []

    for block in page.get_text("dict")["blocks"]:

        if block["type"] != 0:  # 0 = texte, 1 = image
            continue

        for line in block["lines"]:

            # alpha == 0 : texte invisible (zones de survol PowerPoint)
            spans = [s for s in line["spans"] if s["alpha"] > 0 and s["text"].strip()]

            if not spans:
                continue

            # On recolle les morceaux de la ligne. S'il y a un écart entre
            # deux morceaux ("1" puis "Sensibiliser"), on ajoute un espace.
            text = spans[0]["text"]
            for previous, span in zip(spans, spans[1:]):
                if span["bbox"][0] - previous["bbox"][2] > 2:
                    text += " "
                text += span["text"]

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
# 1 bis. Menus et pieds de page répétés sur chaque page
# --------------------------------------------------

def is_in_margin(line, page):
    # Tout en haut (12 % de la hauteur) ou tout en bas (10 %) de la page
    height = page.rect.height
    return line["bbox"][3] < 0.12 * height or line["bbox"][1] > 0.90 * height


def find_repeated_lines(doc):

    # Pour chaque texte placé en haut ou en bas : sur quelles pages il apparaît
    pages_per_text = {}

    for page in doc:
        for line in extract_lines(page):
            if is_in_margin(line, page):
                pages_per_text.setdefault(line["content"], set()).add(page.number)

    # Répété sur au moins 3 pages : c'est un menu ou un pied de page
    return {text for text, pages in pages_per_text.items() if len(pages) >= 3}


# --------------------------------------------------
# 2. Textes courts sur une même ligne -> une seule ligne
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
# 3. Ordre de lecture : on coupe la page le long du plus grand
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
# 4. Une zone de texte -> un bloc
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


def order_elements(elements):

    if not elements:
        return []

    body_size = body_font_size(elements)
    ordered = []

    for zone in xy_cut(elements):

        # Dans une zone : de haut en bas, puis de gauche à droite
        zone = sorted(zone, key=lambda e: (e["bbox"][1], e["bbox"][0]))
        text_lines = []

        for element in zone:
            if element["type"] == "text":
                text_lines.append(element)
            else:
                # Une image ou un tableau : on ferme le bloc de texte en cours
                if text_lines:
                    ordered.append(make_block(text_lines))
                    text_lines = []
                ordered.append(element)

        if text_lines:
            ordered.append(make_block(text_lines))

    ordered = merge_lists_and_tables(ordered)
    mark_headings(ordered, body_size)

    return ordered


def merge_lists_and_tables(elements):

    # Chaque puce et chaque ligne de tableau sort de xy_cut comme une zone
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


# --------------------------------------------------
# 5. Titres : texte court écrit nettement plus grand que le reste
# --------------------------------------------------

def body_font_size(elements):

    # Taille du texte "normal" : celle qui couvre le plus de caractères
    characters_per_size = {}

    for element in elements:
        if element["type"] == "text":
            size = round(element["size"])
            characters_per_size[size] = characters_per_size.get(size, 0) + len(element["content"])

    return max(characters_per_size, key=characters_per_size.get, default=10)


def mark_headings(elements, body_size):

    for element in elements:

        if element["type"] != "text":
            continue

        text = element["content"]

        element["is_heading"] = (
            element["size"] >= 1.3 * body_size
            and len(text) <= 100
            and not is_list_or_table(text)
            and sum(c.isalpha() for c in text) >= 3  # pas un chiffre clé ("82,7")
        )
