from pathlib import Path
from uuid import uuid4

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Plan_stratégique_Impact.pdf"
)

STATIC_DIR = PROJECT_ROOT / "app" / "static"

STATIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def extract_pdf_page(
    page_number: int,
    bboxes: list[list[float]] | None = None
) -> bytes:
    """
    Extrait une page du PDF original et encadre
    tous les éléments indiqués par leurs bbox.
    """

    with pymupdf.open(PDF_PATH) as source_pdf:

        if not 1 <= page_number <= len(source_pdf):
            raise ValueError(
                f"Page invalide : {page_number}"
            )

        with pymupdf.open() as output_pdf:

            # Extraire uniquement la page demandée
            output_pdf.insert_pdf(
                source_pdf,
                from_page=page_number - 1,
                to_page=page_number - 1
            )

            page = output_pdf[0]

            # Dessiner les rectangles
            if bboxes:

                shape = page.new_shape()

                for bbox in bboxes:

                    if not bbox or len(bbox) != 4:
                        continue

                    rect = pymupdf.Rect(bbox)

                    if rect.is_empty or rect.is_infinite:
                        continue

                    shape.draw_rect(rect)

                shape.finish(
                    color=(1, 0, 0),
                    width=2
                )

                shape.commit()

            return output_pdf.tobytes()


def prepare_pdf_source(
    page_number: int,
    bboxes: list[list[float]] | None = None
) -> str:
    """
    Crée un PDF annoté dans app/static/
    et retourne son URL pour Streamlit.
    """

    filename = (
        f"source_page_{page_number}_"
        f"{uuid4().hex[:12]}.pdf"
    )

    output_path = STATIC_DIR / filename

    pdf_bytes = extract_pdf_page(
        page_number=page_number,
        bboxes=bboxes
    )

    output_path.write_bytes(pdf_bytes)

    return f"/app/static/{filename}"