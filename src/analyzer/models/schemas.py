"""
Core data models for AI Finance Analyzer.

All modules communicate through these standardized schemas.
Uses dataclasses for simplicity and broad compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class Category(str, Enum):
    """Primary spending categories with standardized labels."""

    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTH = "health"
    EDUCATION = "education"
    UTILITIES = "utilities"
    TRANSFER = "transfer"
    INCOME = "income"
    OTHER = "other"

    @classmethod
    def expense_categories(cls) -> list[Category]:
        """Return only expense-related categories (exclude income/transfer)."""
        return [c for c in cls if c not in (cls.INCOME, cls.TRANSFER)]


class ClassificationMethod(str, Enum):
    """How a transaction was classified."""

    RULE = "rule"
    LLM = "llm"
    MANUAL = "manual"
    DEFAULT = "default"


class TransactionType(str, Enum):
    """Direction of money flow."""

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


@dataclass
class Transaction:
    """A single financial transaction parsed from raw data.

    This is the output of the Parser layer — a cleaned,
    standardized record ready for classification.
    """

    amount: float
    description: str
    date: date
    raw_text: str = ""
    counterparty: str = ""
    tx_type: TransactionType = TransactionType.EXPENSE
    payment_method: str = ""
    currency: str = "CNY"

    def __post_init__(self):
        if isinstance(self.date, str):
            self.date = datetime.strptime(self.date, "%Y-%m-%d").date()
        if isinstance(self.tx_type, str):
            self.tx_type = TransactionType(self.tx_type)


@dataclass
class CategorizedTransaction:
    """A transaction with classification results attached.

    Output of the Classifier layer.
    """

    transaction: Transaction
    category: Category
    sub_category: str = ""
    confidence: float = 1.0
    method: ClassificationMethod = ClassificationMethod.DEFAULT

    @property
    def amount(self) -> float:
        return self.transaction.amount

    @property
    def date(self) -> date:
        return self.transaction.date

    @property
    def description(self) -> str:
        return self.transaction.description


@dataclass
class CategoryBreakdown:
    """Spending breakdown for a single category."""

    category: Category
    total: float
    count: int
    percentage: float
    avg_per_transaction: float
    top_items: list[str] = field(default_factory=list)


@dataclass
class TrendPoint:
    """A single data point in a time series trend."""

    period: str  # e.g. "2026-01", "2026-W14"
    amount: float
    change_rate: Optional[float] = None  # vs previous period


@dataclass
class TrendAnalysis:
    """Trend analysis results for a category or total spending."""

    label: str
    data_points: list[TrendPoint] = field(default_factory=list)
    direction: str = "stable"  # "increasing", "decreasing", "stable"
    avg_change_rate: float = 0.0
    is_anomalous: bool = False
    anomaly_reason: str = ""


@dataclass
class RiskAlert:
    """A specific risk or warning detected in spending behavior."""

    level: str  # "high", "medium", "low"
    category: str
    message: str
    value: float = 0.0
    threshold: float = 0.0


@dataclass
class HealthScore:
    """Financial health score with component breakdown."""

    total_score: float  # 0-100
    components: dict[str, float] = field(default_factory=dict)
    grade: str = ""  # A/B/C/D/F

    def __post_init__(self):
        if not self.grade:
            if self.total_score >= 90:
                self.grade = "A"
            elif self.total_score >= 75:
                self.grade = "B"
            elif self.total_score >= 60:
                self.grade = "C"
            elif self.total_score >= 40:
                self.grade = "D"
            else:
                self.grade = "F"


@dataclass
class AnalysisReport:
    """Complete analysis output from the Analyzer layer.

    This structured data is fed to the Advisor layer for
    generating actionable recommendations.
    """

    # Time range
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_transactions: int = 0

    # Structure analysis
    total_expense: float = 0.0
    total_income: float = 0.0
    category_breakdown: list[CategoryBreakdown] = field(default_factory=list)

    # Trend analysis
    monthly_trends: list[TrendAnalysis] = field(default_factory=list)
    overall_trend: Optional[TrendAnalysis] = None

    # Health metrics
    health_score: Optional[HealthScore] = None
    disposable_income: float = 0.0
    savings_rate: float = 0.0
    volatility_index: float = 0.0

    # Risk alerts
    risk_alerts: list[RiskAlert] = field(default_factory=list)

    def to_llm_context(self) -> dict:
        """Convert to a clean dict suitable for LLM prompt injection.

        Only sends aggregated metrics — never raw transaction details.
        This is a deliberate privacy-preserving design.
        """
        return {
            "period": {
                "start": str(self.start_date) if self.start_date else None,
                "end": str(self.end_date) if self.end_date else None,
                "total_transactions": self.total_transactions,
            },
            "totals": {
                "expense": round(self.total_expense, 2),
                "income": round(self.total_income, 2),
                "disposable_income": round(self.disposable_income, 2),
                "savings_rate": round(self.savings_rate, 4),
            },
            "category_breakdown": [
                {
                    "category": cb.category.value,
                    "total": round(cb.total, 2),
                    "percentage": round(cb.percentage, 4),
                    "count": cb.count,
                }
                for cb in self.category_breakdown
            ],
            "health": {
                "score": round(self.health_score.total_score, 1) if self.health_score else None,
                "grade": self.health_score.grade if self.health_score else None,
                "components": self.health_score.components if self.health_score else {},
            },
            "volatility_index": round(self.volatility_index, 4),
            "trends": {
                "direction": self.overall_trend.direction if self.overall_trend else "unknown",
                "avg_change_rate": round(
                    self.overall_trend.avg_change_rate, 4
                ) if self.overall_trend else 0,
            },
            "risk_alerts": [
                {"level": r.level, "category": r.category, "message": r.message}
                for r in self.risk_alerts
            ],
        }


@dataclass
class Suggestion:
    """A single actionable suggestion from the Advisor."""

    action: str
    expected_impact: str
    priority: str = "medium"  # "high", "medium", "low"
    category: str = ""


@dataclass
class FinancialAdvice:
    """Complete advice output from the Advisor layer."""

    summary: str
    suggestions: list[Suggestion] = field(default_factory=list)
    encouragement: str = ""
    raw_llm_response: str = ""


@dataclass
class FullReport:
    """The final deliverable combining analysis and advice."""

    analysis: AnalysisReport
    advice: Optional[FinancialAdvice] = None
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
