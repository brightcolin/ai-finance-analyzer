"""
LLM-based classification — fallback for transactions
that the rule engine cannot confidently classify.

Only invoked when RulesEngine returns confidence < threshold.
Uses DeepSeek API (or compatible OpenAI-format API) for semantic
understanding of transaction descriptions.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from analyzer.core.config import get_config
from analyzer.models.schemas import (
    Category,
    CategorizedTransaction,
    ClassificationMethod,
    Transaction,
)

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a financial transaction classifier. Given a transaction description, classify it into exactly ONE of these categories:

Categories: food, transport, housing, entertainment, shopping, health, education, utilities, transfer, other

Transaction: "{description}"
Counterparty: "{counterparty}"

Respond with ONLY a JSON object, no other text:
{{"category": "<category>", "sub_category": "<optional_sub>", "confidence": <0.0-1.0>}}"""


class LLMClassifier:
    """LLM-powered transaction classifier.

    Uses the DeepSeek API (OpenAI-compatible format) for semantic
    classification of transactions that rules cannot handle.
    """

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        """Initialize with API credentials.

        Falls back to global config if not provided.
        """
        config = get_config()
        self._api_key = api_key or config.llm.api_key
        self._base_url = base_url or config.llm.base_url
        self._model = model or config.llm.model
        self._client = None

    def _get_client(self):
        """Lazy-initialize the HTTP client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
            except ImportError:
                raise ImportError(
                    "openai package is required for LLM classification. "
                    "Install with: pip install openai"
                )
        return self._client

    def classify(self, transaction: Transaction) -> CategorizedTransaction:
        """Classify a transaction using the LLM.

        Args:
            transaction: Transaction to classify.

        Returns:
            CategorizedTransaction with LLM-assigned category.
        """
        if not self._api_key:
            logger.warning("No API key configured; returning 'other' as default")
            return self._default_result(transaction)

        try:
            prompt = CLASSIFICATION_PROMPT.format(
                description=transaction.description,
                counterparty=transaction.counterparty,
            )

            client = self._get_client()
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
            )

            content = response.choices[0].message.content.strip()
            return self._parse_response(transaction, content)

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return self._default_result(transaction)

    def classify_batch(
        self,
        transactions: list[Transaction],
        batch_size: int = 10,
    ) -> list[CategorizedTransaction]:
        """Classify multiple transactions.

        Processes individually (batch API could be added later).
        """
        results = []
        for tx in transactions:
            results.append(self.classify(tx))
        return results

    def _parse_response(
        self, transaction: Transaction, content: str
    ) -> CategorizedTransaction:
        """Parse LLM JSON response into a CategorizedTransaction."""
        try:
            # Strip markdown code fences if present
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[-1]
                clean = clean.rsplit("```", 1)[0]
            clean = clean.strip()

            data = json.loads(clean)
            category_str = data.get("category", "other").lower()
            sub_category = data.get("sub_category", "")
            confidence = float(data.get("confidence", 0.7))

            try:
                category = Category(category_str)
            except ValueError:
                category = Category.OTHER
                confidence = 0.3

            return CategorizedTransaction(
                transaction=transaction,
                category=category,
                sub_category=sub_category or "",
                confidence=min(confidence, 0.95),  # Cap at 0.95 for LLM
                method=ClassificationMethod.LLM,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse LLM response: {content!r} — {e}")
            return self._default_result(transaction)

    def _default_result(self, transaction: Transaction) -> CategorizedTransaction:
        """Return a low-confidence default classification."""
        return CategorizedTransaction(
            transaction=transaction,
            category=Category.OTHER,
            sub_category="",
            confidence=0.1,
            method=ClassificationMethod.DEFAULT,
        )
