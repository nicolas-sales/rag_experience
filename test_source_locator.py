import os
from dotenv import load_dotenv

from src.source_locator import find_relevant_bbox


load_dotenv()

question = "Quel est le chiffre d'affaires 2025 ?"
page_number = 14

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY absente du fichier .env")

bbox = find_relevant_bbox(
    question=question,
    page_number=page_number,
    api_key=api_key
)

print("\n=== RÉSULTAT FINAL ===")
print("BBOX trouvée :", bbox)