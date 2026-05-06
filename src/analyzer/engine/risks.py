"""
Risk detection — identifies concerning spending patterns.

Generates actionable risk alerts based on configurable thresholds.
"""

from __future__ import annotations

from analyzer.core.config import get_config
from analyzer.models.schemas import (
    CategoryBreakdown,
    RiskAlert,
    TrendAnalysis,
)


def detect_risks(
    breakdowns: list[CategoryBreakdown],
    savings_rate: float,
    volatility_index: float,
    overall_trend: TrendAnalysis | None = None,
    category_trends: list[TrendAnalysis] | None = None,
) -> list[RiskAlert]:
    """Run all risk detection checks and return alerts.

    Args:
        breakdowns: Category breakdown from structure analysis.
        savings_rate: Computed savings rate.
        volatility_index: Spending volatility index.
        overall_trend: Overall spending trend.
        category_trends: Per-category trends.

    Returns:
        List of RiskAlert objects sorted by severity.
    """
    config = get_config().analyzer
    alerts: list[RiskAlert] = []

    # Check 1: Category over-concentration
    for breakdown in breakdowns:
        if breakdown.percentage > config.high_category_threshold:
            alerts.append(
                RiskAlert(
                    level="high" if breakdown.percentage > 0.45 else "medium",
                    category=breakdown.category.value,
                    message=(
                        f"{breakdown.category.value} spending accounts for "
                        f"{breakdown.percentage:.0%} of total expenses, "
                        f"exceeding the {config.high_category_threshold:.0%} threshold"
                    ),
                    value=breakdown.percentage,
                    threshold=config.high_category_threshold,
                )
            )

    # Check 2: Low savings rate
    if savings_rate < config.min_savings_rate:
        level = "high" if savings_rate < 0 else "medium"
        alerts.append(
            RiskAlert(
                level=level,
                category="savings",
                message=(
                    f"Savings rate is {savings_rate:.1%}, "
                    f"below the recommended minimum of {config.min_savings_rate:.0%}"
                ),
                value=savings_rate,
                threshold=config.min_savings_rate,
            )
        )

    # Check 3: High volatility
    if volatility_index > 0.5:
        alerts.append(
            RiskAlert(
                level="medium",
                category="stability",
                message=(
                    f"Spending volatility index is {volatility_index:.2f}, "
                    f"indicating inconsistent spending patterns"
                ),
                value=volatility_index,
                threshold=0.5,
            )
        )

    # Check 4: Spending trend increasing
    if overall_trend and overall_trend.direction == "increasing":
        if overall_trend.avg_change_rate > 0.15:
            alerts.append(
                RiskAlert(
                    level="high",
                    category="trend",
                    message=(
                        f"Overall spending is increasing at "
                        f"{overall_trend.avg_change_rate:.1%} per month"
                    ),
                    value=overall_trend.avg_change_rate,
                    threshold=0.15,
                )
            )
        else:
            alerts.append(
                RiskAlert(
                    level="low",
                    category="trend",
                    message=(
                        f"Spending shows an upward trend "
                        f"({overall_trend.avg_change_rate:.1%} per month)"
                    ),
                    value=overall_trend.avg_change_rate,
                    threshold=0.05,
                )
            )

    # Check 5: Anomalous category trends
    if category_trends:
        for ct in category_trends:
            if ct.is_anomalous:
                alerts.append(
                    RiskAlert(
                        level="medium",
                        category=ct.label,
                        message=f"Anomalous spending detected: {ct.anomaly_reason}",
                    )
                )

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a.level, 3))

    return alerts
