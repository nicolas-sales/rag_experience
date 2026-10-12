import json
from pathlib import Path

import numpy as np
from langchain_openai import OpenAIEmbeddings


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Lien où est stocké le fichier json savegardé grâce au notebook
SOURCE_ELEMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "source_elements.json"
)


def load_source_elements():
    with open(SOURCE_ELEMENTS_PATH, encoding="utf-8") as f: # encoding="utf-8" -> prise en charge des accents
        return json.load(f) # transformation en objet python (dictionnaire contenant des listes)


def get_element_content(element):
    element_type = element.get("type")

    #Si l'élément est une image, on récupère le texte produit par DePlot
    if element_type == "image":
        return element.get("deplot_clean") or ""

    # Pour un texte ou un tableau, on récupère la représentation textuelle stockée dans le JSON
    if element_type in ("text", "table"):
        return element.get("text") or ""

    return ""


def find_relevant_bbox(
    question: str,
    page_number: int,
    api_key: str
):
    """
    Sélectionne automatiquement la zone la plus pertinente
    sur une page PDF.

    Retourne une bbox [x0, y0, x1, y1] ou None.
    """

    # Chargement des données json
    source_data = load_source_elements()

    # Récupération des éléments de la page sélectionnée
    elements = source_data.get(str(page_number), []) # str car le json contient par exemple "14" et non un nombre entier

    candidates = []

    for element in elements:

        content = get_element_content(element)
        bbox = element.get("bbox")

        if not content.strip() or not bbox:
            continue

        candidates.append({
            "content": content,
            "bbox": bbox,
            "type": element.get("type")
        })

    if not candidates:
        return None

    embeddings = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        api_key=api_key
    )

    texts = [candidate["content"] for candidate in candidates]

    question_vector = np.array(
        embeddings.embed_query(question) # np.array(...) transforme le résultat en tableau NumPy pour les calculs
    )

    element_vectors = np.array(
        embeddings.embed_documents(texts)
    )

    # Calcul de la longueur du vecteur de la question
    question_norm = np.linalg.norm(question_vector)

    # Calcul de la longueur de chaque vecteur candidat
    element_norms = np.linalg.norm(element_vectors, axis=1) # axis=1 signifie qu'on effectue le calcul ligne par ligne : chaque ligne représente un élément

    # Calcul des similarités
    similarities = (
        element_vectors @ question_vector # @ est l'opérateur de multiplication matricielle de Python
    ) / (
        element_norms * question_norm + 1e-12
    )

    best_index = int(np.argmax(similarities))

    best_candidate = candidates[best_index]

    print("=== SOURCE LOCATOR ===")
    print("Question :", question)
    print("Page :", page_number)
    print("Type sélectionné :", best_candidate["type"])
    print("Contenu :", best_candidate["content"][:200])
    print("Score :", float(similarities[best_index]))
    print("BBOX :", best_candidate["bbox"])

    return best_candidate["bbox"]