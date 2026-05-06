"""
Prompt templates for the AI Advisor layer.

These templates are carefully engineered to produce:
  - Specific, actionable suggestions
  - Quantified impact estimates
  - Professional yet approachable tone

The templates receive STRUCTURED analysis data (never raw transactions)
as a deliberate privacy-preserving design.
"""

SYSTEM_PROMPT = """You are a professional financial advisor AI. Your role is to analyze structured spending data and provide actionable, specific advice.

Rules:
1. Every suggestion MUST include a concrete action and a quantified expected impact
2. Do NOT give vague advice like "spend less" — specify WHAT to reduce and by HOW MUCH
3. Be encouraging but honest about problems
4. Prioritize suggestions by potential impact
5. Use the user's currency ({currency_symbol}) for all amounts
6. Keep language clear and direct

Respond in JSON format ONLY with this structure:
{{
  "summary": "2-3 sentence overview of financial health",
  "suggestions": [
    {{
      "action": "Specific action to take",
      "expected_impact": "Quantified result (e.g., save ¥300/month)",
      "priority": "high|medium|low",
      "category": "which spending category this relates to"
    }}
  ],
  "encouragement": "One sentence of genuine encouragement based on the data"
}}"""


ANALYSIS_PROMPT = """Based on the following financial analysis data, provide professional spending advice.

## Financial Summary
- Period: {start_date} to {end_date}
- Total transactions: {total_transactions}
- Total expenses: {currency_symbol}{total_expense:,.2f}
- Total income: {currency_symbol}{total_income:,.2f}
- Savings rate: {savings_rate:.1%}
- Health score: {health_score}/100 (Grade: {health_grade})
- Volatility index: {volatility_index:.2f}

## Category Breakdown
{category_breakdown_text}

## Trend
- Overall direction: {trend_direction}
- Average monthly change: {avg_change_rate:.1%}

## Risk Alerts
{risk_alerts_text}

Provide 3-5 specific, actionable suggestions based on this data."""


def build_analysis_prompt(report_context: dict, currency_symbol: str = "¥") -> str:
    """Build the analysis prompt from structured report data.

    Args:
        report_context: Output of AnalysisReport.to_llm_context()
        currency_symbol: Currency symbol for display.

    Returns:
        Formatted prompt string.
    """
    # Format category breakdown
    cat_lines = []
    for cat in report_context.get("category_breakdown", []):
        cat_lines.append(
            f"  - {cat['category']}: {currency_symbol}{cat['total']:,.2f} "
            f"({cat['percentage']:.1%}, {cat['count']} transactions)"
        )
    cat_text = "\n".join(cat_lines) if cat_lines else "  No category data available"

    # Format risk alerts
    risk_lines = []
    for risk in report_context.get("risk_alerts", []):
        risk_lines.append(f"  - [{risk['level'].upper()}] {risk['message']}")
    risk_text = "\n".join(risk_lines) if risk_lines else "  No risk alerts"

    # Build prompt
    totals = report_context.get("totals", {})
    health = report_context.get("health", {})
    trends = report_context.get("trends", {})
    period = report_context.get("period", {})

    return ANALYSIS_PROMPT.format(
        start_date=period.get("start", "N/A"),
        end_date=period.get("end", "N/A"),
        total_transactions=period.get("total_transactions", 0),
        currency_symbol=currency_symbol,
        total_expense=totals.get("expense", 0),
        total_income=totals.get("income", 0),
        savings_rate=totals.get("savings_rate", 0),
        health_score=health.get("score", "N/A"),
        health_grade=health.get("grade", "N/A"),
        volatility_index=report_context.get("volatility_index", 0),
        category_breakdown_text=cat_text,
        trend_direction=trends.get("direction", "unknown"),
        avg_change_rate=trends.get("avg_change_rate", 0),
        risk_alerts_text=risk_text,
    )


def build_system_prompt(currency_symbol: str = "¥") -> str:
    """Build the system prompt with currency configuration."""
    return SYSTEM_PROMPT.format(currency_symbol=currency_symbol)
