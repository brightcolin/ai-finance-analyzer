"""
Classifier layer — maps transactions to semantic categories.

Uses a two-tier strategy:
  1. Rule engine (fast, deterministic, handles ~80% of transactions)
  2. LLM fallback (for unrecognized or low-confidence items)

Usage:
    from analyzer.classifier import classify
    categorized = classify(transactions)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from analyzer.classifier.llm_classifier import LLMClassifier
from analyzer.classifier.rules_engine import RulesEngine
from analyzer.models.schemas import (
    CategorizedTransaction,
    Transaction,
)

logger = logging.getLogger(__name__)

# Confidence threshold: below this, escalate to LLM
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


def classify(
    transactions: list[Transaction],
    rules_path: Optional[str | Path] = None,
    use_llm_fallback: bool = True,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[CategorizedTransaction]:
    """Classify a list of transactions using the two-tier strategy.

    Args:
        transactions: List of parsed transactions.
        rules_path: Optional custom rules JSON file path.
        use_llm_fallback: Whether to use LLM for low-confidence items.
        confidence_threshold: Minimum confidence to accept rule-based result.

    Returns:
        List of CategorizedTransaction objects.
    """
    # Initialize rule engine
    rules = RulesEngine(rules_path)

    # First pass: rule-based classification
    results = rules.classify_batch(transactions)

    # Identify low-confidence items for LLM escalation
    if use_llm_fallback:
        low_conf_indices = [
            i for i, r in enumerate(results)
            if r.confidence < confidence_threshold
        ]

        if low_conf_indices:
            logger.info(
                f"Escalating {len(low_conf_indices)}/{len(results)} "
                f"transactions to LLM classifier"
            )
            try:
                llm = LLMClassifier()
                low_conf_txs = [transactions[i] for i in low_conf_indices]
                llm_results = llm.classify_batch(low_conf_txs)

                for idx, llm_result in zip(low_conf_indices, llm_results):
                    # Only use LLM result if it's more confident
                    if llm_result.confidence > results[idx].confidence:
                        results[idx] = llm_result

            except Exception as e:
                logger.warning(f"LLM fallback failed, keeping rule results: {e}")

    return results


def classify_one(
    transaction: Transaction,
    rules_path: Optional[str | Path] = None,
    use_llm_fallback: bool = True,
) -> CategorizedTransaction:
    """Classify a single transaction. Convenience wrapper."""
    results = classify(
        [transaction],
        rules_path=rules_path,
        use_llm_fallback=use_llm_fallback,
    )
    return results[0]


__all__ = [
    "classify",
    "classify_one",
    "RulesEngine",
    "LLMClassifier",
]
