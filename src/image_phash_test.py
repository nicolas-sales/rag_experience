
import json
from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError


IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

# Distance maximale pour considérer deux images comme similaires.
# Valeur de départ expérimentale, à ajuster après les tests.
PHASH_THRESHOLD = 10



def compute_image_phash(image_path):
    """
    Compute the perceptual hash (pHash) of an image.
    """
    with Image.open(image_path) as image:
        return imagehash.phash(image.convert("RGB"))


def find_similar_images(image_bank_path, threshold=PHASH_THRESHOLD):
    """
    Find visually similar images using pHash.

    Does not delete or modify any image.
    """
    image_bank_path = Path(image_bank_path)

    if not image_bank_path.is_dir():
        raise FileNotFoundError(
            f"Image folder not found: {image_bank_path}"
        )

    # Images déjà rencontrées, avec leur pHash.
    known_images = []

    # Résultat détaillé pour chaque image.
    images = []

    for image_path in sorted(image_bank_path.rglob("*")):

        if not image_path.is_file():
            continue

        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        relative_path = image_path.relative_to(
            image_bank_path
        ).as_posix()

        try:
            image_phash = compute_image_phash(image_path)

        except (OSError, ValueError, UnidentifiedImageError) as error:
            print(f"Image ignored: {relative_path} ({error})")
            continue

        # On recherche l'image déjà rencontrée ayant
        # la plus petite distance de Hamming.
        closest_image = None
        minimum_distance = None

        for known_image in known_images:

            distance = int(image_phash - known_image["phash"])

            if (
                minimum_distance is None
                or distance < minimum_distance
            ):
                minimum_distance = distance
                closest_image = known_image["image_path"]

        # On considère l'image comme similaire si la
        # distance minimale est inférieure au seuil.
        is_similar = (
            minimum_distance is not None
            and minimum_distance <= threshold
        )

        images.append({
            "image_path": relative_path,
            "phash": str(image_phash),
            "is_similar": is_similar,
            "similar_to": closest_image if is_similar else None,
            "distance": minimum_distance,
        })

        # On garde toutes les images pour les comparaisons
        # suivantes, même celles considérées similaires.
        known_images.append({
            "image_path": relative_path,
            "phash": image_phash
        })

    similar_images = sum(
        image["is_similar"] for image in images
    )

    return {
        "threshold": threshold,
        "total_images": len(images),
        "similar_images": similar_images,
        "images_without_similar_predecessor": (
            len(images) - similar_images
        ),
        "images": images
    }


if __name__ == "__main__":

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    IMAGE_BANK_PATH = (
        PROJECT_ROOT / "image_bank" / "test_logo"
    )

    OUTPUT_PATH = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "images_phash_TEST.json"
    )

    results = find_similar_images(IMAGE_BANK_PATH)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Total images:", results["total_images"])
    print("Similar images:", results["similar_images"])
    print(
        "Images without similar predecessor:",
        results["images_without_similar_predecessor"]
    )

    print("\nComparison details:")

    for image in results["images"]:
        print(
            image["image_path"],
            "| similar_to:", image["similar_to"],
            "| distance:", image["distance"]
        )
