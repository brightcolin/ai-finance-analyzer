"""
Structure analysis — spending composition and category breakdown.

Pure algorithmic computation, no AI involved.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from analyzer.models.schemas import (
    Category,
    CategorizedTransaction,
    CategoryBreakdown,
    TransactionType,
)


def analyze_structure(
    transactions: list[CategorizedTransaction],
) -> list[CategoryBreakdown]:
    """Compute spending breakdown by category.

    Args:
        transactions: Classified transactions.

    Returns:
        List of CategoryBreakdown sorted by total (descending).
    """
    # Filter to expenses only
    expenses = [
        tx for tx in transactions
        if tx.transaction.tx_type == TransactionType.EXPENSE
    ]

    if not expenses:
        return []

    # Aggregate by category
    cat_totals: dict[Category, float] = defaultdict(float)
    cat_counts: dict[Category, int] = defaultdict(int)
    cat_items: dict[Category, list[str]] = defaultdict(list)

    for tx in expenses:
        cat_totals[tx.category] += tx.amount
        cat_counts[tx.category] += 1
        cat_items[tx.category].append(tx.description)

    total_expense = sum(cat_totals.values())

    # Build breakdowns
    breakdowns = []
    for cat in sorted(cat_totals, key=lambda c: cat_totals[c], reverse=True):
        total = cat_totals[cat]
        count = cat_counts[cat]

        # Find top items by frequency
        item_freq = Counter(cat_items[cat])
        top_items = [item for item, _ in item_freq.most_common(5)]

        breakdowns.append(
            CategoryBreakdown(
                category=cat,
                total=round(total, 2),
                count=count,
                percentage=round(total / total_expense, 4) if total_expense > 0 else 0,
                avg_per_transaction=round(total / count, 2) if count > 0 else 0,
                top_items=top_items,
            )
        )

    return breakdowns


def compute_totals(
    transactions: list[CategorizedTransaction],
) -> tuple[float, float]:
    """Compute total expense and total income.

    Returns:
        (total_expense, total_income)
    """
    total_expense = sum(
        tx.amount for tx in transactions
        if tx.transaction.tx_type == TransactionType.EXPENSE
    )
    total_income = sum(
        tx.amount for tx in transactions
        if tx.transaction.tx_type == TransactionType.INCOME
    )
    return round(total_expense, 2), round(total_income, 2)


def compute_savings_rate(total_income: float, total_expense: float) -> float:
    """Compute savings rate: (income - expense) / income."""
    if total_income <= 0:
        return 0.0
    return round((total_income - total_expense) / total_income, 4)


def compute_essential_ratio(
    breakdowns: list[CategoryBreakdown],
    essential_categories: list[str] | None = None,
) -> float:
    """Compute the ratio of essential spending to total spending.

    Essential categories default to food, housing, transport,
    utilities, and health.
    """
    if essential_categories is None:
        essential_categories = ["food", "housing", "transport", "utilities", "health"]

    total = sum(b.total for b in breakdowns)
    if total <= 0:
        return 0.0

    essential_total = sum(
        b.total for b in breakdowns
        if b.category.value in essential_categories
    )
    return round(essential_total / total, 4)
