# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-06

Initial release.

### Added

**Core pipeline** — four sequential processing layers exposed via a single `run_pipeline()` call:

- **Parser** — format detection and conversion to `Transaction` objects; supports WeChat Pay CSV/XLSX and generic CSV with auto-detected column mapping; pluggable via `BaseParser` + `register_parser()`
- **Classifier** — two-tier strategy: keyword rules engine (`rules.json`, 11 categories, Chinese-optimized) as primary path, optional LLM fallback (DeepSeek) for low-confidence items below a configurable threshold
- **Analyzer** — deterministic statistical engine (no AI); computes category breakdown, monthly trends, volatility index, a 5-component weighted health score (0–100, grades A–F), and automatic risk alerts
- **Advisor** — advice generation in two modes: LLM mode via DeepSeek (OpenAI-compatible API) or offline mock mode that generates data-driven suggestions from actual metrics

**Data models** (`schemas.py`) — typed dataclass pipeline: `Transaction` → `CategorizedTransaction` → `AnalysisReport` → `FullReport`; raw transactions never leave the machine (only aggregated metrics sent to LLM)

**Public API**:
```python
from analyzer import run_pipeline, analyze_transactions, get_advice
```

**Configuration** — environment variables (`DEEPSEEK_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`) and programmatic config via `AnalyzerConfig` (adjustable health score weights, alert thresholds)

**Sample data**:
- `examples/sample_wechat.csv` — WeChat Pay bill (CNY, 3 months)
- `examples/sample_generic.csv` — generic CSV with English descriptions and USD amounts (Starbucks, Uber, Amazon, DoorDash, Netflix, etc.) for non-WeChat users

**CLI** (`ai-finance`) — installed automatically with the package:
```bash
ai-finance analyze bill.csv               # text output
ai-finance analyze bill.csv --format json # structured JSON for scripting
ai-finance analyze bill.csv --no-ai       # offline: rules engine + mock advisor
ai-finance --version
```

**Currency auto-detection** — `GenericCSVParser` infers currency from amount symbols in the file (`$` → USD, `€` → EUR, `£` → GBP, `¥/￥` → CNY); falls back to `CURRENCY` env var, then CNY. Detected currency propagates through `AnalysisReport.currency` so the mock advisor and LLM prompts use the correct symbol without any configuration.

**Tooling**:
- `examples/quickstart.py` — runnable demo; accepts an optional file path argument, works with both sample datasets
- CI via GitHub Actions (Python 3.10, 3.11, 3.12; 70% coverage minimum enforced)
- Linting via ruff

[0.1.0]: https://github.com/brightcolin/ai-finance-analyzer/releases/tag/v0.1.0
