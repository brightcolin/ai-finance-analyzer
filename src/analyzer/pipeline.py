"""
Main pipeline — end-to-end execution from raw file to full report.

This is the primary entry point for using AI Finance Analyzer.
Orchestrates all four layers: Parser → Classifier → Analyzer → Advisor.

Usage:
    from analyzer import run_pipeline
    report = run_pipeline("wechat_bill.csv")
    print(report.analysis.health_score.total_score)
    print(report.advice.summary)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from analyzer.advisor import generate_advice
from analyzer.classifier import classify
from analyzer.engine import analyze
from analyzer.models.schemas import (
    AnalysisReport,
    FinancialAdvice,
    FullReport,
    Transaction,
)
from analyzer.parser import parse_file

logger = logging.getLogger(__name__)


def run_pipeline(
    filepath: str | Path,
    use_llm_classify: bool = True,
    use_llm_advice: bool = True,
    rules_path: Optional[str | Path] = None,
) -> FullReport:
    """Execute the complete analysis pipeline.

    Args:
        filepath: Path to the bill file (CSV, etc.)
        use_llm_classify: Use LLM for low-confidence classifications.
        use_llm_advice: Use LLM for generating advice (vs mock).
        rules_path: Optional custom rules file for classifier.

    Returns:
        FullReport containing analysis and advice.
    """
    logger.info(f"Starting pipeline for: {filepath}")

    # Step 1: Parse
    logger.info("Step 1/4: Parsing bill file...")
    transactions = parse_file(filepath)
    logger.info(f"  Parsed {len(transactions)} transactions")

    if not transactions:
        logger.warning("No transactions found in file")
        return FullReport(analysis=AnalysisReport())

    # Step 2: Classify
    logger.info("Step 2/4: Classifying transactions...")
    categorized = classify(
        transactions,
        rules_path=rules_path,
        use_llm_fallback=use_llm_classify,
    )
    logger.info(f"  Classified {len(categorized)} transactions")

    # Step 3: Analyze
    logger.info("Step 3/4: Running analysis engine...")
    report = analyze(categorized)
    logger.info(
        f"  Health score: {report.health_score.total_score:.0f}/100"
        if report.health_score else "  No health score computed"
    )

    # Step 4: Generate advice
    logger.info("Step 4/4: Generating advice...")
    advice = generate_advice(report, use_mock=not use_llm_advice)
    logger.info(f"  Generated {len(advice.suggestions)} suggestions")

    result = FullReport(analysis=report, advice=advice)
    logger.info("Pipeline complete")

    return result


def analyze_transactions(
    transactions: list[Transaction],
    use_llm_classify: bool = False,
    rules_path: Optional[str | Path] = None,
) -> AnalysisReport:
    """Analyze pre-parsed transactions (skip the parser step).

    Useful when you already have Transaction objects from a custom source.

    Args:
        transactions: Pre-parsed Transaction objects.
        use_llm_classify: Use LLM for classification.
        rules_path: Optional custom rules file.

    Returns:
        AnalysisReport with all metrics.
    """
    categorized = classify(
        transactions,
        rules_path=rules_path,
        use_llm_fallback=use_llm_classify,
    )
    return analyze(categorized)


def get_advice(
    report: AnalysisReport,
    use_mock: bool = False,
) -> FinancialAdvice:
    """Generate advice from an existing analysis report.

    Args:
        report: Pre-computed AnalysisReport.
        use_mock: Force mock mode.

    Returns:
        FinancialAdvice with suggestions.
    """
    return generate_advice(report, use_mock=use_mock)
