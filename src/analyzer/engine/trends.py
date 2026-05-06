"""
Trend analysis — time series spending patterns and anomaly detection.

Computes monthly/weekly trends, identifies growth direction,
and flags anomalous spending spikes.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date

from analyzer.models.schemas import (
    CategorizedTransaction,
    Category,
    TrendAnalysis,
    TrendPoint,
    TransactionType,
)


def analyze_monthly_trends(
    transactions: list[CategorizedTransaction],
) -> tuple[TrendAnalysis, list[TrendAnalysis]]:
    """Compute monthly spending trends for overall and per-category.

    Args:
        transactions: Classified transactions.

    Returns:
        (overall_trend, per_category_trends)
    """
    expenses = [
        tx for tx in transactions
        if tx.transaction.tx_type == TransactionType.EXPENSE
    ]

    if not expenses:
        return TrendAnalysis(label="overall"), []

    # Group by month
    monthly_totals: dict[str, float] = defaultdict(float)
    monthly_by_cat: dict[Category, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    for tx in expenses:
        month_key = tx.date.strftime("%Y-%m")
        monthly_totals[month_key] += tx.amount
        monthly_by_cat[tx.category][month_key] += tx.amount

    # Build overall trend
    overall = _build_trend("overall", monthly_totals)

    # Build per-category trends
    cat_trends = []
    for cat in sorted(monthly_by_cat.keys(), key=lambda c: c.value):
        trend = _build_trend(cat.value, monthly_by_cat[cat])
        cat_trends.append(trend)

    return overall, cat_trends


def _build_trend(label: str, period_totals: dict[str, float]) -> TrendAnalysis:
    """Build a TrendAnalysis from period totals."""
    sorted_periods = sorted(period_totals.keys())

    if len(sorted_periods) == 0:
        return TrendAnalysis(label=label)

    # Build data points with change rates
    data_points = []
    prev_amount = None

    for period in sorted_periods:
        amount = round(period_totals[period], 2)
        change_rate = None
        if prev_amount is not None and prev_amount > 0:
            change_rate = round((amount - prev_amount) / prev_amount, 4)
        data_points.append(
            TrendPoint(period=period, amount=amount, change_rate=change_rate)
        )
        prev_amount = amount

    # Compute direction and average change rate
    change_rates = [dp.change_rate for dp in data_points if dp.change_rate is not None]
    avg_change = statistics.mean(change_rates) if change_rates else 0.0

    if avg_change > 0.05:
        direction = "increasing"
    elif avg_change < -0.05:
        direction = "decreasing"
    else:
        direction = "stable"

    # Anomaly detection using standard deviation
    is_anomalous = False
    anomaly_reason = ""
    if len(data_points) >= 3:
        amounts = [dp.amount for dp in data_points]
        mean_amt = statistics.mean(amounts)
        std_amt = statistics.stdev(amounts) if len(amounts) > 1 else 0

        if std_amt > 0:
            latest = data_points[-1].amount
            z_score = (latest - mean_amt) / std_amt
            if abs(z_score) > 2.0:
                is_anomalous = True
                if z_score > 0:
                    anomaly_reason = (
                        f"Latest period ({data_points[-1].period}) spending is "
                        f"{z_score:.1f} standard deviations above the mean"
                    )
                else:
                    anomaly_reason = (
                        f"Latest period ({data_points[-1].period}) spending is "
                        f"{abs(z_score):.1f} standard deviations below the mean"
                    )

    return TrendAnalysis(
        label=label,
        data_points=data_points,
        direction=direction,
        avg_change_rate=round(avg_change, 4),
        is_anomalous=is_anomalous,
        anomaly_reason=anomaly_reason,
    )


def compute_volatility_index(
    transactions: list[CategorizedTransaction],
) -> float:
    """Compute the Spending Volatility Index.

    Measures how stable the user's spending is across time periods.
    Uses Coefficient of Variation (CV = std / mean) of monthly totals.

    Returns:
        A float between 0 and 1+. Lower = more stable.
        0.0-0.2: Very stable
        0.2-0.4: Normal
        0.4-0.6: Volatile
        0.6+: Highly volatile
    """
    expenses = [
        tx for tx in transactions
        if tx.transaction.tx_type == TransactionType.EXPENSE
    ]

    if not expenses:
        return 0.0

    # Aggregate by month
    monthly: dict[str, float] = defaultdict(float)
    for tx in expenses:
        month_key = tx.date.strftime("%Y-%m")
        monthly[month_key] += tx.amount

    amounts = list(monthly.values())

    if len(amounts) < 2:
        return 0.0

    mean_val = statistics.mean(amounts)
    if mean_val == 0:
        return 0.0

    std_val = statistics.stdev(amounts)
    cv = std_val / mean_val

    return round(cv, 4)
