# AI Finance Analyzer

**Turn raw expense data into actionable financial insights, not just reports.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://github.com/brightcolin/ai-finance-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/brightcolin/ai-finance-analyzer/actions)

---

![Demo](demo.gif)

## What This Is

AI Finance Analyzer is a **developer-first AI financial decision engine**. It takes raw expense data (WeChat Pay CSV, etc.) and produces structured analysis with actionable, quantified suggestions.

**This is NOT** another bookkeeping app, budgeting tool, or expense tracker.

**This IS** a programmable analysis engine that answers: *"What should I do about my money?"*

```python
from analyzer import run_pipeline

report = run_pipeline("wechat_bill.csv")
print(f"Health Score: {report.analysis.health_score.total_score}/100")
# → Health Score: 72/100

for s in report.advice.suggestions:
    print(f"[{s.priority}] {s.action}")
# → [high] Reduce food spending by 20% — cut back on: 美团外卖, 饿了么
#   → Save approximately ¥300/month
```

## How It's Different

| | Traditional Tools | AI Finance Analyzer |
|---|---|---|
| **Purpose** | Record what happened | Decide what to do |
| **Output** | Charts & tables | Actionable suggestions with numbers |
| **AI Role** | Bolt-on classifier | Core decision engine |
| **Target** | End users (app) | Developers (SDK) |
| **Data Flow** | Data → Category → Chart | Data → Understanding → Behavior Analysis → Decision |

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Parser     │ ──→ │  Classifier  │ ──→ │   Analyzer   │ ──→ │   Advisor    │
│  (Input)     │     │(Understanding)│     │  (Insight)   │     │ (Decision)   │
├──────────────┤     ├──────────────┤     ├──────────────┤     ├──────────────┤
│ WeChat CSV   │     │ Rules Engine │     │ Structure    │     │ DeepSeek LLM │
│ Generic CSV  │     │ + LLM Backup │     │ Trends       │     │ Prompt Eng.  │
│ (Pluggable)  │     │              │     │ Health Score │     │ Mock Mode    │
│              │     │              │     │ Risk Alerts  │     │              │
│  ❌ No AI    │     │  ⚠️ AI Assist │     │  ❌ No AI    │     │  ✅ AI Core  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

AI is used precisely where it adds value (reasoning & language generation) and avoided where determinism matters (parsing & statistics).

## Quick Start

### 1. Install

```bash
git clone https://github.com/yourusername/ai-finance-analyzer.git
cd ai-finance-analyzer
pip install -e ".[all]"
```

### 2. Run the Demo

```bash
python examples/quickstart.py
```

### 3. Use in Your Code

```python
from analyzer import run_pipeline

# Full pipeline: parse → classify → analyze → advise
report = run_pipeline("your_wechat_bill.csv")

# Access structured analysis
print(report.analysis.health_score)      # HealthScore(72, grade='B')
print(report.analysis.savings_rate)       # 0.23
print(report.analysis.category_breakdown) # [CategoryBreakdown(...), ...]
print(report.analysis.risk_alerts)        # [RiskAlert(...), ...]

# Access AI-generated advice
print(report.advice.summary)
print(report.advice.suggestions)
```

### 4. Enable AI Advice (Optional)

```bash
export DEEPSEEK_API_KEY="your-key-here"
```

Without an API key, the system uses intelligent mock advice based on your actual data patterns.

## CLI

`ai-finance` is installed automatically with the package — no extra steps needed.

```bash
# Analyze a bill and print a formatted report
ai-finance analyze bill.csv

# Output JSON (useful for scripting or piping into other tools)
ai-finance analyze bill.csv --format json

# Offline mode — rules engine + mock advisor, no API key required
ai-finance analyze bill.csv --no-ai

# Try it immediately with the included English sample
ai-finance analyze examples/sample_generic.csv --no-ai
```

Sample output:

```
============================================================
  AI Finance Analyzer  —  sample_generic.csv
============================================================

ANALYSIS
  Period:        2026-01-02  to  2026-03-31
  Transactions:  77
  Total Expense: 9,203.72
  Total Income:  15,000.00
  Savings Rate:  38.6%

HEALTH SCORE: 78/100  (Grade B)
  savings_rate           [##################..] 94
  essential_ratio        [#########...........] 48
  ...

RISK ALERTS
  [HIGH] housing spending accounts for 59% of total expenses

AI ADVICE
  Your savings rate is strong at 38.6%. Main risk is housing concentration.

  1. [HIGH] Reduce housing spending by 20% ...
       -> Save approximately $1,080/month
```

## Core Metrics

### Financial Health Score (0-100)

A weighted composite score based on:
- **Savings Rate** (30%) — Are you saving enough?
- **Essential Ratio** (25%) — Is spending on necessities balanced?
- **Stability** (20%) — How consistent are your spending patterns?
- **Diversity** (15%) — Is spending spread across categories?
- **Trend** (10%) — Is spending going up or down?

### Spending Volatility Index

Measures spending consistency using the Coefficient of Variation across monthly totals. Lower = more stable habits.

### Risk Alerts

Automatic detection of: category over-concentration (>35%), low savings rate (<10%), spending spikes, and trend acceleration.

## API Reference

| Function | Description |
|---|---|
| `run_pipeline(file)` | End-to-end: file → FullReport |
| `analyze_transactions(txs)` | Analyze pre-parsed transactions |
| `get_advice(report)` | Generate advice from analysis |
| `parse_file(file)` | Parse bill file → transactions |
| `classify(transactions)` | Classify → categorized transactions |

## Supported Formats

- ✅ WeChat Pay (微信支付) CSV
- ✅ Generic CSV (auto-detect columns)
- 🔜 Alipay (支付宝) CSV
- 🔜 Bank statement CSV
- 🔜 Screenshot OCR

## Project Structure

```
src/analyzer/
├── parser/          # Layer 1: Data parsing (pluggable)
├── classifier/      # Layer 2: Rules + LLM classification
├── engine/          # Layer 3: Statistical analysis
├── advisor/         # Layer 4: AI decision generation
├── models/          # Shared data schemas
├── core/            # Configuration
└── pipeline.py      # Orchestrator
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=analyzer --cov-report=term-missing

# Lint
ruff check src/
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | (none) | DeepSeek API key for AI features |
| `LLM_BASE_URL` | `https://api.deepseek.com` | LLM API endpoint |
| `LLM_MODEL` | `deepseek-chat` | Model name |
| `DEBUG` | `false` | Enable debug logging |

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, PR workflow, and how to add a new Parser.

## License

MIT — see [LICENSE](LICENSE) for details.
