"""
AI Finance Analyzer — Turn raw expense data into actionable financial insights.

A developer-first AI financial decision engine.

Quick Start:
    from analyzer import run_pipeline
    report = run_pipeline("wechat_bill.csv")
    print(f"Health Score: {report.analysis.health_score.total_score}/100")
    for suggestion in report.advice.suggestions:
        print(f"  [{suggestion.priority}] {suggestion.action}")
"""

__version__ = "0.1.0"

from analyzer.pipeline import (
    analyze_transactions,
    get_advice,
    run_pipeline,
)

__all__ = [
    "run_pipeline",
    "analyze_transactions",
    "get_advice",
    "__version__",
]
