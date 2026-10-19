import hashlib
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

def compute_image_hash(image_path):
    """
    Compute SHA-256 hash of an image file.
    """
    sha256 = hashlib.sha256()

    with open(image_path, "rb") as file: # imege en mode binaire (rb: read binary)
        for chunk in iter(lambda: file.read(65536), b""): # lecture du fichier par morceaux de 65 536 octets, soit 64 Kio pour éviter de charger entièrement les grosses images en mémoire
            sha256.update(chunk) # chaque morceau au calcul du hash

    return sha256.hexdigest() # récupération de l'empreinte finale sous forme de chaine de caractères


def find_duplicate_images(image_bank_path):
    """
    Find exact duplicate images without deleting files.
    """
    image_bank_path = Path(image_bank_path)

    images_by_hash = {} # dictionnaire qui mémorise les empreintes déjà rencontrées
    images = [] # liste qui contiendra les résultats pour chaque image

    for image_path in sorted(image_bank_path.rglob("*")): # rglob("*") parcourt récursivement le dossier et tous ses sous-dossiers
        if not image_path.is_file(): # ignore les dossiers
            continue

        if image_path.suffix.lower() not in IMAGE_EXTENSIONS: # ignore les fichiers dont l'extension n'est pas dans IMAGE_EXTENSIONS
            continue

        image_hash = compute_image_hash(image_path)

        relative_path = image_path.relative_to(image_bank_path).as_posix() # transforme le chemin en chemin relatif. Par exzemple obtenir page_16/image_2.png au lien de tout le lien du fichier. Plus pratique pour enregistrer les résultats dans un JSON

        # Identification des doublons
        if image_hash in images_by_hash:
            duplicate_of = images_by_hash[image_hash]

        else:
            duplicate_of = None
            images_by_hash[image_hash] = relative_path

        images.append({
            "image_path": relative_path,
            "sha256": image_hash,
            "is_duplicate": duplicate_of is not None,
            "duplicate_of": duplicate_of
        })

    return {
        "total_images": len(images),
        "unique_images": len(images_by_hash),
        "duplicate_images": (
            len(images) - len(images_by_hash)
        ),
        "images": images
    }



if __name__=="__main__":
    import json
    PROJECT_ROOT  = Path(__file__).resolve().parent.parent

    IMAGE_BANK_PATH = PROJECT_ROOT / "image_bank" / "MEC 002_Blue Data 2_Lot 1_B4ALL_Réponse technique"

    OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "images_index.json"

    results = find_duplicate_images(IMAGE_BANK_PATH)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print("Total images:", results["total_images"])
    print("Unique images:", results["unique_images"])
    print("Duplicate images:", results["duplicate_images"])