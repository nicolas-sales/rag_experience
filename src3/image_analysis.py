
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

CHART_LABELS = {
    "a chart or graph showing numerical data",
    "an infographic",
}

CHART_MIN_SCORE = 0.50


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
                f"{CHART_MIN_SCORE}:"
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

            # Meilleure catégorie "graphique"
            deplot_results = [
                result
                for result in results
                if result["label"] in CHART_LABELS
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
                if result["label"] not in CHART_LABELS
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

            # Décision : graphique ou non (lu ensuite par l'OCR)
            if (
                best_result["label"]
                == "a chart or graph showing numerical data"
                and element["classification_score"] >= CHART_MIN_SCORE
            ):
                chart_decision = "chart"
                is_chart = True

            elif (
                best_result["label"] == "an infographic"
                and element["classification_score"] >= CHART_MIN_SCORE
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
                "| Graphique candidat:", element["deplot_candidate_type"],
                "| Score graphique:", round(element["deplot_score"], 3),
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
