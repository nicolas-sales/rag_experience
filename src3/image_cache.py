import hashlib
import json
from pathlib import Path

# On ajoute donc un cache persistant pour CLIP, DePlot et l'OCR, afin de ne pas refaire les inférences à chaque lancement de src3/ingestion.py.


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cache propre à src3 (copie de celui de src2 au départ)
CACHE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "src3"
    / "image_analysis_cache.json"
)

CACHE_VERSION = 1


def load_image_cache():

    if not CACHE_PATH.exists():
        return {
            "version": CACHE_VERSION,
            "clip": {},
            "deplot": {},
            "ocr": {}
        }

    with open(CACHE_PATH, "r", encoding="utf-8") as file:
        cache = json.load(file)

    if cache.get("version") != CACHE_VERSION:
        raise ValueError(
            "Version du cache incompatible. "
            "Vérifier le cache avant de le réinitialiser."
        )

    cache.setdefault("clip", {})
    cache.setdefault("deplot", {})
    cache.setdefault("ocr", {})

    return cache


def save_image_cache(cache):

    CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Écriture temporaire pour éviter un JSON incomplet
    temporary_path = CACHE_PATH.with_suffix(".tmp")

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(
            cache,
            file,
            ensure_ascii=False,
            indent=2
        )

    temporary_path.replace(CACHE_PATH)


def get_image_hash(storage_path):

    image_path = PROJECT_ROOT / storage_path

    sha256 = hashlib.sha256()

    with open(image_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()