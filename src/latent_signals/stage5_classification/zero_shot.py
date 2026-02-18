"""Zero-shot classification using facebook/bart-large-mnli."""

from __future__ import annotations

from transformers import pipeline

from latent_signals.utils.logging import get_logger

log = get_logger("zero_shot")

# Category mapping from human-readable to model labels
CATEGORY_MAP = {
    "pain point": "pain_point",
    "feature request": "feature_request",
    "praise": "praise",
    "question": "question",
    "bug report": "bug_report",
}


class ZeroShotClassifier:
    """Classify documents into categories using zero-shot NLI."""

    def __init__(self, model_name: str = "facebook/bart-large-mnli", device: int = -1) -> None:
        log.info("zero_shot.loading", model=model_name)
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=device,
        )
        self.categories = list(CATEGORY_MAP.keys())

    def classify(self, text: str) -> tuple[str, float]:
        """Classify a single text. Returns (category_key, confidence)."""
        result = self.classifier(text, self.categories, multi_label=False)
        top_label = result["labels"][0]
        top_score = result["scores"][0]
        return CATEGORY_MAP.get(top_label, "question"), top_score

    def classify_batch(
        self, texts: list[str], batch_size: int = 32
    ) -> list[tuple[str, float]]:
        """Classify a batch of texts. Returns list of (category_key, confidence)."""
        # Truncate to ~512 chars (~128 tokens) — bart-large-mnli is very slow on long texts
        truncated = [t[:512] for t in texts]
        log.info("zero_shot.classifying", count=len(truncated), batch_size=batch_size)

        output: list[tuple[str, float]] = []
        for i in range(0, len(truncated), batch_size):
            chunk = truncated[i : i + batch_size]
            results = self.classifier(
                chunk, self.categories, batch_size=batch_size, multi_label=False
            )
            for result in results:
                top_label = result["labels"][0]
                top_score = result["scores"][0]
                output.append((CATEGORY_MAP.get(top_label, "question"), top_score))
            log.info("zero_shot.progress", done=len(output), total=len(truncated))

        return output
