"""GPT-4o-mini extraction via OpenAI Batch API with Structured Outputs."""

from __future__ import annotations

import json
import time
from pathlib import Path

from openai import OpenAI

from latent_signals.stage5_classification.schemas import FeedbackAnalysis
from latent_signals.utils.logging import get_logger

log = get_logger("llm_extraction")

def _strict_schema() -> dict:
    """Build an OpenAI-compatible strict JSON schema from FeedbackAnalysis."""
    schema = FeedbackAnalysis.model_json_schema()
    # OpenAI strict mode requires: no defaults, additionalProperties: false, all fields required
    for prop in schema.get("properties", {}).values():
        prop.pop("default", None)
    schema["additionalProperties"] = False
    schema["required"] = list(schema.get("properties", {}).keys())
    return schema


SYSTEM_PROMPT = """You are an expert at analyzing community feedback from forums and review sites.
Given a forum post or review, extract structured information about user pain points, feature requests,
urgency level, and any product/company names mentioned.

Focus on specific, actionable insights. Rate urgency based on the language intensity —
words like "desperately", "critical", "blocking" indicate high urgency."""


def extract_batch(
    texts: dict[str, str],
    api_key: str,
    model: str = "gpt-4o-mini",
    use_batch_api: bool = True,
    output_dir: Path | None = None,
) -> dict[str, FeedbackAnalysis]:
    """Extract structured feedback from texts using GPT-4o-mini.

    Args:
        texts: mapping of doc_id -> text
        api_key: OpenAI API key
        model: model to use
        use_batch_api: if True, use Batch API (cheaper, async). If False, use synchronous calls.
        output_dir: directory to save batch results

    Returns:
        Mapping of doc_id -> FeedbackAnalysis
    """
    client = OpenAI(api_key=api_key)

    if use_batch_api and len(texts) > 10:
        return _batch_extract(client, texts, model, output_dir)
    else:
        return _sync_extract(client, texts, model)


def _sync_extract(
    client: OpenAI, texts: dict[str, str], model: str
) -> dict[str, FeedbackAnalysis]:
    """Synchronous extraction for small batches."""
    results: dict[str, FeedbackAnalysis] = {}
    for doc_id, text in texts.items():
        try:
            response = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text[:4000]},  # Truncate to fit context
                ],
                response_format=FeedbackAnalysis,
            )
            if response.choices[0].message.parsed:
                results[doc_id] = response.choices[0].message.parsed
        except Exception as e:
            log.warning("llm.extraction_failed", doc_id=doc_id, error=str(e))

    log.info("llm.sync_complete", extracted=len(results), total=len(texts))
    return results


def _batch_extract(
    client: OpenAI,
    texts: dict[str, str],
    model: str,
    output_dir: Path | None = None,
) -> dict[str, FeedbackAnalysis]:
    """Batch API extraction for large volumes (50% cheaper)."""
    # Build batch requests
    requests = []
    for doc_id, text in texts.items():
        requests.append(
            {
                "custom_id": doc_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text[:4000]},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "FeedbackAnalysis",
                            "strict": True,
                            "schema": _strict_schema(),
                        },
                    },
                },
            }
        )

    # Write JSONL file for batch upload
    batch_input_path = (output_dir or Path(".")) / "batch_input.jsonl"
    batch_input_path.parent.mkdir(parents=True, exist_ok=True)
    with open(batch_input_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")

    # Upload and create batch
    with open(batch_input_path, "rb") as f:
        uploaded = client.files.create(file=f, purpose="batch")

    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
    )
    log.info("batch.created", batch_id=batch.id, n_requests=len(requests))

    # Poll for completion
    while True:
        batch = client.batches.retrieve(batch.id)
        log.info(
            "batch.status",
            status=batch.status,
            completed=batch.request_counts.completed if batch.request_counts else 0,
            total=batch.request_counts.total if batch.request_counts else 0,
        )
        if batch.status in ("completed", "failed", "expired", "cancelled"):
            break
        time.sleep(30)

    if batch.status != "completed":
        log.error("batch.failed", status=batch.status)
        return {}

    # Re-retrieve to ensure output_file_id is populated
    batch = client.batches.retrieve(batch.id)
    if not batch.output_file_id:
        log.error("batch.no_output_file", status=batch.status, error_file=batch.error_file_id)
        # Try to get error details
        if batch.error_file_id:
            error_content = client.files.content(batch.error_file_id).text
            log.error("batch.errors", content=error_content[:1000])
        return {}

    # Download and parse results
    output_content = client.files.content(batch.output_file_id).text
    results: dict[str, FeedbackAnalysis] = {}
    for line in output_content.strip().split("\n"):
        entry = json.loads(line)
        doc_id = entry["custom_id"]
        try:
            body = entry["response"]["body"]
            content = body["choices"][0]["message"]["content"]
            parsed = FeedbackAnalysis.model_validate_json(content)
            results[doc_id] = parsed
        except Exception as e:
            log.warning("batch.parse_failed", doc_id=doc_id, error=str(e))

    # Save raw batch results
    if output_dir:
        with open(output_dir / "llm_batch_results.json", "w") as f:
            f.write(output_content)

    log.info("batch.complete", extracted=len(results), total=len(texts))
    return results
