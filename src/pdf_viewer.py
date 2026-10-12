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
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_page(page_number: int, bbox=None) -> bytes:
    """Extrait une page PDF et encadre la zone sélectionnée."""

    with pymupdf.open(PDF_PATH) as source_pdf:

        if not 1 <= page_number <= len(source_pdf):
            raise ValueError(f"Page invalide : {page_number}")

        with pymupdf.open() as output_pdf:

            output_pdf.insert_pdf(
                source_pdf,
                from_page=page_number - 1,
                to_page=page_number - 1
            )

            if bbox is not None:

                page = output_pdf[0]

                shape = page.new_shape()
                shape.draw_rect(pymupdf.Rect(bbox))

                shape.finish(
                    color=(1, 0, 0),
                    width=2
                )

                shape.commit()

            return output_pdf.tobytes()


def prepare_pdf_source(page_number: int, bbox=None) -> str:
    """Crée un PDF annoté et retourne son URL Streamlit."""

    # Nom unique pour éviter de réutiliser un ancien PDF
    filename = f"source_page_{page_number}_{uuid4().hex[:12]}.pdf"

    output_path = STATIC_DIR / filename

    output_path.write_bytes(
        extract_pdf_page(
            page_number=page_number,
            bbox=bbox
        )
    )

    return f"/app/static/{filename}"