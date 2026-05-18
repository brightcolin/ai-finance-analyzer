# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

AI Finance Analyzer is a **developer-first financial decision engine** that transforms raw expense data (WeChat Pay CSV, generic CSV) into structured financial insights and actionable recommendations. It is not a bookkeeping app — it's a programmable Python SDK for financial analysis.

**Core principle:** AI used strategically, determinism enforced elsewhere. LLM is used only for advice generation; parsing, classification, and statistical analysis are deterministic and rule-based.

## Commands

```bash
# Install (full with dev tools and LLM support)
pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Run single test
pytest tests/test_all.py::test_parser_wechat -v

# Run with coverage
pytest tests/ --cov=analyzer --cov-report=term-missing

# Lint
ruff check src/

# Run demo
python examples/quickstart.py
```

## Architecture: Four Sequential Layers

```
Raw Bill (CSV/XLSX)
    ↓
[PARSER]      — Format detection & conversion to Transaction objects
    ↓
[CLASSIFIER]  — Rules-first (keyword matching), optional LLM fallback
    ↓
[ANALYZER]    — Deterministic stats: health score, trends, risks (no AI)
    ↓
[ADVISOR]     — Advice generation (LLM via DeepSeek, or intelligent mock)
    ↓
FullReport = AnalysisReport + FinancialAdvice
```

### Parser (`src/analyzer/parser/`)
Pluggable architecture: extend `BaseParser`, register with `register_parser()`. Supports WeChat Pay CSV/XLSX and generic CSV with auto-detection. Outputs standardized `Transaction` objects.

### Classifier (`src/analyzer/classifier/`)
Two-tier strategy:
1. **Rules engine** (primary): Fast keyword matching against `rules.json` — 11 categories, Chinese-optimized
2. **LLM fallback** (optional): Activates for items below 0.5 confidence threshold, requires API key

### Analyzer (`src/analyzer/engine/`)
Four sub-modules — `structure.py` (totals, category breakdown, savings rate), `trends.py` (monthly aggregates, volatility index), `health.py` (5-component weighted score 0–100), `risks.py` (automatic alert detection). Entirely deterministic; no AI.

**Health Score components** (default weights): Savings Rate 30%, Essential Ratio 25%, Stability 20%, Diversity 15%, Trend 10%. Grades: A (90+), B (75+), C (60+), D (40+), F (<40).

**Risk alerts triggered by**: category over-concentration (>35%), low savings rate (<10%), spending anomalies (>2σ), accelerating trend.

### Advisor (`src/advisor/`)
Two modes: **LLM mode** (requires `DEEPSEEK_API_KEY`, uses DeepSeek via OpenAI-compatible API) or **mock mode** (data-driven suggestions from actual metrics — not generic templates, works offline).

## Data Models (`src/analyzer/models/schemas.py`)

All layers communicate via dataclasses: `Transaction` → `CategorizedTransaction` → `AnalysisReport` → `FullReport`. `AnalysisReport.to_llm_context()` serializes only aggregated metrics — raw transactions never leave the machine.

## Public API

```python
from analyzer import run_pipeline, analyze_transactions, get_advice
```

Lower-level access via sub-packages: `analyzer.parser`, `analyzer.classifier`, `analyzer.engine`, `analyzer.advisor`.

## Configuration

Environment variables (load from `.env`):
- `DEEPSEEK_API_KEY` — enables LLM advice; if unset, mock advisor is used
- `LLM_BASE_URL` — default: `https://api.deepseek.com`
- `LLM_MODEL` — default: `deepseek-chat`

Programmatic config via `src/analyzer/core/config.py`:

```python
from analyzer.core.config import Config, AnalyzerConfig, set_config
set_config(Config(analyzer=AnalyzerConfig(weight_savings_rate=0.40)))
```

## Key Files

- `pyproject.toml` — dependencies, pytest config (70% coverage minimum), ruff config
- `src/analyzer/classifier/rules.json` — keyword rules for 11 spending categories
- `examples/quickstart.py` — runnable demo showing all result types
- `tests/test_all.py` — single comprehensive test suite; no external API calls (mock enforced)
- `.github/workflows/ci.yml` — CI runs on Python 3.10, 3.11, 3.12
