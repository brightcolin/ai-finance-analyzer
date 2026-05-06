#!/usr/bin/env python3
"""
Quick Start Example — AI Finance Analyzer

Demonstrates the full pipeline from a WeChat Pay CSV to
actionable financial insights in just a few lines.

Usage:
    python examples/quickstart.py

Set DEEPSEEK_API_KEY environment variable for real AI advice.
Without it, the system uses smart mock advice based on your data.
"""

import sys
from pathlib import Path

# Add project root to path for development
project_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(project_root))

from analyzer import run_pipeline


def main():
    # Path to sample WeChat Pay CSV
    sample_file = Path(__file__).parent / "sample_wechat.csv"

    print("=" * 60)
    print("  AI Finance Analyzer — Quick Start Demo")
    print("=" * 60)
    print()

    # Run the full pipeline
    report = run_pipeline(
        filepath=sample_file,
        use_llm_classify=True,   # Use rules only (no API needed)
        use_llm_advice=True,     # Use mock advice (no API needed)
    )

    # --- Analysis Results ---
    analysis = report.analysis
    print("📊 ANALYSIS RESULTS")
    print("-" * 40)
    print(f"  Period:       {analysis.start_date} to {analysis.end_date}")
    print(f"  Transactions: {analysis.total_transactions}")
    print(f"  Total Expense: ¥{analysis.total_expense:,.2f}")
    print(f"  Total Income:  ¥{analysis.total_income:,.2f}")
    print(f"  Savings Rate:  {analysis.savings_rate:.1%}")
    print()

    # --- Health Score ---
    if analysis.health_score:
        hs = analysis.health_score
        print(f"🏥 HEALTH SCORE: {hs.total_score:.0f}/100 (Grade {hs.grade})")
        print("-" * 40)
        for component, score in hs.components.items():
            bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
            print(f"  {component:20s} {bar} {score:.0f}")
        print()

    # --- Category Breakdown ---
    print("📂 CATEGORY BREAKDOWN")
    print("-" * 40)
    for cb in analysis.category_breakdown[:8]:
        bar = "█" * int(cb.percentage * 40)
        print(f"  {cb.category.value:15s} ¥{cb.total:>8,.0f}  {cb.percentage:5.1%}  {bar}")
    print()

    # --- Risk Alerts ---
    if analysis.risk_alerts:
        print("⚠️  RISK ALERTS")
        print("-" * 40)
        icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for alert in analysis.risk_alerts:
            icon = icons.get(alert.level, "⚪")
            print(f"  {icon} [{alert.level.upper()}] {alert.message}")
        print()

    # --- AI Advice ---
    if report.advice:
        advice = report.advice
        print("💡 AI ADVICE")
        print("-" * 40)
        print(f"  {advice.summary}")
        print()
        for i, s in enumerate(advice.suggestions, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                s.priority, "⚪"
            )
            print(f"  {i}. {priority_icon} {s.action}")
            print(f"     → {s.expected_impact}")
            print()

        if advice.encouragement:
            print(f"  💪 {advice.encouragement}")

    print()
    print("=" * 60)
    print("  Set DEEPSEEK_API_KEY for real AI-powered advice!")
    print("=" * 60)


if __name__ == "__main__":
    main()
