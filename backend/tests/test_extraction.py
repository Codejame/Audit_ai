"""Automated tests for financial validation rules, bracketed negatives, and missing field handling."""
import pytest
from backend.app.services.financial_validation_service import FinancialValidationService
from backend.app.utils.helpers import parse_financial_number

def test_negative_bracket_parsing():
    """Verify accounting bracketed numbers are correctly parsed as negative floats."""
    assert parse_financial_number("(1,018,904,990)") == -1018904990.0
    assert parse_financial_number("(282,622)") == -282622.0
    assert parse_financial_number("12,500.00") == 12500.0
    assert parse_financial_number("-500.50") == -500.50
    assert parse_financial_number("-") == 0.0
    assert parse_financial_number(None) is None

def test_invoice_validation_success():
    """Verify correct invoice calculation passes validation."""
    service = FinancialValidationService(tolerance=1.0)
    data = {
        "subtotal": {"value": 12500.00},
        "tax_amount": {"value": 625.00},
        "discount": {"value": 0.00},
        "total_amount": {"value": 13125.00},
        "line_items": [
            {"description": "Service A", "quantity": 1, "unit_price": 12500.00, "amount": 12500.00}
        ]
    }
    result = service.validate("invoice", data)
    assert result.overall_status == "PASS"
    assert len(result.issues) == 0
    checks = {c.name: c.status for c in result.checks}
    assert checks.get("invoice_total_check") == "PASS"
    assert checks.get("line_items_sum_check") == "PASS"

def test_invoice_validation_failure_scenario():
    """Verify mismatched invoice calculation triggers FAIL and records variance."""
    service = FinancialValidationService(tolerance=1.0)
    # Incorrect total: reported 15000 instead of 13125
    data = {
        "subtotal": 12500.00,
        "tax_amount": 625.00,
        "discount": 0.00,
        "total_amount": 15000.00
    }
    result = service.validate("invoice", data)
    assert result.overall_status == "FAIL"
    assert len(result.issues) > 0
    total_check = next(c for c in result.checks if c.name == "invoice_total_check")
    assert total_check.status == "FAIL"
    assert total_check.variance == 1875.00

def test_balance_sheet_validation():
    """Verify Balance Sheet Assets == Liabilities + Equity check."""
    service = FinancialValidationService(tolerance=1.0)
    data = {
        "total_capital_and_liabilities": 8923441607.0,
        "total_assets": 8923441607.0
    }
    result = service.validate("balance_sheet", data)
    assert result.overall_status == "PASS"
    eq_check = result.checks[0]
    assert eq_check.status == "PASS"
    assert eq_check.variance == 0.0

def test_profit_and_loss_validation():
    """Verify P&L income and expenditure reconciliations."""
    service = FinancialValidationService(tolerance=1.0)
    data = {
        "interest_earned": 732713529.0,
        "other_income": 128776329.0,
        "total_income": 861489858.0,
        "interest_expended": 380415844.0,
        "operating_expenses": 207510707.0,
        "provisions_and_contingencies": 120689285.0,
        "total_expenditure": 708615836.0,
        "net_profit_for_the_year": 152874022.0
    }
    result = service.validate("profit_and_loss", data)
    assert result.overall_status == "PASS"
    for c in result.checks:
        assert c.status == "PASS"

def test_cash_flow_validation_with_negatives():
    """Verify Cash Flow summation and negative accounting adjustments."""
    service = FinancialValidationService(tolerance=1.0)
    data = {
        "operating_cash_flow": 172815931.0,
        "investing_cash_flow": -11476802.0,
        "financing_cash_flow": -58929743.0,
        "fx_translation_adjustment": -282622.0,
        "net_increase_in_cash": 102126764.0,
        "opening_cash": 390688815.0,
        "closing_cash": 492815579.0
    }
    result = service.validate("cash_flow_statement", data)
    assert result.overall_status == "PASS"

def test_missing_fields_return_not_applicable():
    """Verify missing required fields return NOT_APPLICABLE rather than inventing values."""
    service = FinancialValidationService()
    # Incomplete cash flow statement
    data = {
        "operating_cash_flow": 1000.0
    }
    result = service.validate("cash_flow_statement", data)
    for c in result.checks:
        assert c.status == "NOT_APPLICABLE"
