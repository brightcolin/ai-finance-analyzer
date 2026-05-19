"""
CLI for AI Finance Analyzer.

Usage:
    ai-finance analyze bill.csv
    ai-finance analyze bill.csv --format json
    ai-finance analyze bill.csv --no-ai
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

# Ensure UTF-8 output on Windows terminals (handles emojis and non-ASCII in data)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from analyzer import __version__, run_pipeline

app = typer.Typer(
    name="ai-finance",
    help="Turn raw expense data into actionable financial insights.",
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ai-finance-analyzer {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V",
        callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


@app.command()
def analyze(
    file: Path = typer.Argument(..., help="Path to the bill file (CSV or XLSX)."),
    output_format: OutputFormat = typer.Option(
        OutputFormat.TEXT, "--format", "-f", help="Output format: text or json.",
    ),
    no_ai: bool = typer.Option(
        False, "--no-ai", help="Disable LLM; use rules engine + mock advisor.",
    ),
) -> None:
    """Analyze a bill file and print financial insights."""
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    use_llm = not no_ai
    try:
        report = run_pipeline(file, use_llm_classify=use_llm, use_llm_advice=use_llm)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        _print_json(report)
    else:
        _print_text(report, file)


def _print_text(report, file: Path) -> None:
    a = report.analysis
    W = 60

    typer.echo("=" * W)
    typer.echo(f"  AI Finance Analyzer  —  {file.name}")
    typer.echo("=" * W)
    typer.echo()

    typer.echo("ANALYSIS")
    if a.start_date and a.end_date:
        typer.echo(f"  Period:        {a.start_date}  to  {a.end_date}")
    typer.echo(f"  Transactions:  {a.total_transactions}")
    typer.echo(f"  Total Expense: {a.total_expense:,.2f}")
    typer.echo(f"  Total Income:  {a.total_income:,.2f}")
    typer.echo(f"  Savings Rate:  {a.savings_rate:.1%}")
    typer.echo()

    if a.health_score:
        hs = a.health_score
        typer.echo(f"HEALTH SCORE: {hs.total_score:.0f}/100  (Grade {hs.grade})")
        for component, score in hs.components.items():
            bar = "#" * int(score / 5) + "." * (20 - int(score / 5))
            typer.echo(f"  {component:22s} [{bar}] {score:.0f}")
        typer.echo()

    if a.category_breakdown:
        typer.echo("CATEGORY BREAKDOWN")
        for cb in a.category_breakdown[:8]:
            bar = "#" * int(cb.percentage * 36)
            typer.echo(
                f"  {cb.category.value:15s}  {cb.total:>10,.2f}  {cb.percentage:5.1%}  {bar}"
            )
        typer.echo()

    if a.risk_alerts:
        typer.echo("RISK ALERTS")
        labels = {"high": "[HIGH]", "medium": "[MED] ", "low": "[LOW] "}
        for alert in a.risk_alerts:
            typer.echo(f"  {labels.get(alert.level, '[???]')} {alert.message}")
        typer.echo()

    if report.advice:
        adv = report.advice
        labels = {"high": "[HIGH]", "medium": "[MED] ", "low": "[LOW] "}
        typer.echo("AI ADVICE")
        typer.echo(f"  {adv.summary}")
        typer.echo()
        for i, s in enumerate(adv.suggestions, 1):
            typer.echo(f"  {i}. {labels.get(s.priority, '[    ]')} {s.action}")
            typer.echo(f"       -> {s.expected_impact}")
            typer.echo()
        if adv.encouragement:
            typer.echo(f"  {adv.encouragement}")
        typer.echo()

    typer.echo("=" * W)


def _json_default(obj: object) -> str:
    if isinstance(obj, date):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _print_json(report) -> None:
    typer.echo(json.dumps(asdict(report), default=_json_default, indent=2, ensure_ascii=False))
