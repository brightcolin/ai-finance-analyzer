"""
Financial Health Score — multi-dimensional weighted scoring system.

Computes a 0-100 score based on:
  - Savings rate (30%)
  - Essential spending ratio (25%)
  - Spending stability (20%)
  - Category diversity (15%)
  - Trend direction (10%)
"""

from __future__ import annotations

import math

from analyzer.core.config import get_config
from analyzer.models.schemas import (
    CategorizedTransaction,
    CategoryBreakdown,
    HealthScore,
)


def compute_health_score(
    transactions: list[CategorizedTransaction],
    breakdowns: list[CategoryBreakdown],
    savings_rate: float,
    volatility_index: float,
    trend_direction: str = "stable",
) -> HealthScore:
    """Compute the overall financial health score.

    Args:
        transactions: Classified expense transactions.
        breakdowns: Category breakdown from structure analysis.
        savings_rate: Computed savings rate (0 to 1).
        volatility_index: Spending volatility index.
        trend_direction: "increasing", "decreasing", or "stable".

    Returns:
        HealthScore with total and component breakdown.
    """
    config = get_config().analyzer

    # Component 1: Savings Rate Score (0-100)
    savings_score = _score_savings_rate(savings_rate)

    # Component 2: Essential Ratio Score (0-100)
    essential_score = _score_essential_ratio(breakdowns, config.essential_categories)

    # Component 3: Stability Score (0-100)
    stability_score = _score_stability(volatility_index)

    # Component 4: Diversity Score (0-100)
    diversity_score = _score_diversity(breakdowns)

    # Component 5: Trend Score (0-100)
    trend_score = _score_trend(trend_direction)

    # Weighted total
    total = (
        savings_score * config.weight_savings_rate
        + essential_score * config.weight_essential_ratio
        + stability_score * config.weight_stability
        + diversity_score * config.weight_diversity
        + trend_score * config.weight_trend
    )

    total = round(min(max(total, 0), 100), 1)

    return HealthScore(
        total_score=total,
        components={
            "savings_rate": round(savings_score, 1),
            "essential_ratio": round(essential_score, 1),
            "stability": round(stability_score, 1),
            "diversity": round(diversity_score, 1),
            "trend": round(trend_score, 1),
        },
    )


def _score_savings_rate(rate: float) -> float:
    """Score savings rate on a 0-100 scale.

    Benchmarks:
      < 0%:    0 points (spending more than earning)
      0-10%:   20-50 points
      10-20%:  50-75 points
      20-30%:  75-90 points
      30%+:    90-100 points
    """
    if rate <= 0:
        return max(0, 20 + rate * 100)  # Graceful degradation for negative
    if rate <= 0.10:
        return 20 + (rate / 0.10) * 30
    if rate <= 0.20:
        return 50 + ((rate - 0.10) / 0.10) * 25
    if rate <= 0.30:
        return 75 + ((rate - 0.20) / 0.10) * 15
    return min(100, 90 + ((rate - 0.30) / 0.20) * 10)


def _score_essential_ratio(
    breakdowns: list[CategoryBreakdown],
    essential_categories: list[str],
) -> float:
    """Score essential spending ratio.

    A healthy budget has essentials at 50-70% of total spending.
    Too high (>80%) means no discretionary room.
    Too low (<30%) may indicate missing essential tracking.
    """
    total = sum(b.total for b in breakdowns)
    if total <= 0:
        return 50.0  # Neutral if no data

    essential = sum(
        b.total for b in breakdowns
        if b.category.value in essential_categories
    )
    ratio = essential / total

    if 0.50 <= ratio <= 0.70:
        return 90 + (1 - abs(ratio - 0.60) / 0.10) * 10
    if 0.40 <= ratio <= 0.80:
        return 70 + (1 - abs(ratio - 0.60) / 0.20) * 20
    if 0.30 <= ratio <= 0.90:
        return 40 + (1 - abs(ratio - 0.60) / 0.30) * 30
    return 20.0


def _score_stability(volatility_index: float) -> float:
    """Score spending stability based on volatility index.

    Lower volatility = higher score.
    """
    if volatility_index <= 0.15:
        return 95
    if volatility_index <= 0.25:
        return 80 + (0.25 - volatility_index) / 0.10 * 15
    if volatility_index <= 0.40:
        return 60 + (0.40 - volatility_index) / 0.15 * 20
    if volatility_index <= 0.60:
        return 35 + (0.60 - volatility_index) / 0.20 * 25
    return max(10, 35 - (volatility_index - 0.60) * 50)


def _score_diversity(breakdowns: list[CategoryBreakdown]) -> float:
    """Score category diversity using Shannon entropy.

    More evenly distributed spending across categories = healthier.
    Avoid over-concentration in any single category.
    """
    if not breakdowns:
        return 50.0

    percentages = [b.percentage for b in breakdowns if b.percentage > 0]
    if len(percentages) <= 1:
        return 30.0

    # Shannon entropy
    entropy = -sum(p * math.log2(p) for p in percentages if p > 0)

    # Max entropy for this number of categories
    max_entropy = math.log2(len(percentages))

    if max_entropy == 0:
        return 50.0

    # Normalize to 0-1
    normalized = entropy / max_entropy

    # Map to score (0.3-1.0 normalized -> 30-100 score)
    return 30 + normalized * 70


def _score_trend(direction: str) -> float:
    """Score spending trend direction.

    Decreasing spending = good (high score).
    Stable = okay.
    Increasing = concerning (low score).
    """
    scores = {
        "decreasing": 90,
        "stable": 70,
        "increasing": 40,
    }
    return scores.get(direction, 60)
