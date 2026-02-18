"""CLI entry point for the Latent Signals pipeline."""

from __future__ import annotations

import click

from latent_signals.config import load_config
from latent_signals.run_pipeline import run_pipeline
from latent_signals.utils.logging import setup_logging


@click.group()
def main() -> None:
    """Latent Signals — detect underserved market opportunities."""
    setup_logging()


@main.command()
@click.option("--config", "config_path", required=True, help="Path to YAML config file")
@click.option("--stages", default=None, help="Comma-separated stage numbers to run (e.g. '1,2,3')")
@click.option("--run-id", default=None, help="Override run ID (auto-generated if not set)")
def run(config_path: str, stages: str | None, run_id: str | None) -> None:
    """Run the pipeline (all stages or a subset)."""
    config = load_config(config_path)
    if run_id:
        config.pipeline.run_id = run_id

    stage_list: list[int] | None = None
    if stages:
        stage_list = [int(s.strip()) for s in stages.split(",")]

    run_pipeline(config, stage_list)


if __name__ == "__main__":
    main()
