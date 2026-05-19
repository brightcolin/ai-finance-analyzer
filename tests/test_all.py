"""
Test suite for AI Finance Analyzer.

Covers all four layers: Parser, Classifier, Analyzer, Advisor.
Run with: pytest tests/ -v
"""

import sys
from datetime import date
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analyzer.models.schemas import (
    AnalysisReport,
    Category,
    CategorizedTransaction,
    ClassificationMethod,
    FullReport,
    HealthScore,
    Transaction,
    TransactionType,
)


# ═══════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════


@pytest.fixture
def sample_csv_path():
    return Path(__file__).parent.parent / "examples" / "sample_wechat.csv"


@pytest.fixture
def sample_transactions():
    """Create a set of test transactions."""
    return [
        Transaction(amount=25.0, description="美团外卖-午餐", date=date(2026, 1, 5),
                     counterparty="美团外卖", tx_type=TransactionType.EXPENSE),
        Transaction(amount=30.0, description="滴滴出行-快车", date=date(2026, 1, 5),
                     counterparty="滴滴出行", tx_type=TransactionType.EXPENSE),
        Transaction(amount=599.0, description="Nike运动鞋", date=date(2026, 1, 7),
                     counterparty="淘宝", tx_type=TransactionType.EXPENSE),
        Transaction(amount=8500.0, description="1月工资", date=date(2026, 1, 25),
                     counterparty="公司", tx_type=TransactionType.INCOME),
        Transaction(amount=198.0, description="Steam游戏", date=date(2026, 1, 18),
                     counterparty="Steam", tx_type=TransactionType.EXPENSE),
        Transaction(amount=50.0, description="话费充值", date=date(2026, 1, 6),
                     counterparty="中国移动", tx_type=TransactionType.EXPENSE),
        Transaction(amount=35.0, description="感冒药", date=date(2026, 1, 20),
                     counterparty="药房", tx_type=TransactionType.EXPENSE),
        Transaction(amount=100.0, description="地铁充值", date=date(2026, 1, 8),
                     counterparty="地铁", tx_type=TransactionType.EXPENSE),
        # Feb transactions
        Transaction(amount=38.0, description="美团外卖-麻辣香锅", date=date(2026, 2, 18),
                     counterparty="美团外卖", tx_type=TransactionType.EXPENSE),
        Transaction(amount=358.0, description="西贝莜面村-聚餐", date=date(2026, 2, 14),
                     counterparty="西贝莜面村", tx_type=TransactionType.EXPENSE),
        Transaction(amount=8500.0, description="2月工资", date=date(2026, 2, 25),
                     counterparty="公司", tx_type=TransactionType.INCOME),
    ]


@pytest.fixture
def categorized_transactions(sample_transactions):
    """Pre-classified transactions for engine tests."""
    mapping = {
        "美团外卖-午餐": Category.FOOD,
        "滴滴出行-快车": Category.TRANSPORT,
        "Nike运动鞋": Category.SHOPPING,
        "1月工资": Category.INCOME,
        "Steam游戏": Category.ENTERTAINMENT,
        "话费充值": Category.UTILITIES,
        "感冒药": Category.HEALTH,
        "地铁充值": Category.TRANSPORT,
        "美团外卖-麻辣香锅": Category.FOOD,
        "西贝莜面村-聚餐": Category.FOOD,
        "2月工资": Category.INCOME,
    }
    return [
        CategorizedTransaction(
            transaction=tx,
            category=mapping.get(tx.description, Category.OTHER),
            confidence=0.9,
            method=ClassificationMethod.RULE,
        )
        for tx in sample_transactions
    ]


# ═══════════════════════════════════════════════════
# Parser Tests
# ═══════════════════════════════════════════════════


class TestWeChatParser:
    def test_parse_sample_file(self, sample_csv_path):
        from analyzer.parser import parse_file

        transactions = parse_file(sample_csv_path)
        assert len(transactions) > 0
        assert all(isinstance(tx, Transaction) for tx in transactions)

    def test_parse_amounts(self, sample_csv_path):
        from analyzer.parser import parse_file

        transactions = parse_file(sample_csv_path)
        for tx in transactions:
            assert tx.amount > 0
            assert isinstance(tx.amount, float)

    def test_parse_dates(self, sample_csv_path):
        from analyzer.parser import parse_file

        transactions = parse_file(sample_csv_path)
        for tx in transactions:
            assert isinstance(tx.date, date)
            assert tx.date.year == 2026

    def test_parse_transaction_types(self, sample_csv_path):
        from analyzer.parser import parse_file

        transactions = parse_file(sample_csv_path)
        types = {tx.tx_type for tx in transactions}
        assert TransactionType.EXPENSE in types
        assert TransactionType.INCOME in types

    def test_can_handle_detection(self, sample_csv_path):
        from analyzer.parser.wechat import WeChatParser

        parser = WeChatParser()
        assert parser.can_handle(sample_csv_path) is True

    def test_file_not_found(self):
        from analyzer.parser import parse_file

        with pytest.raises(FileNotFoundError):
            parse_file("/nonexistent/file.csv")


class TestGenericCSVParser:
    def test_can_handle_csv(self, tmp_path):
        from analyzer.parser.csv_generic import GenericCSVParser

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,amount,description\n2026-01-01,100,Test\n")
        parser = GenericCSVParser()
        assert parser.can_handle(csv_file) is True

    def test_parse_simple_csv(self, tmp_path):
        from analyzer.parser.csv_generic import GenericCSVParser

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "date,amount,description\n"
            "2026-01-01,50.00,Lunch\n"
            "2026-01-02,30.00,Coffee\n"
        )
        parser = GenericCSVParser()
        transactions = parser.parse(csv_file)
        assert len(transactions) == 2
        assert transactions[0].amount == 50.0


# ═══════════════════════════════════════════════════
# Classifier Tests
# ═══════════════════════════════════════════════════


class TestRulesEngine:
    def test_food_classification(self):
        from analyzer.classifier.rules_engine import RulesEngine

        engine = RulesEngine()
        tx = Transaction(
            amount=25, description="美团外卖-午餐",
            date=date(2026, 1, 1), counterparty="美团外卖"
        )
        result = engine.classify(tx)
        assert result.category == Category.FOOD
        assert result.confidence > 0.5

    def test_transport_classification(self):
        from analyzer.classifier.rules_engine import RulesEngine

        engine = RulesEngine()
        tx = Transaction(
            amount=30, description="快车",
            date=date(2026, 1, 1), counterparty="滴滴出行"
        )
        result = engine.classify(tx)
        assert result.category == Category.TRANSPORT

    def test_income_classification(self):
        from analyzer.classifier.rules_engine import RulesEngine

        engine = RulesEngine()
        tx = Transaction(
            amount=8500, description="工资",
            date=date(2026, 1, 1), tx_type=TransactionType.INCOME
        )
        result = engine.classify(tx)
        assert result.category == Category.INCOME

    def test_unknown_defaults_to_other(self):
        from analyzer.classifier.rules_engine import RulesEngine

        engine = RulesEngine()
        tx = Transaction(
            amount=100, description="XXXXUNKNOWNXXXX",
            date=date(2026, 1, 1)
        )
        result = engine.classify(tx)
        assert result.category == Category.OTHER
        assert result.confidence < 0.5

    def test_batch_classification(self, sample_transactions):
        from analyzer.classifier.rules_engine import RulesEngine

        engine = RulesEngine()
        results = engine.classify_batch(sample_transactions)
        assert len(results) == len(sample_transactions)


class TestClassifierIntegration:
    def test_classify_without_llm(self, sample_transactions):
        from analyzer.classifier import classify

        results = classify(sample_transactions, use_llm_fallback=False)
        assert len(results) == len(sample_transactions)
        # Check that known items are classified correctly
        food_items = [r for r in results if r.category == Category.FOOD]
        assert len(food_items) >= 2  # At least the 美团 items


# ═══════════════════════════════════════════════════
# Engine Tests
# ═══════════════════════════════════════════════════


class TestStructureAnalysis:
    def test_analyze_structure(self, categorized_transactions):
        from analyzer.engine.structure import analyze_structure

        breakdowns = analyze_structure(categorized_transactions)
        assert len(breakdowns) > 0
        # Percentages should sum to ~1.0
        total_pct = sum(b.percentage for b in breakdowns)
        assert abs(total_pct - 1.0) < 0.01

    def test_compute_totals(self, categorized_transactions):
        from analyzer.engine.structure import compute_totals

        expense, income = compute_totals(categorized_transactions)
        assert expense > 0
        assert income > 0
        assert income > expense  # Salary > expenses in test data

    def test_savings_rate(self):
        from analyzer.engine.structure import compute_savings_rate

        rate = compute_savings_rate(10000, 7000)
        assert rate == 0.3

        rate_zero = compute_savings_rate(0, 500)
        assert rate_zero == 0.0


class TestTrendAnalysis:
    def test_monthly_trends(self, categorized_transactions):
        from analyzer.engine.trends import analyze_monthly_trends

        overall, by_cat = analyze_monthly_trends(categorized_transactions)
        assert overall.label == "overall"
        assert len(overall.data_points) >= 1

    def test_volatility_index(self, categorized_transactions):
        from analyzer.engine.trends import compute_volatility_index

        vol = compute_volatility_index(categorized_transactions)
        assert isinstance(vol, float)
        assert vol >= 0


class TestHealthScore:
    def test_compute_health_score(self, categorized_transactions):
        from analyzer.engine.health import compute_health_score
        from analyzer.engine.structure import analyze_structure

        breakdowns = analyze_structure(categorized_transactions)
        score = compute_health_score(
            transactions=categorized_transactions,
            breakdowns=breakdowns,
            savings_rate=0.20,
            volatility_index=0.25,
            trend_direction="stable",
        )
        assert 0 <= score.total_score <= 100
        assert score.grade in ("A", "B", "C", "D", "F")
        assert len(score.components) == 5

    def test_score_grade_mapping(self):
        score_a = HealthScore(total_score=95)
        assert score_a.grade == "A"

        score_f = HealthScore(total_score=30)
        assert score_f.grade == "F"


class TestRiskDetection:
    def test_detect_risks(self, categorized_transactions):
        from analyzer.engine.risks import detect_risks
        from analyzer.engine.structure import analyze_structure, compute_savings_rate, compute_totals
        from analyzer.engine.trends import analyze_monthly_trends, compute_volatility_index

        breakdowns = analyze_structure(categorized_transactions)
        expense, income = compute_totals(categorized_transactions)
        savings_rate = compute_savings_rate(income, expense)
        volatility = compute_volatility_index(categorized_transactions)
        overall, _ = analyze_monthly_trends(categorized_transactions)

        risks = detect_risks(breakdowns, savings_rate, volatility, overall)
        assert isinstance(risks, list)


class TestEngineIntegration:
    def test_full_analysis(self, categorized_transactions):
        from analyzer.engine import analyze

        report = analyze(categorized_transactions)
        assert isinstance(report, AnalysisReport)
        assert report.total_expense > 0
        assert report.total_income > 0
        assert report.health_score is not None
        assert len(report.category_breakdown) > 0

    def test_empty_input(self):
        from analyzer.engine import analyze

        report = analyze([])
        assert report.total_transactions == 0


# ═══════════════════════════════════════════════════
# Advisor Tests
# ═══════════════════════════════════════════════════


class TestAdvisor:
    def test_mock_advice(self, categorized_transactions):
        from analyzer.advisor import generate_advice
        from analyzer.engine import analyze

        report = analyze(categorized_transactions)
        advice = generate_advice(report, use_mock=True)
        assert advice.summary != ""
        assert len(advice.suggestions) > 0
        assert advice.encouragement != ""

    def test_suggestion_structure(self, categorized_transactions):
        from analyzer.advisor import generate_advice
        from analyzer.engine import analyze

        report = analyze(categorized_transactions)
        advice = generate_advice(report, use_mock=True)
        for s in advice.suggestions:
            assert s.action != ""
            assert s.expected_impact != ""
            assert s.priority in ("high", "medium", "low")


# ═══════════════════════════════════════════════════
# Pipeline Tests
# ═══════════════════════════════════════════════════


class TestPipeline:
    def test_full_pipeline(self, sample_csv_path):
        from analyzer.pipeline import run_pipeline

        report = run_pipeline(
            sample_csv_path,
            use_llm_classify=False,
            use_llm_advice=False,
        )
        assert isinstance(report, FullReport)
        assert report.analysis.total_transactions > 0
        assert report.advice is not None
        assert len(report.advice.suggestions) > 0

    def test_pipeline_health_score(self, sample_csv_path):
        from analyzer.pipeline import run_pipeline

        report = run_pipeline(
            sample_csv_path,
            use_llm_classify=False,
            use_llm_advice=False,
        )
        assert report.analysis.health_score is not None
        assert 0 <= report.analysis.health_score.total_score <= 100

    def test_llm_context_privacy(self, sample_csv_path):
        """Verify that LLM context does NOT contain raw transaction details."""
        from analyzer.pipeline import run_pipeline

        report = run_pipeline(
            sample_csv_path,
            use_llm_classify=False,
            use_llm_advice=False,
        )
        context = report.analysis.to_llm_context()
        # Should have aggregated data, not individual transactions
        assert "category_breakdown" in context
        assert "health" in context
        # Should NOT have raw descriptions or counterparties
        context_str = str(context)
        assert "美团外卖" not in context_str
        assert "滴滴出行" not in context_str


# ═══════════════════════════════════════════════════
# Data Model Tests
# ═══════════════════════════════════════════════════


class TestModels:
    def test_transaction_date_parsing(self):
        tx = Transaction(amount=100, description="test", date="2026-01-15")
        assert tx.date == date(2026, 1, 15)

    def test_category_expense_filter(self):
        expense_cats = Category.expense_categories()
        assert Category.INCOME not in expense_cats
        assert Category.TRANSFER not in expense_cats
        assert Category.FOOD in expense_cats

    def test_health_score_grading(self):
        assert HealthScore(total_score=95).grade == "A"
        assert HealthScore(total_score=80).grade == "B"
        assert HealthScore(total_score=65).grade == "C"
        assert HealthScore(total_score=45).grade == "D"
        assert HealthScore(total_score=20).grade == "F"

    def test_analysis_report_currency_default(self):
        from analyzer.models.schemas import AnalysisReport
        report = AnalysisReport()
        assert report.currency == "CNY"


# ═══════════════════════════════════════════════════
# CLI Tests
# ═══════════════════════════════════════════════════


class TestCLI:
    @pytest.fixture
    def bill_csv(self, tmp_path):
        """Minimal USD bill CSV for CLI tests."""
        content = (
            "date,description,amount,category\n"
            "2026-01-10,Employer salary,-$3000.00,income\n"
            "2026-01-02,Starbucks,$5.50,food\n"
            "2026-01-03,Uber,$15.00,transport\n"
            "2026-01-04,Amazon,$50.00,shopping\n"
            "2026-01-05,Netflix,$15.00,entertainment\n"
            "2026-01-10,Rent,$900.00,housing\n"
            "2026-01-15,Electric bill,$80.00,utilities\n"
        )
        f = tmp_path / "bill.csv"
        f.write_text(content, encoding="utf-8")
        return f

    def test_version(self):
        from typer.testing import CliRunner
        from analyzer.cli import app
        result = CliRunner().invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_analyze_text_output(self, bill_csv):
        from typer.testing import CliRunner
        from analyzer.cli import app
        result = CliRunner().invoke(app, ["analyze", str(bill_csv), "--no-ai"])
        assert result.exit_code == 0
        assert "ANALYSIS" in result.output
        assert "HEALTH SCORE" in result.output
        assert "CATEGORY BREAKDOWN" in result.output
        assert "AI ADVICE" in result.output

    def test_analyze_json_output(self, bill_csv):
        import json
        from typer.testing import CliRunner
        from analyzer.cli import app
        result = CliRunner().invoke(app, ["analyze", str(bill_csv), "--no-ai", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "analysis" in data
        assert "advice" in data
        assert data["analysis"]["currency"] == "USD"
        assert data["analysis"]["total_transactions"] == 7

    def test_analyze_risk_alerts_shown(self, bill_csv):
        from typer.testing import CliRunner
        from analyzer.cli import app
        result = CliRunner().invoke(app, ["analyze", str(bill_csv), "--no-ai"])
        assert result.exit_code == 0
        assert "RISK ALERTS" in result.output

    def test_file_not_found(self):
        from typer.testing import CliRunner
        from analyzer.cli import app
        result = CliRunner().invoke(app, ["analyze", "no_such_file.csv"])
        assert result.exit_code == 1
        assert "not found" in result.output
