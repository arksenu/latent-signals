"""Generate Markdown gap report from scored opportunities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from latent_signals.models import GapOpportunity, PipelineRunMeta
from latent_signals.utils.logging import get_logger

log = get_logger("report")


def generate_report(
    opportunities: list[GapOpportunity],
    market_category: str,
    run_id: str,
    output_path: Path,
    max_quotes_per_gap: int = 20,
    weights: dict[str, float] | None = None,
) -> str:
    """Generate a Markdown gap report."""
    lines: list[str] = []

    lines.append(f"# Gap Report: {market_category}")
    lines.append(f"")
    lines.append(f"**Run ID:** {run_id}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Opportunities Found:** {len(opportunities)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary table
    lines.append("## Ranked Opportunities")
    lines.append("")
    lines.append("| Rank | Gap | Score | Mentions | Unaddressed | Pain | Whitespace |")
    lines.append("|------|-----|-------|----------|-------------|------|------------|")
    for i, gap in enumerate(opportunities, 1):
        bd = gap.score_breakdown
        lines.append(
            f"| {i} | {gap.label} | **{gap.gap_score:.3f}** | {gap.mention_count} "
            f"| {bd.get('unaddressedness', 0):.2f} | {bd.get('pain_intensity', 0):.2f} "
            f"| {bd.get('competitive_whitespace', 0):.2f} |"
        )
    lines.append("")

    # Detailed per-gap sections
    for i, gap in enumerate(opportunities, 1):
        lines.append(f"## {i}. {gap.label}")
        lines.append("")
        lines.append(f"**Gap Score:** {gap.gap_score:.4f}  ")
        lines.append(f"**Gap ID:** `{gap.gap_id}`  ")
        lines.append(f"**Mentions:** {gap.mention_count}  ")
        lines.append(f"**Max Similarity to Features:** {gap.max_similarity_to_features:.3f}  ")
        lines.append(f"**Trend Slope:** {gap.trend_slope:.4f}")
        lines.append("")

        # Score breakdown
        lines.append("### Score Breakdown")
        lines.append("")
        lines.append("| Component | Value | Weight | Contribution |")
        lines.append("|-----------|-------|--------|--------------|")
        weight_map = weights or {
            "unaddressedness": 0.30,
            "frequency": 0.25,
            "pain_intensity": 0.15,
            "competitive_whitespace": 0.15,
            "market_size": 0.10,
            "trend_direction": 0.05,
        }
        for comp, value in gap.score_breakdown.items():
            w = weight_map.get(comp, 0)
            lines.append(f"| {comp} | {value:.4f} | {w:.2f} | {value * w:.4f} |")
        lines.append("")

        # Competitive whitespace
        if gap.competitive_whitespace:
            lines.append("### Competitive Coverage")
            lines.append("")
            for competitor, sim in sorted(gap.competitive_whitespace.items(), key=lambda x: x[1]):
                bar = "█" * int(sim * 20) + "░" * (20 - int(sim * 20))
                lines.append(f"- **{competitor}:** {bar} ({sim:.3f})")
            lines.append("")

        # Representative quotes
        quotes = gap.representative_quotes[:max_quotes_per_gap]
        if quotes:
            lines.append("### Representative Quotes")
            lines.append("")
            for q in quotes:
                # Clean and truncate
                clean = q.replace("\n", " ").strip()
                if len(clean) > 250:
                    clean = clean[:250] + "..."
                lines.append(f"> {clean}")
                lines.append("")

        lines.append("---")
        lines.append("")

    report = "\n".join(lines)

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    log.info("report.generated", path=str(output_path), n_gaps=len(opportunities))
    return report
