"""
WeChat Pay (微信支付) bill parser.

Handles BOTH formats exported from WeChat Pay:
  - Legacy: Plain CSV text files (older WeChat versions)
  - Current: Excel (.xlsx) files with .csv extension (2025+ WeChat versions)

Both formats share the same column structure:
  - First ~16 rows are metadata headers
  - Data starts after a header row with known column names
  - Columns: 交易时间, 交易类型, 交易对方, 商品, 收/支, 金额(元), etc.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from analyzer.models.schemas import Transaction, TransactionType
from analyzer.parser.base import BaseParser

# Known WeChat header signatures
WECHAT_SIGNATURES = [
    "微信支付账单明细",
    "WeChat Pay Bill",
    "交易时间",
]

# Column name mappings (Chinese -> internal key)
COLUMN_ALIASES = {
    "交易时间": "time",
    "Transaction Time": "time",
    "交易类型": "tx_type",
    "Transaction Type": "tx_type",
    "交易对方": "counterparty",
    "Counterparty": "counterparty",
    "商品": "description",
    "Product": "description",
    "Description": "description",
    "收/支": "direction",
    "Income/Expense": "direction",
    "金额(元)": "amount",
    "Amount(CNY)": "amount",
    "金额": "amount",
    "支付方式": "payment_method",
    "Payment Method": "payment_method",
    "当前状态": "status",
    "Current Status": "status",
    "交易单号": "tx_id",
    "Transaction ID": "tx_id",
    "商户单号": "merchant_id",
    "Merchant ID": "merchant_id",
    "备注": "notes",
    "Notes": "notes",
}

# Direction indicators
INCOME_INDICATORS = ["收入", "Income"]
NEUTRAL_INDICATORS = ["不计收支", "N/A"]

# Statuses to skip
SKIP_STATUSES = [
    "已退款", "退款成功", "已全额退款", "对方已退还",
    "Refunded", "Full Refund",
    "已关闭", "交易关闭", "Closed",
]


def _is_xlsx_file(filepath: Path) -> bool:
    """Check if a file is actually an Excel/ZIP file regardless of extension."""
    try:
        with open(filepath, "rb") as f:
            magic = f.read(4)
            return magic == b"PK\x03\x04"  # ZIP magic bytes (XLSX is a ZIP)
    except Exception:
        return False


class WeChatParser(BaseParser):
    """Parser for WeChat Pay exported bills (CSV or Excel)."""

    @property
    def name(self) -> str:
        return "WeChat Pay"

    @property
    def supported_formats(self) -> list[str]:
        return [".csv", ".xlsx"]

    def can_handle(self, filepath: str | Path) -> bool:
        """Detect WeChat bill by checking file content."""
        path = Path(filepath)

        # Check 1: Is it an Excel file (new WeChat format)?
        if _is_xlsx_file(path):
            try:
                rows = self._read_xlsx_rows(path, max_rows=5)
                first_values = " ".join(
                    str(cell) for row in rows for cell in row if cell
                )
                return any(sig in first_values for sig in WECHAT_SIGNATURES)
            except Exception:
                return False

        # Check 2: Is it a text CSV (legacy WeChat format)?
        try:
            content = self._read_file(filepath)
            first_chunk = content[:2000]
            return any(sig in first_chunk for sig in WECHAT_SIGNATURES)
        except Exception:
            return False

    def parse(self, filepath: str | Path) -> list[Transaction]:
        """Parse a WeChat Pay bill file (auto-detects CSV vs Excel)."""
        path = Path(filepath)

        if _is_xlsx_file(path):
            return self._parse_xlsx(path)
        else:
            return self._parse_csv(path)

    # ─── Excel (XLSX) parsing ───────────────────────────────

    def _read_xlsx_rows(
        self, filepath: Path, max_rows: int | None = None
    ) -> list[tuple]:
        """Read rows from an Excel file using openpyxl."""
        try:
            import openpyxl
        except ImportError:
            raise ImportError(
                "openpyxl is required to read WeChat Excel bills. "
                "Install with: pip install openpyxl"
            )

        # openpyxl refuses non-.xlsx extensions, so use a temp copy
        actual_path = filepath
        tmp_path = None
        if filepath.suffix.lower() != ".xlsx":
            tmp_path = Path(tempfile.mktemp(suffix=".xlsx"))
            shutil.copy2(filepath, tmp_path)
            actual_path = tmp_path

        try:
            wb = openpyxl.load_workbook(actual_path, read_only=True)
            ws = wb.active
            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                rows.append(row)
                if max_rows and i >= max_rows:
                    break
            wb.close()
            return rows
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

    def _parse_xlsx(self, filepath: Path) -> list[Transaction]:
        """Parse an Excel-format WeChat bill."""
        rows = self._read_xlsx_rows(filepath)

        # Find header row
        header_idx = None
        header_row = None
        target_columns = {"交易时间", "Transaction Time", "金额(元)", "Amount(CNY)", "金额"}

        for i, row in enumerate(rows):
            row_values = [str(cell).strip() if cell else "" for cell in row]
            if any(col in row_values for col in target_columns):
                header_idx = i
                header_row = row_values
                break

        if header_idx is None or header_row is None:
            raise ValueError(
                "Cannot find data header row in WeChat Excel bill. "
                "Expected columns like '交易时间' or '金额(元)'."
            )

        # Build column index mapping
        col_map: dict[str, int] = {}
        for col_idx, col_name in enumerate(header_row):
            clean = col_name.strip()
            if clean in COLUMN_ALIASES:
                internal_key = COLUMN_ALIASES[clean]
                if internal_key not in col_map:
                    col_map[internal_key] = col_idx

        # Parse data rows
        transactions = []
        for row in rows[header_idx + 1:]:
            try:
                tx = self._parse_xlsx_row(row, col_map)
                if tx is not None:
                    transactions.append(tx)
            except Exception:
                continue

        return transactions

    def _parse_xlsx_row(
        self, row: tuple, col_map: dict[str, int]
    ) -> Transaction | None:
        """Parse a single Excel row into a Transaction."""

        def get(key: str) -> Any:
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        def get_str(key: str) -> str:
            val = get(key)
            if val is None:
                return ""
            s = str(val).strip()
            return "" if s == "/" else s  # WeChat uses "/" for empty fields

        # Check status
        status = get_str("status")
        if status and any(skip in status for skip in SKIP_STATUSES):
            return None

        # Parse direction
        direction = get_str("direction")
        tx_type = self._parse_direction(direction)
        if tx_type is None:
            return None

        # Parse amount — in Excel format it's already a number
        raw_amount = get("amount")
        amount = self._normalize_amount(raw_amount)
        if amount is None or amount == 0:
            return None

        # Parse date — in Excel format it's already a datetime object
        raw_time = get("time")
        tx_date = self._normalize_date(raw_time)
        if tx_date is None:
            return None

        # Build description
        description = get_str("description") or get_str("counterparty") or ""
        counterparty = get_str("counterparty") or ""
        notes = get_str("notes")

        raw_parts = [counterparty, description, notes]
        raw_text = " | ".join(p for p in raw_parts if p)

        return Transaction(
            amount=amount,
            description=description,
            date=tx_date,
            raw_text=raw_text,
            counterparty=counterparty,
            tx_type=tx_type,
            payment_method=get_str("payment_method"),
            currency="CNY",
        )

    def _normalize_amount(self, value: Any) -> float | None:
        """Normalize amount from either number or string."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return abs(float(value))
        return self._parse_amount(str(value))

    def _normalize_date(self, value: Any) -> date | None:
        """Normalize date from either datetime object or string."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return self._parse_datetime(str(value))

    # ─── CSV (text) parsing ─────────────────────────────────

    def _parse_csv(self, filepath: Path) -> list[Transaction]:
        """Parse a text CSV WeChat bill (legacy format)."""
        content = self._read_file(filepath)
        lines = content.strip().split("\n")

        header_idx = self._find_csv_header_row(lines)
        if header_idx is None:
            raise ValueError(
                "Cannot find data header row in WeChat CSV. "
                "Expected columns like '交易时间' or 'Transaction Time'."
            )

        data_text = "\n".join(lines[header_idx:])
        reader = csv.DictReader(io.StringIO(data_text))
        csv_col_map = self._build_csv_column_map(reader.fieldnames or [])

        transactions = []
        for row in reader:
            try:
                tx = self._parse_csv_row(row, csv_col_map)
                if tx is not None:
                    transactions.append(tx)
            except Exception:
                continue

        return transactions

    def _find_csv_header_row(self, lines: list[str]) -> int | None:
        """Find the line index containing the actual data header."""
        target_columns = {"交易时间", "Transaction Time", "金额(元)", "Amount(CNY)", "金额"}
        for i, line in enumerate(lines):
            if any(col in line for col in target_columns):
                return i
        return None

    def _build_csv_column_map(self, fieldnames: list[str]) -> dict[str, str]:
        """Map actual CSV column names to internal keys."""
        col_map = {}
        for fname in fieldnames:
            clean = fname.strip().strip("\ufeff")
            if clean in COLUMN_ALIASES:
                col_map[COLUMN_ALIASES[clean]] = fname
        return col_map

    def _parse_csv_row(
        self, row: dict[str, str], col_map: dict[str, str]
    ) -> Transaction | None:
        """Parse a single CSV text row into a Transaction."""

        def get(key: str) -> str:
            col_name = col_map.get(key, "")
            val = row.get(col_name, "").strip() if col_name else ""
            return "" if val == "/" else val

        status = get("status")
        if status and any(skip in status for skip in SKIP_STATUSES):
            return None

        direction = get("direction")
        tx_type = self._parse_direction(direction)
        if tx_type is None:
            return None

        amount = self._parse_amount(get("amount"))
        if amount is None or amount == 0:
            return None

        tx_date = self._parse_datetime(get("time"))
        if tx_date is None:
            return None

        description = get("description") or get("counterparty") or ""
        counterparty = get("counterparty") or ""
        notes = get("notes")

        raw_parts = [counterparty, description, notes]
        raw_text = " | ".join(p for p in raw_parts if p)

        return Transaction(
            amount=amount,
            description=description,
            date=tx_date,
            raw_text=raw_text,
            counterparty=counterparty,
            tx_type=tx_type,
            payment_method=get("payment_method"),
            currency="CNY",
        )

    # ─── Shared helpers ─────────────────────────────────────

    def _parse_direction(self, direction: str) -> TransactionType | None:
        """Parse 收/支 field. Returns None for neutral (不计收支)."""
        if not direction:
            return TransactionType.EXPENSE

        if any(ind in direction for ind in INCOME_INDICATORS):
            return TransactionType.INCOME
        if any(ind in direction for ind in NEUTRAL_INDICATORS):
            return None
        return TransactionType.EXPENSE

    def _parse_amount(self, amount_str: str) -> float | None:
        """Parse amount string, removing currency symbols."""
        if not amount_str:
            return None
        cleaned = re.sub(r"[¥￥,\s]", "", amount_str)
        cleaned = cleaned.replace("CNY", "").strip()
        try:
            return abs(float(cleaned))
        except ValueError:
            return None

    def _parse_datetime(self, time_str: str) -> date | None:
        """Parse various datetime string formats from WeChat."""
        if not time_str:
            return None
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
