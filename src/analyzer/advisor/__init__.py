"""
Advisor layer — AI-powered financial advice generation.

Uses DeepSeek API (OpenAI-compatible) to generate actionable
financial suggestions from structured analysis data.

Includes a mock advisor for testing without API access.

Usage:
    from analyzer.advisor import generate_advice
    advice = generate_advice(analysis_report)
"""

from __future__ import annotations

import json
import logging

from analyzer.advisor.prompts import build_analysis_prompt, build_system_prompt
from analyzer.core.config import get_config
from analyzer.models.schemas import (
    AnalysisReport,
    FinancialAdvice,
    Suggestion,
)

logger = logging.getLogger(__name__)

_CURRENCY_SYMBOLS: dict[str, str] = {
    "CNY": "¥",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
}


def _currency_symbol(currency: str) -> str:
    return _CURRENCY_SYMBOLS.get(currency, currency)


def generate_advice(
    report: AnalysisReport,
    use_mock: bool = False,
) -> FinancialAdvice:
    """Generate financial advice from an analysis report.

    Automatically falls back to mock if no API key is configured.

    Args:
        report: Complete analysis report from the engine.
        use_mock: Force mock mode (for testing).

    Returns:
        FinancialAdvice with actionable suggestions.
    """
    config = get_config()

    if use_mock or not config.llm.api_key:
        if not use_mock:
            logger.info("No API key configured, using mock advisor")
        return _mock_advice(report)

    return _llm_advice(report, config)


def _llm_advice(report: AnalysisReport, config) -> FinancialAdvice:
    """Generate advice using DeepSeek API."""
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
        )

        context = report.to_llm_context()
        symbol = _currency_symbol(report.currency)
        system_prompt = build_system_prompt(symbol)
        user_prompt = build_analysis_prompt(context, symbol)

        response = client.chat.completions.create(
            model=config.llm.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        raw_content = response.choices[0].message.content.strip()
        return _parse_llm_response(raw_content)

    except ImportError:
        logger.error(
            "openai package not installed. Install with: pip install openai"
        )
        return _mock_advice(report)

    except Exception as e:
        logger.error(f"LLM advice generation failed: {e}")
        return _mock_advice(report)


def _parse_llm_response(content: str) -> FinancialAdvice:
    """Parse LLM JSON response into FinancialAdvice."""
    try:
        # Strip markdown fences if present
        clean = content.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
            clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()

        data = json.loads(clean)

        suggestions = []
        for s in data.get("suggestions", []):
            suggestions.append(
                Suggestion(
                    action=s.get("action", ""),
                    expected_impact=s.get("expected_impact", ""),
                    priority=s.get("priority", "medium"),
                    category=s.get("category", ""),
                )
            )

        return FinancialAdvice(
            summary=data.get("summary", ""),
            suggestions=suggestions,
            encouragement=data.get("encouragement", ""),
            raw_llm_response=content,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        # Return the raw text as summary
        return FinancialAdvice(
            summary=content[:500],
            raw_llm_response=content,
        )


def _mock_advice(report: AnalysisReport) -> FinancialAdvice:
    """Generate deterministic mock advice based on analysis data.

    Useful for testing and demo purposes without API access.
    """
    suggestions = []
    symbol = _currency_symbol(report.currency)

    # Generate suggestions based on actual analysis data
    for breakdown in report.category_breakdown[:3]:
        if breakdown.percentage > 0.30:
            monthly = breakdown.total
            reduction = monthly * 0.20
            suggestions.append(
                Suggestion(
                    action=(
                        f"Reduce {breakdown.category.value} spending by 20% — "
                        f"consider cutting back on: {', '.join(breakdown.top_items[:3])}"
                    ),
                    expected_impact=f"Save approximately {symbol}{reduction:,.0f}/month",
                    priority="high",
                    category=breakdown.category.value,
                )
            )
        elif breakdown.percentage > 0.20:
            suggestions.append(
                Suggestion(
                    action=(
                        f"Monitor {breakdown.category.value} spending — "
                        f"it accounts for {breakdown.percentage:.0%} of your budget"
                    ),
                    expected_impact="Maintain awareness to prevent creep",
                    priority="medium",
                    category=breakdown.category.value,
                )
            )

    if report.savings_rate < 0.10:
        gap = (0.20 - report.savings_rate) * report.total_income if report.total_income else 0
        suggestions.append(
            Suggestion(
                action="Set a savings target of 20% of income",
                expected_impact=f"Need to free up {symbol}{gap:,.0f}/month",
                priority="high",
                category="savings",
            )
        )

    if report.volatility_index > 0.4:
        suggestions.append(
            Suggestion(
                action=(
                    "Create a monthly budget to stabilize spending — "
                    "your volatility index indicates irregular patterns"
                ),
                expected_impact="More predictable cash flow and better planning",
                priority="medium",
                category="stability",
            )
        )

    # Ensure at least one suggestion
    if not suggestions:
        suggestions.append(
            Suggestion(
                action="Continue your current spending habits — they look healthy",
                expected_impact="Maintain financial stability",
                priority="low",
                category="general",
            )
        )

    # Build summary
    score = report.health_score.total_score if report.health_score else 0
    grade = report.health_score.grade if report.health_score else "N/A"
    summary = (
        f"Your financial health score is {score:.0f}/100 (Grade {grade}). "
        f"Your savings rate is {report.savings_rate:.1%} and total monthly "
        f"expenses are {symbol}{report.total_expense:,.0f}."
    )

    encouragement = (
        "You're tracking your finances — that's already a great step. "
        "Small, consistent changes lead to big results over time."
    )

    return FinancialAdvice(
        summary=summary,
        suggestions=suggestions,
        encouragement=encouragement,
        raw_llm_response="[mock]",
    )


__all__ = ["generate_advice"]
