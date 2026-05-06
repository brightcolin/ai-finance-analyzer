"""
Rule-based classification engine.

Uses keyword matching against a configurable rules file.
This is the first layer of the "rules first, AI fallback" strategy.
Handles ~80% of transactions with zero API cost and 100% determinism.
"""

from __future__ import annotations

import json
from pathlib import Path

from analyzer.models.schemas import (
    Category,
    CategorizedTransaction,
    ClassificationMethod,
    Transaction,
    TransactionType,
)

# Default rules file path
DEFAULT_RULES_PATH = Path(__file__).parent / "rules.json"


class RulesEngine:
    """Keyword-based transaction classifier.

    Loads rules from a JSON config and matches transaction text
    against keyword lists. Supports sub-category detection.
    """

    def __init__(self, rules_path: str | Path | None = None):
        """Initialize with rules from a JSON file.

        Args:
            rules_path: Path to rules JSON. Uses built-in rules if None.
        """
        path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self._rules = self._load_rules(path)
        self._keyword_index = self._build_index()

    def _load_rules(self, path: Path) -> dict:
        """Load and validate rules JSON."""
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Remove comments
        data.pop("_comment", None)
        return data

    def _build_index(self) -> list[tuple[str, str, str]]:
        """Build a flat (keyword, category, sub_category) index for fast lookup.

        Returns a list sorted by keyword length (longest first) to ensure
        more specific matches take priority.
        """
        index = []
        for category, config in self._rules.items():
            keywords = config.get("keywords", [])
            sub_cats = config.get("sub_categories", {})

            # Build reverse sub-category lookup
            kw_to_sub = {}
            for sub_name, sub_keywords in sub_cats.items():
                for skw in sub_keywords:
                    kw_to_sub[skw.lower()] = sub_name

            for kw in keywords:
                sub = kw_to_sub.get(kw.lower(), "")
                index.append((kw.lower(), category, sub))

        # Sort by keyword length descending for greedy matching
        index.sort(key=lambda x: len(x[0]), reverse=True)
        return index

    def classify(self, transaction: Transaction) -> CategorizedTransaction:
        """Classify a single transaction using keyword rules.

        Args:
            transaction: The transaction to classify.

        Returns:
            CategorizedTransaction with category and confidence.
        """
        # Handle income and transfers by transaction type
        if transaction.tx_type == TransactionType.INCOME:
            return CategorizedTransaction(
                transaction=transaction,
                category=Category.INCOME,
                confidence=1.0,
                method=ClassificationMethod.RULE,
            )

        # Build search text from all available fields
        search_text = " ".join([
            transaction.description,
            transaction.counterparty,
            transaction.raw_text,
        ]).lower()

        # Try keyword matching
        for keyword, category_str, sub_cat in self._keyword_index:
            if keyword in search_text:
                try:
                    category = Category(category_str)
                except ValueError:
                    continue

                return CategorizedTransaction(
                    transaction=transaction,
                    category=category,
                    sub_category=sub_cat,
                    confidence=0.9,
                    method=ClassificationMethod.RULE,
                )

        # No match found — return with low confidence
        return CategorizedTransaction(
            transaction=transaction,
            category=Category.OTHER,
            sub_category="",
            confidence=0.1,
            method=ClassificationMethod.DEFAULT,
        )

    def classify_batch(
        self, transactions: list[Transaction]
    ) -> list[CategorizedTransaction]:
        """Classify a batch of transactions.

        Args:
            transactions: List of transactions to classify.

        Returns:
            List of classified transactions in the same order.
        """
        return [self.classify(tx) for tx in transactions]

    def get_categories(self) -> list[str]:
        """List all categories defined in the rules."""
        return list(self._rules.keys())

    def get_keywords(self, category: str) -> list[str]:
        """Get all keywords for a specific category."""
        config = self._rules.get(category, {})
        return config.get("keywords", [])
