# Contributing to AI Finance Analyzer

Contributions are welcome. This document covers environment setup, the PR workflow, and the two most common extension points: adding a new Parser and improving classification rules.

## Setup

```bash
git clone https://github.com/brightcolin/ai-finance-analyzer.git
cd ai-finance-analyzer
pip install -e ".[all]"
```

Verify everything works:

```bash
pytest tests/ -v
ruff check src/
```

## PR Workflow

1. Fork the repo and create a branch off `main` (`feat/alipay-parser`, `fix/...`, etc.)
2. Make your changes — tests must pass and coverage must stay above 70%
3. Run `ruff check src/` before pushing; CI will reject lint failures
4. Open a PR against `main` with a short description of what and why

There are no issue templates yet. For larger changes, open an issue first to align on direction before writing code.

## Adding a New Parser

Parsers live in `src/analyzer/parser/`. The steps to add one:

**1. Create your parser file** and inherit from `BaseParser`:

```python
# src/analyzer/parser/alipay.py
from analyzer.parser.base import BaseParser
from analyzer.models.schemas import Transaction, TransactionType

class AlipayParser(BaseParser):
    @property
    def name(self) -> str:
        return "Alipay CSV"

    @property
    def supported_formats(self) -> list[str]:
        return [".csv"]

    def can_handle(self, filepath) -> bool:
        # Use header sniffing, not just file extension
        content = self._read_file(filepath)
        return "支付宝" in content.splitlines()[0]

    def parse(self, filepath) -> list[Transaction]:
        # Return a list[Transaction]; use self._read_file() for
        # encoding-safe reads (handles utf-8, gbk, gb2312 automatically)
        ...
```

`BaseParser._read_file()` handles encoding fallback (UTF-8 → UTF-8-BOM → GBK → GB2312 → Latin-1) so you don't need to manage that yourself.

**2. Register your parser** in `src/analyzer/parser/__init__.py` so it participates in auto-detection:

```python
from analyzer.parser.alipay import AlipayParser
register_parser(AlipayParser())
```

Parsers are tried in registration order; the first one where `can_handle()` returns `True` wins. `GenericCSVParser` is always registered last as the fallback.

**3. Add tests** in `tests/test_all.py`. Use a small inline fixture (5–10 rows) rather than a file on disk:

```python
def test_parser_alipay(tmp_path):
    csv_content = "支付宝...\n..."
    f = tmp_path / "bill.csv"
    f.write_text(csv_content, encoding="utf-8")
    txs = parse_file(f)
    assert len(txs) == ...
    assert txs[0].amount == ...
```

**4. Add sample data** (optional but encouraged): `examples/sample_alipay.csv` so users can test against a real file.

## Improving Classification Rules

Rules live in `src/analyzer/classifier/rules.json`. Each category has a list of keyword arrays — a transaction matches if **any** keyword in any sub-array appears in its description (case-insensitive).

To add or adjust keywords, edit the relevant category directly. The rules engine is the primary classification path (no API cost, no latency), so good rules have more impact than LLM improvements.

When adding keywords for non-Chinese merchants (e.g., "uber", "starbucks"), add them under the appropriate category. The classifier already lowercases all input before matching.

## What's Most Useful Right Now

From the README roadmap — highest-impact contributions:

- **Alipay parser** (`src/analyzer/parser/alipay.py`) — most requested format
- **Bank statement CSV parsers** — any major bank format
- **English/international classification rules** in `rules.json` — the current ruleset is Chinese-optimized
