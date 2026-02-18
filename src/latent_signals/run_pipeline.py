"""Main pipeline orchestrator — runs stages 1-6 sequentially."""

from __future__ import annotations

import time
from uuid import uuid4

from latent_signals.config import Config, config_hash
from latent_signals.models import PipelineRunMeta
from latent_signals.utils.cost_tracker import CostTracker
from latent_signals.utils.logging import get_logger

log = get_logger("pipeline")


def _should_run(stage: int, stages: list[int] | None) -> bool:
    return stages is None or stage in stages


def run_pipeline(config: Config, stages: list[int] | None = None) -> None:
    """Run the full pipeline or specific stages."""
    run_id = config.pipeline.run_id or str(uuid4())[:8]
    config.pipeline.run_id = run_id
    cost_tracker = CostTracker()

    meta = PipelineRunMeta(
        run_id=run_id,
        market_category=config.pipeline.market_category,
        started_at=time.time(),  # type: ignore[arg-type]
        config_hash=config_hash(config),
    )

    log.info("pipeline.start", run_id=run_id, market=config.pipeline.market_category, stages=stages)

    if _should_run(1, stages):
        log.info("stage.start", stage=1, name="collection")
        t0 = time.time()
        from latent_signals.stage1_collection import run as run_stage1

        run_stage1(config, run_id, cost_tracker)
        meta.stage_durations["collection"] = time.time() - t0

    if _should_run(2, stages):
        log.info("stage.start", stage=2, name="preprocessing")
        t0 = time.time()
        from latent_signals.stage2_preprocessing import run as run_stage2

        run_stage2(config, run_id)
        meta.stage_durations["preprocessing"] = time.time() - t0

    if _should_run(3, stages):
        log.info("stage.start", stage=3, name="embedding")
        t0 = time.time()
        from latent_signals.stage3_embedding import run as run_stage3

        run_stage3(config, run_id)
        meta.stage_durations["embedding"] = time.time() - t0

    if _should_run(4, stages):
        log.info("stage.start", stage=4, name="clustering")
        t0 = time.time()
        from latent_signals.stage4_clustering import run as run_stage4

        run_stage4(config, run_id)
        meta.stage_durations["clustering"] = time.time() - t0

    if _should_run(5, stages):
        log.info("stage.start", stage=5, name="classification")
        t0 = time.time()
        from latent_signals.stage5_classification import run as run_stage5

        run_stage5(config, run_id, cost_tracker)
        meta.stage_durations["classification"] = time.time() - t0

    if _should_run(6, stages):
        log.info("stage.start", stage=6, name="scoring")
        t0 = time.time()
        from latent_signals.stage6_scoring import run as run_stage6

        run_stage6(config, run_id)
        meta.stage_durations["scoring"] = time.time() - t0

    meta.api_costs = cost_tracker.summary()
    log.info("pipeline.complete", run_id=run_id, costs=meta.api_costs, durations=meta.stage_durations)
