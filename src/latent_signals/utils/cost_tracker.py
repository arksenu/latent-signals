"""Track API costs per pipeline run."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostTracker:
    """Accumulate API costs by service."""

    costs: dict[str, float] = field(default_factory=dict)

    def add(self, service: str, amount: float) -> None:
        self.costs[service] = self.costs.get(service, 0.0) + amount

    @property
    def total(self) -> float:
        return sum(self.costs.values())

    def summary(self) -> dict[str, float]:
        return {**self.costs, "total": self.total}
