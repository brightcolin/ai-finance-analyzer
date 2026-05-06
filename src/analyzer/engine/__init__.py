"""
Analysis engine — computes structured insights from classified data.

Orchestrates structure analysis, trend detection, health scoring,
and risk assessment into a single AnalysisReport.

Usage:
    from analyzer.engine import analyze
    report = analyze(categorized_transactions)
"""

from __future__ import annotations

from analyzer.engine.health import compute_health_score
from analyzer.engine.risks import detect_risks
from analyzer.engine.structure import (
    analyze_structure,
    compute_savings_rate,
    compute_totals,
)
from analyzer.engine.trends import (
    analyze_monthly_trends,
    compute_volatility_index,
)
from analyzer.models.schemas import (
    AnalysisReport,
    CategorizedTransaction,
)


def analyze(transactions: list[CategorizedTransaction]) -> AnalysisReport:
    """Run the complete analysis pipeline on classified transactions.

    This is the main entry point for the analysis engine.
    All computation is deterministic — no AI involved.

    Args:
        transactions: List of classified transactions.

    Returns:
        Complete AnalysisReport with all metrics computed.
    """
    if not transactions:
        return AnalysisReport()

    # Date range
    dates = [tx.date for tx in transactions]
    start_date = min(dates)
    end_date = max(dates)

    # Structure analysis
    total_expense, total_income = compute_totals(transactions)
    breakdowns = analyze_structure(transactions)
    savings_rate = compute_savings_rate(total_income, total_expense)

    # Trend analysis
    overall_trend, category_trends = analyze_monthly_trends(transactions)
    volatility = compute_volatility_index(transactions)

    # Health score
    health = compute_health_score(
        transactions=transactions,
        breakdowns=breakdowns,
        savings_rate=savings_rate,
        volatility_index=volatility,
        trend_direction=overall_trend.direction if overall_trend else "stable",
    )

    # Risk detection
    risks = detect_risks(
        breakdowns=breakdowns,
        savings_rate=savings_rate,
        volatility_index=volatility,
        overall_trend=overall_trend,
        category_trends=category_trends,
    )

    # Disposable income estimation
    disposable = total_income - total_expense

    return AnalysisReport(
        start_date=start_date,
        end_date=end_date,
        total_transactions=len(transactions),
        total_expense=total_expense,
        total_income=total_income,
        category_breakdown=breakdowns,
        monthly_trends=category_trends,
        overall_trend=overall_trend,
        health_score=health,
        disposable_income=round(disposable, 2),
        savings_rate=savings_rate,
        volatility_index=volatility,
        risk_alerts=risks,
    )


__all__ = ["analyze"]
