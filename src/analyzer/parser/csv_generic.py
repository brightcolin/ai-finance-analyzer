"""
Generic CSV parser for custom or unknown bill formats.

Attempts to auto-detect columns by matching common header names.
Works as a fallback when no specific parser matches.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from pathlib import Path

from analyzer.models.schemas import Transaction, TransactionType
from analyzer.parser.base import BaseParser

# Common column name patterns for auto-detection
AMOUNT_PATTERNS = re.compile(
    r"(amount|金额|sum|total|price|value|cost|花费|消费金额)", re.IGNORECASE
)
DATE_PATTERNS = re.compile(
    r"(date|time|日期|时间|交易时间|transaction.?date|created)", re.IGNORECASE
)
DESC_PATTERNS = re.compile(
    r"(description|desc|商品|备注|摘要|说明|memo|note|item|detail|name)", re.IGNORECASE
)
CATEGORY_PATTERNS = re.compile(
    r"(category|type|分类|类别|类型)", re.IGNORECASE
)


class GenericCSVParser(BaseParser):
    """Fallback parser for generic CSV files.

    Uses heuristic column detection and is lenient about format.
    """

    @property
    def name(self) -> str:
        return "Generic CSV"

    @property
    def supported_formats(self) -> list[str]:
        return [".csv", ".tsv"]

    def can_handle(self, filepath: str | Path) -> bool:
        """Accept any CSV/TSV file as last resort."""
        return Path(filepath).suffix.lower() in self.supported_formats

    def parse(self, filepath: str | Path) -> list[Transaction]:
        """Parse a generic CSV into Transactions using column auto-detection."""
        content = self._read_file(filepath)

        # Detect delimiter
        delimiter = self._detect_delimiter(content)

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV file has no header row")

        # Auto-detect column roles
        col_map = self._detect_columns(reader.fieldnames)
        if "amount" not in col_map:
            raise ValueError(
                f"Cannot detect amount column. Headers found: {reader.fieldnames}"
            )

        transactions = []
        for row in reader:
            tx = self._parse_row(row, col_map)
            if tx is not None:
                transactions.append(tx)

        return transactions

    def _detect_delimiter(self, content: str) -> str:
        """Detect CSV delimiter from content."""
        first_line = content.split("\n")[0]
        if "\t" in first_line:
            return "\t"
        if ";" in first_line and "," not in first_line:
            return ";"
        return ","

    def _detect_columns(self, fieldnames: list[str]) -> dict[str, str]:
        """Auto-detect column roles by matching header name patterns."""
        col_map = {}

        for fname in fieldnames:
            clean = fname.strip()
            if AMOUNT_PATTERNS.search(clean) and "amount" not in col_map:
                col_map["amount"] = fname
            elif DATE_PATTERNS.search(clean) and "date" not in col_map:
                col_map["date"] = fname
            elif DESC_PATTERNS.search(clean) and "description" not in col_map:
                col_map["description"] = fname
            elif CATEGORY_PATTERNS.search(clean) and "category" not in col_map:
                col_map["category"] = fname

        return col_map

    def _parse_row(
        self, row: dict[str, str], col_map: dict[str, str]
    ) -> Transaction | None:
        """Parse a single row using detected column mapping."""
        # Amount (required)
        amount_str = row.get(col_map.get("amount", ""), "").strip()
        amount = self._parse_amount(amount_str)
        if amount is None or amount == 0:
            return None

        # Date
        date_str = row.get(col_map.get("date", ""), "").strip()
        tx_date = self._parse_date(date_str)

        # Description
        description = row.get(col_map.get("description", ""), "").strip()

        # Build raw text from all non-empty fields
        raw_parts = [v.strip() for v in row.values() if v and v.strip()]
        raw_text = " | ".join(raw_parts)

        # Determine type from amount sign
        tx_type = TransactionType.INCOME if amount < 0 else TransactionType.EXPENSE

        return Transaction(
            amount=abs(amount),
            description=description or "Unknown",
            date=tx_date or datetime.now().date(),
            raw_text=raw_text,
            tx_type=tx_type,
        )

    def _parse_amount(self, amount_str: str) -> float | None:
        """Parse amount from various formats."""
        if not amount_str:
            return None
        cleaned = re.sub(r"[¥￥$€,\s]", "", amount_str)
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_date(self, date_str: str) -> "date | None":
        """Try multiple date formats."""
        if not date_str:
            return None

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y.%m.%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
