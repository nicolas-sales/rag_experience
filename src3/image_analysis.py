
from pathlib import Path
import time

from src3.image_cache import load_image_cache, save_image_cache, get_image_hash


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CANDIDATE_LABELS = [
    "a chart or graph showing numerical data",
    "a diagram or schematic",
    "an infographic",
    "a map",
    "a logo or decorative graphic",
    "a scanned document",
    "a photograph",
]

DEPLOT_LABELS = {
    "a chart or graph showing numerical data",
    "an infographic",
}

DEPLOT_MIN_SCORE = 0.50


# --------------------------------------------------
# Classification CLIP
# --------------------------------------------------

def classify_images(pages_document, image_bank):

    from transformers import pipeline

    loading_start = time.perf_counter()

    cache = load_image_cache()

    image_classifier = None

    #image_classifier = pipeline(
        #task="zero-shot-image-classification",
        #model="openai/clip-vit-base-patch32",
        #device=-1
    #)

    print(
        "CLIP loading time:",
        round(time.perf_counter() - loading_start, 2),
        "seconds"
    )

    asset_paths = {
        record["asset_id"]: record["storage_path"]
        for record in image_bank
    }

    clip_start = time.perf_counter()
    clip_calls = 0
    clip_inference_duration = 0.0

    for page_data in pages_document:

        for element in page_data["elements"]:

            if element["type"] != "image":
                continue

            # Restauration du chemin si nécessaire
            if "storage_path" not in element:

                asset_id = element["asset_id"]

                if asset_id not in asset_paths:
                    print("No file found for:", element["image_id"])
                    continue

                element["storage_path"] = asset_paths[asset_id]

            image_path = PROJECT_ROOT / element["storage_path"]

            # Inférence CLIP
            image_start = time.perf_counter()

            image_hash = get_image_hash(element["storage_path"])

            clip_cache_key = (
                f"openai/clip-vit-base-patch32:"
                f"{DEPLOT_MIN_SCORE}:"
                f"{'|'.join(CANDIDATE_LABELS)}:"
                f"{image_hash}"
            )

            if clip_cache_key in cache["clip"]:

                element.update(cache["clip"][clip_cache_key])

                print("CLIP cache hit:", element["image_id"])
                continue

            # Charger CLIP uniquement si une image
            # n'est pas présente dans le cache
            if image_classifier is None:

                from transformers import pipeline

                loading_start = time.perf_counter()

                image_classifier = pipeline(
                    task="zero-shot-image-classification",
                    model="openai/clip-vit-base-patch32",
                    device=-1
                )

                print(
                    "CLIP loading time:",
                    round(time.perf_counter() - loading_start, 2),
                    "seconds"
                )

            results = image_classifier(
                str(image_path),
                candidate_labels=CANDIDATE_LABELS
            )

            image_duration = time.perf_counter() - image_start

            clip_calls += 1
            clip_inference_duration += image_duration

            best_result = results[0]

            element["image_category"] = best_result["label"]
            element["classification_score"] = float(
                best_result["score"]
            )

            element["classification_results"] = [
                {
                    "label": result["label"],
                    "score": float(result["score"])
                }
                for result in results
            ]

            # Meilleure catégorie candidate DePlot
            deplot_results = [
                result
                for result in results
                if result["label"] in DEPLOT_LABELS
            ]

            best_deplot_result = max(
                deplot_results,
                key=lambda result: result["score"]
            )

            element["deplot_candidate_type"] = (
                best_deplot_result["label"]
            )

            element["deplot_score"] = float(
                best_deplot_result["score"]
            )

            # Meilleure catégorie non candidate
            non_deplot_results = [
                result
                for result in results
                if result["label"] not in DEPLOT_LABELS
            ]

            best_non_deplot_result = max(
                non_deplot_results,
                key=lambda result: result["score"]
            )

            element["non_deplot_type"] = (
                best_non_deplot_result["label"]
            )

            element["non_deplot_score"] = float(
                best_non_deplot_result["score"]
            )

            # Décision DePlot
            if (
                best_result["label"]
                == "a chart or graph showing numerical data"
                and element["classification_score"] >= DEPLOT_MIN_SCORE
            ):
                chart_decision = "chart"
                is_chart = True

            elif (
                best_result["label"] == "an infographic"
                and element["classification_score"] >= DEPLOT_MIN_SCORE
            ):
                chart_decision = "possible_chart"
                is_chart = True

            else:
                chart_decision = "not_chart"
                is_chart = False

            element["chart_decision"] = chart_decision
            element["is_chart"] = is_chart
            element["clip_inference_time"] = image_duration

            # Sauvegarde CLIP uniquement après avoir rempli tous les champs
            clip_fields = (
                "image_category",
                "classification_score",
                "classification_results",
                "deplot_candidate_type",
                "deplot_score",
                "non_deplot_type",
                "non_deplot_score",
                "chart_decision",
                "is_chart",
                "clip_inference_time"
            )

            cache["clip"][clip_cache_key] = {
                key: element[key]
                for key in clip_fields
            }

            save_image_cache(cache)

            print(
                element["image_id"],
                "| Category:", element["image_category"],
                "| Score:", round(element["classification_score"], 3),
                "| DePlot candidate:", element["deplot_candidate_type"],
                "| DePlot score:", round(element["deplot_score"], 3),
                "| Decision:", chart_decision,
                "| Latency:", round(image_duration, 3), "s"
            )

    clip_total_duration = time.perf_counter() - clip_start

    print("\n=== CLIP STATISTICS ===")
    print("Number of calls:", clip_calls)
    print("Inference time:", round(clip_inference_duration, 2), "s")
    print("Total time:", round(clip_total_duration, 2), "s")

    if clip_calls:
        print(
            "Average inference:",
            round(clip_inference_duration / clip_calls, 3),
            "s"
        )

    return clip_calls


# --------------------------------------------------
# Analyse DePlot
# --------------------------------------------------

def run_deplot(pages_document):

    from transformers import (
        Pix2StructProcessor,
        Pix2StructForConditionalGeneration
    )
    from PIL import Image
    import torch

    deplot_candidates = [
        element
        for page_data in pages_document
        for element in page_data["elements"]
        if (
            element["type"] == "image"
            and element.get("is_chart", False)
            and "storage_path" in element
        )
    ]

    print("\nDePlot candidates:", len(deplot_candidates))

    if not deplot_candidates:
        return 0

    cache = load_image_cache()

    deplot_processor = None
    deplot_model = None

    #loading_start = time.perf_counter()

    #deplot_processor = Pix2StructProcessor.from_pretrained(
        #"google/deplot"
    #)

    #deplot_model = Pix2StructForConditionalGeneration.from_pretrained(
        #"google/deplot"
    #)

    #deplot_model.eval()

    #print(
        #"DePlot loading time:",
        #"round(time.perf_counter() - loading_start, 2),
        #"seconds"
    #)

    deplot_cache = {}

    deplot_start = time.perf_counter()
    deplot_calls = 0
    deplot_cache_hits = 0
    deplot_processing_duration = 0.0

    for element in deplot_candidates:

        asset_id = element["asset_id"]

        # Cache des occurrences de la même image
        if asset_id in deplot_cache:

            element["deplot_raw"] = deplot_cache[asset_id]
            element["deplot_from_cache"] = True

            deplot_cache_hits += 1
            continue

        print("\nAnalyzing with DePlot:", element["image_id"])

        chart_start = time.perf_counter()

        image_path = PROJECT_ROOT / element["storage_path"]

        try:
            with Image.open(image_path) as image:
                chart_image = image.convert("RGB")

        except Exception as error:
            print("Error loading image:", element["image_id"], error)
            continue

        image_hash = get_image_hash(element["storage_path"])

        deplot_cache_key = (
            f"google/deplot:max_new_tokens=256:"
            f"{image_hash}"
        )

        if deplot_cache_key in cache["deplot"]:

            element["deplot_raw"] = cache["deplot"][deplot_cache_key]
            element["deplot_from_cache"] = True

            deplot_cache_hits += 1

            print("DePlot cache hit:", element["image_id"])
            continue

        # Charger DePlot uniquement lors du premier cache miss
        if deplot_model is None:

            from transformers import (
                Pix2StructProcessor,
                Pix2StructForConditionalGeneration
            )

            loading_start = time.perf_counter()

            deplot_processor = Pix2StructProcessor.from_pretrained(
                "google/deplot"
            )

            deplot_model = (
                Pix2StructForConditionalGeneration.from_pretrained(
                    "google/deplot"
                )
            )

            deplot_model.eval()

            print(
                "DePlot loading time:",
                round(time.perf_counter() - loading_start, 2),
                "seconds"
            )

        model_inputs = deplot_processor(
            images=chart_image,
            text="Generate underlying data table of the figure below:",
            return_tensors="pt"
        )

        with torch.inference_mode():
            predictions = deplot_model.generate(
                **model_inputs,
                max_new_tokens=256
            )

        raw_chart_table = deplot_processor.decode(
            predictions[0],
            skip_special_tokens=True
        )

        cache["deplot"][deplot_cache_key] = raw_chart_table

        save_image_cache(cache)

        chart_duration = time.perf_counter() - chart_start

        deplot_cache[asset_id] = raw_chart_table

        element["deplot_raw"] = raw_chart_table
        element["deplot_inference_time"] = chart_duration
        element["deplot_from_cache"] = False

        deplot_calls += 1
        deplot_processing_duration += chart_duration

        print(
            element["image_id"],
            "| DePlot time:",
            round(chart_duration, 2),
            "seconds"
        )

        print("DePlot result:")
        print(raw_chart_table)

    deplot_total_duration = time.perf_counter() - deplot_start

    print("\n=== DEPLOT STATISTICS ===")
    print("Unique model calls:", deplot_calls)
    print("Cache hits:", deplot_cache_hits)
    print("Processing time:", round(deplot_processing_duration, 2), "s")
    print("Total loop time:", round(deplot_total_duration, 2), "s")

    if deplot_calls:
        print(
            "Average model call:",
            round(deplot_processing_duration / deplot_calls, 2),
            "s"
        )

    return deplot_calls


# --------------------------------------------------
# Validation des résultats DePlot
# --------------------------------------------------

def is_number(value):

    try:
        float(
            value.strip()
            .replace("%", "")
            .replace(",", ".")
            .replace(" ", "")
        )
        return True

    except ValueError:
        return False


def validate_deplot_result(text):

    if not text:
        return False

    text = text.strip()

    if len(text) < 10:
        return False

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) < 2:
        return False

    table_lines = [
        line for line in lines
        if "|" in line
    ]

    if len(table_lines) < 2:
        return False

    parsed_rows = [
        [cell.strip() for cell in line.split("|")]
        for line in table_lines
    ]

    column_counts = [
        len(row) for row in parsed_rows
    ]

    dominant_column_count = max(
        set(column_counts),
        key=column_counts.count
    )

    if dominant_column_count < 2:
        return False

    consistent_rows = [
        row
        for row in parsed_rows
        if len(row) == dominant_column_count
    ]

    if len(consistent_rows) < 2:
        return False

    consistency_ratio = len(consistent_rows) / len(lines)

    if consistency_ratio < 0.5:
        return False

    numeric_cells = sum(
        1
        for row in consistent_rows
        for cell in row
        if is_number(cell)
    )

    if numeric_cells < 2:
        return False

    return True


# --------------------------------------------------
# Parsing des tableaux DePlot
# --------------------------------------------------

def parse_deplot_table(text):

    if not text:
        return None

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    title = None

    if lines[0].upper().startswith("TITLE"):

        title_parts = [
            part.strip()
            for part in lines[0].split("|")
        ]

        if len(title_parts) >= 2:
            title = " | ".join(title_parts[1:]).strip() or None

        lines = lines[1:]

    table_lines = [
        line
        for line in lines
        if "|" in line
    ]

    if len(table_lines) < 2:
        return None

    parsed_lines = [
        [cell.strip() for cell in line.split("|")]
        for line in table_lines
    ]

    column_counts = [
        len(row) for row in parsed_lines
    ]

    dominant_column_count = max(
        set(column_counts),
        key=column_counts.count
    )

    consistent_rows = [
        row
        for row in parsed_lines
        if len(row) == dominant_column_count
    ]

    if len(consistent_rows) < 2:
        return None

    return {
        "title": title,
        "columns": consistent_rows[0],
        "rows": consistent_rows[1:]
    }


# --------------------------------------------------
# Nettoyage et finalisation DePlot
# --------------------------------------------------

def finalize_deplot(pages_document):

    for page_data in pages_document:

        for element in page_data["elements"]:

            if element["type"] != "image":
                continue

            # Supprime un ancien parsing éventuel
            element.pop("deplot_parsed", None)

            # Nettoyage des sauts de ligne : DePlot écrit "<0x0A>"
            # ("&lt;0x0A&gt;" est seulement son affichage en HTML)
            if "deplot_raw" in element:

                element["deplot_clean"] = (
                    element["deplot_raw"]
                    .replace("<0x0A>", "\n")
                )

            # Validation et parsing
            if "deplot_clean" in element:

                element["deplot_valid"] = validate_deplot_result(
                    element["deplot_clean"]
                )

                if element["deplot_valid"]:
                    element["deplot_parsed"] = parse_deplot_table(
                        element["deplot_clean"]
                    )

            element["use_deplot_for_rag"] = (
                element.get("deplot_valid", False)
            )
