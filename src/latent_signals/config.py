"""Configuration loading from YAML + environment variables."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class ExaConfig(BaseModel):
    enabled: bool = True
    max_results_per_query: int = 100
    domains: list[str] = Field(default_factory=lambda: ["reddit.com", "news.ycombinator.com"])
    queries: list[str] = Field(default_factory=list)


class SerperConfig(BaseModel):
    enabled: bool = True
    max_results_per_query: int = 100
    site_filters: list[str] = Field(default_factory=lambda: ["reddit.com"])
    queries: list[str] = Field(default_factory=list)


class ApifyConfig(BaseModel):
    enabled: bool = True
    subreddits: list[str] = Field(default_factory=list)
    max_items: int = 10000


class ArcticShiftConfig(BaseModel):
    enabled: bool = False
    subreddits: list[str] = Field(default_factory=list)
    max_items: int = 20000


class HackerNewsConfig(BaseModel):
    enabled: bool = True
    queries: list[str] = Field(default_factory=list)
    max_items: int = 5000


class CollectionConfig(BaseModel):
    date_range: dict[str, str] = Field(default_factory=lambda: {"start": "2024-01-01", "end": "2024-12-31"})
    exa: ExaConfig = Field(default_factory=ExaConfig)
    serper: SerperConfig = Field(default_factory=SerperConfig)
    apify: ApifyConfig = Field(default_factory=ApifyConfig)
    arctic_shift: ArcticShiftConfig = Field(default_factory=ArcticShiftConfig)
    hackernews: HackerNewsConfig = Field(default_factory=HackerNewsConfig)


class PreprocessingConfig(BaseModel):
    min_length: int = 50
    max_length: int = 10000
    language: str = "en"
    minhash_threshold: float = 0.8
    minhash_num_perm: int = 128


class EmbeddingConfig(BaseModel):
    model_name: str = "all-MiniLM-L6-v2"
    batch_size: int = 256
    device: str = "cpu"


class UMAPConfig(BaseModel):
    n_neighbors: int = 15
    n_components: int = 5
    min_dist: float = 0.0
    metric: str = "cosine"


class HDBSCANConfig(BaseModel):
    min_cluster_size: int = 15
    min_samples: int = 5
    metric: str = "euclidean"


class ClusteringConfig(BaseModel):
    umap: UMAPConfig = Field(default_factory=UMAPConfig)
    hdbscan: HDBSCANConfig = Field(default_factory=HDBSCANConfig)
    nr_topics: str | int = "auto"
    top_n_words: int = 10


class ZeroShotConfig(BaseModel):
    model_name: str = "facebook/bart-large-mnli"
    categories: list[str] = Field(
        default_factory=lambda: ["pain point", "feature request", "praise", "question", "bug report"]
    )
    batch_size: int = 32


class LLMExtractionConfig(BaseModel):
    enabled: bool = True
    model: str = "gpt-4o-mini"
    samples_per_cluster: int = 75
    max_clusters: int = 50
    use_batch_api: bool = True


class ClassificationConfig(BaseModel):
    zero_shot: ZeroShotConfig = Field(default_factory=ZeroShotConfig)
    llm_extraction: LLMExtractionConfig = Field(default_factory=LLMExtractionConfig)


class ScoringWeights(BaseModel):
    unaddressedness: float = 0.30
    frequency: float = 0.25
    pain_intensity: float = 0.15
    competitive_whitespace: float = 0.15
    market_size: float = 0.10
    trend_direction: float = 0.05


class ScoringConfig(BaseModel):
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    similarity_threshold: float = 0.5
    top_n_opportunities: int = 10
    competitor_features_file: str = ""


class ReportConfig(BaseModel):
    format: str = "markdown"
    max_quotes_per_gap: int = 20


class PipelineConfig(BaseModel):
    market_category: str = ""
    run_id: str | None = None
    output_dir: str = "data"
    random_seed: int = 42


class Config(BaseModel):
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    collection: CollectionConfig = Field(default_factory=CollectionConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    clustering: ClusteringConfig = Field(default_factory=ClusteringConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    # API keys (loaded from env)
    exa_api_key: str = ""
    serper_api_key: str = ""
    apify_api_token: str = ""
    openai_api_key: str = ""


def load_config(config_path: str | Path) -> Config:
    """Load config from YAML file, overlay environment variables for API keys."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    config = Config(**raw)

    # Overlay API keys from environment
    config.exa_api_key = os.environ.get("EXA_API_KEY", config.exa_api_key)
    config.serper_api_key = os.environ.get("SERPER_API_KEY", config.serper_api_key)
    config.apify_api_token = os.environ.get("APIFY_API_TOKEN", config.apify_api_token)
    config.openai_api_key = os.environ.get("OPENAI_API_KEY", config.openai_api_key)

    return config


def config_hash(config: Config) -> str:
    """Deterministic hash of config for reproducibility tracking."""
    raw = config.model_dump_json(exclude={"pipeline": {"run_id"}})
    return hashlib.sha256(raw.encode()).hexdigest()[:12]
