"""Abstract base class for data collectors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from latent_signals.config import Config
from latent_signals.models import RawDocument
from latent_signals.utils.cost_tracker import CostTracker


class Collector(ABC):
    """Base class for all data source collectors."""

    def __init__(self, config: Config, cost_tracker: CostTracker) -> None:
        self.config = config
        self.cost_tracker = cost_tracker

    @abstractmethod
    def collect(self) -> list[RawDocument]:
        """Fetch documents from this source."""
        ...

    @abstractmethod
    def estimate_cost(self) -> float:
        """Estimate API cost for this collection run."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this source."""
        ...
