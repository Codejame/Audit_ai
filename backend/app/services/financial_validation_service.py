"""Financial calculation validation engine implementing domain checks with numerical tolerance."""
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.extraction import ValidationCheck, ValidationResult
from backend.app.utils.helpers import parse_financial_number, numbers_approx_equal

class FinancialValidationService:
    def __init__(self, tolerance: float = None):
        self.tolerance = tolerance if tolerance is not None else settings.FINANCIAL_TOLERANCE

    def validate(self, document_type: str, extracted_data: Dict[str, Any]) -> ValidationResult:
        """
        Dispatches validation based on document_type.
        Returns a ValidationResult object containing list of checks and overall status.
        """
        logger.info(f"Running financial validations for document_type: {document_type}")
        checks: List[ValidationCheck] = []

        if document_type == "invoice":
            checks = self._validate_invoice(extracted_data)
        elif document_type == "balance_sheet":
            checks = self._validate_balance_sheet(extracted_data)
        elif document_type == "profit_and_loss":
            checks = self._validate_profit_and_loss(extracted_data)
        elif document_type == "cash_flow_statement":
            checks = self._validate_cash_flow(extracted_data)
        else:
            logger.warning(f"Unknown document type for validation: {document_type}")

        # Determine overall status and collect issues
        issues: List[str] = []
        has_failure = False

        for c in checks:
            if c.status == "FAIL":
                has_failure = True
                issues.append(
                    f"Check '{c.name}' failed: calculated {c.calculated_value} vs reported {c.reported_value} (variance: {c.variance})"
                )

        overall_status = "FAIL" if has_failure else "PASS"
        return ValidationResult(
            checks=checks,
            overall_status=overall_status,
            issues=issues
        )

    # -------------------------------------------------------------------------
    # 1. INVOICE VALIDATIONS
    # -------------------------------------------------------------------------
    def _validate_invoice(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []

        subtotal = self._extract_num(data, "subtotal")
        tax_amount = self._extract_num(data, "tax_amount")
        discount = self._extract_num(data, "discount") or 0.0
        total_amount = self._extract_num(data, "total_amount")
        cash_paid = self._extract_num(data, "cash_paid")
        change = self._extract_num(data, "change")
        line_items = data.get("line_items", [])

        # Check A: Line Items (Quantity * Unit Price ≈ Line Total)
        if line_items and isinstance(line_items, list):
            line_sum = 0.0
            valid_items_count = 0
            for idx, item in enumerate(line_items):
                qty = parse_financial_number(item.get("quantity"))
                price = parse_financial_number(item.get("unit_price"))
                line_total = parse_financial_number(item.get("amount") or item.get("total"))
                
                if qty is not None and price is not None:
                    calc_line = round(qty * price, 2)
                    if line_total is not None:
                        is_match, variance = numbers_approx_equal(calc_line, line_total, self.tolerance)
                        checks.append(ValidationCheck(
                            name=f"line_item_{idx+1}_check",
                            formula="quantity * unit_price",
                            operands={"quantity": qty, "unit_price": price},
                            calculated_value=calc_line,
                            reported_value=line_total,
                            variance=variance,
                            status="PASS" if is_match else "FAIL"
                        ))
                    if line_total is not None:
                        line_sum += line_total
                        valid_items_count += 1
                elif line_total is not None:
                    line_sum += line_total
                    valid_items_count += 1

            # Check B: Sum of line items ≈ Subtotal (or Total if no subtotal)
            target_reported = subtotal if subtotal is not None else total_amount
            if valid_items_count > 0 and target_reported is not None:
                calc_sum = round(line_sum, 2)
                is_match, variance = numbers_approx_equal(calc_sum, target_reported, self.tolerance)
                checks.append(ValidationCheck(
                    name="line_items_sum_check",
                    formula="sum(line_items.amount)",
                    operands={"sum_line_items": calc_sum},
                    calculated_value=calc_sum,
                    reported_value=target_reported,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

        # Check C: Invoice Total Check (Subtotal + Tax - Discount ≈ Total)
        if subtotal is not None and total_amount is not None:
            tax = tax_amount if tax_amount is not None else 0.0
            calc_total = round(subtotal + tax - discount, 2)
            is_match, variance = numbers_approx_equal(calc_total, total_amount, self.tolerance)
            checks.append(ValidationCheck(
                name="invoice_total_check",
                formula="subtotal + tax_amount - discount",
                operands={"subtotal": subtotal, "tax_amount": tax, "discount": discount},
                calculated_value=calc_total,
                reported_value=total_amount,
                variance=variance,
                status="PASS" if is_match else "FAIL"
            ))
        else:
            checks.append(ValidationCheck(
                name="invoice_total_check",
                formula="subtotal + tax_amount - discount",
                operands={"subtotal": subtotal, "tax_amount": tax_amount, "discount": discount},
                calculated_value=None,
                reported_value=total_amount,
                variance=None,
                status="NOT_APPLICABLE"
            ))

        # Check D: Cash Paid - Total Amount ≈ Change (if present)
        if cash_paid is not None and total_amount is not None and change is not None:
            calc_change = round(cash_paid - total_amount, 2)
            is_match, variance = numbers_approx_equal(calc_change, change, self.tolerance)
            checks.append(ValidationCheck(
                name="cash_change_check",
                formula="cash_paid - total_amount",
                operands={"cash_paid": cash_paid, "total_amount": total_amount},
                calculated_value=calc_change,
                reported_value=change,
                variance=variance,
                status="PASS" if is_match else "FAIL"
            ))

        return checks

    # -------------------------------------------------------------------------
    # 2. BALANCE SHEET VALIDATIONS
    # -------------------------------------------------------------------------
    def _validate_balance_sheet(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = self._get_periods(data)

        for period in periods:
            suffix = f" ({period})" if period else ""
            total_assets = self._extract_period_num(data, "total_assets", period)
            total_liabilities = self._extract_period_num(data, "total_liabilities", period)
            total_equity = self._extract_period_num(data, "total_equity", period)
            total_capital_liabilities = self._extract_period_num(data, "total_capital_and_liabilities", period)

            # Rule 1: Total Capital & Liabilities ≈ Total Assets
            if total_capital_liabilities is not None and total_assets is not None:
                is_match, variance = numbers_approx_equal(total_capital_liabilities, total_assets, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"balance_sheet_equality_check{suffix}",
                    formula="total_capital_and_liabilities ≈ total_assets",
                    operands={"total_capital_and_liabilities": total_capital_liabilities},
                    calculated_value=total_capital_liabilities,
                    reported_value=total_assets,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))
            elif total_liabilities is not None and total_equity is not None and total_assets is not None:
                calc_total = round(total_liabilities + total_equity, 2)
                is_match, variance = numbers_approx_equal(calc_total, total_assets, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"balance_sheet_equity_liabilities_check{suffix}",
                    formula="total_liabilities + total_equity",
                    operands={"total_liabilities": total_liabilities, "total_equity": total_equity},
                    calculated_value=calc_total,
                    reported_value=total_assets,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"balance_sheet_equality_check{suffix}",
                    formula="total_capital_and_liabilities ≈ total_assets",
                    operands={"total_capital_and_liabilities": total_capital_liabilities, "total_assets": total_assets},
                    calculated_value=total_capital_liabilities,
                    reported_value=total_assets,
                    variance=None,
                    status="NOT_APPLICABLE"
                ))

            # Rule 2: Detailed Assets Sum check if components available
            asset_components = [
                self._extract_period_num(data, "cash_and_rbi_balances", period),
                self._extract_period_num(data, "bank_balances_and_call_money", period),
                self._extract_period_num(data, "investments", period),
                self._extract_period_num(data, "advances", period),
                self._extract_period_num(data, "fixed_assets", period),
                self._extract_period_num(data, "other_assets", period)
            ]
            valid_assets = [a for a in asset_components if a is not None]
            if len(valid_assets) >= 3 and total_assets is not None:
                calc_assets = round(sum(valid_assets), 2)
                is_match, variance = numbers_approx_equal(calc_assets, total_assets, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"assets_breakdown_check{suffix}",
                    formula="sum(asset_components)",
                    operands={"components_sum": calc_assets},
                    calculated_value=calc_assets,
                    reported_value=total_assets,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

            # Rule 3: Detailed Liabilities Sum check if components available
            liab_components = [
                self._extract_period_num(data, "capital", period),
                self._extract_period_num(data, "reserves_and_surplus", period),
                self._extract_period_num(data, "minority_interest", period),
                self._extract_period_num(data, "deposits", period),
                self._extract_period_num(data, "borrowings", period),
                self._extract_period_num(data, "other_liabilities_and_provisions", period)
            ]
            valid_liab = [l for l in liab_components if l is not None]
            target_liab = total_capital_liabilities or total_assets
            if len(valid_liab) >= 3 and target_liab is not None:
                calc_liab = round(sum(valid_liab), 2)
                is_match, variance = numbers_approx_equal(calc_liab, target_liab, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"capital_liabilities_breakdown_check{suffix}",
                    formula="sum(capital_and_liability_components)",
                    operands={"components_sum": calc_liab},
                    calculated_value=calc_liab,
                    reported_value=target_liab,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

        return checks

    # -------------------------------------------------------------------------
    # 3. PROFIT & LOSS VALIDATIONS
    # -------------------------------------------------------------------------
    def _validate_profit_and_loss(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = self._get_periods(data)

        for period in periods:
            suffix = f" ({period})" if period else ""
            
            interest_earned = self._extract_period_num(data, "interest_earned", period)
            other_income = self._extract_period_num(data, "other_income", period)
            total_income = self._extract_period_num(data, "total_income", period) or self._extract_period_num(data, "revenue", period)

            # Check 1: Interest Earned + Other Income ≈ Total Income
            if interest_earned is not None and other_income is not None and total_income is not None:
                calc_inc = round(interest_earned + other_income, 2)
                is_match, variance = numbers_approx_equal(calc_inc, total_income, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"total_income_reconciliation{suffix}",
                    formula="interest_earned + other_income",
                    operands={"interest_earned": interest_earned, "other_income": other_income},
                    calculated_value=calc_inc,
                    reported_value=total_income,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

            # Check 2: Interest Expended + Operating Expenses + Provisions ≈ Total Expenditure
            interest_expended = self._extract_period_num(data, "interest_expended", period)
            operating_expenses = self._extract_period_num(data, "operating_expenses", period)
            provisions = self._extract_period_num(data, "provisions_and_contingencies", period)
            total_expenditure = self._extract_period_num(data, "total_expenditure", period)

            if interest_expended is not None and operating_expenses is not None and total_expenditure is not None:
                prov = provisions if provisions is not None else 0.0
                calc_exp = round(interest_expended + operating_expenses + prov, 2)
                is_match, variance = numbers_approx_equal(calc_exp, total_expenditure, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"total_expenditure_reconciliation{suffix}",
                    formula="interest_expended + operating_expenses + provisions",
                    operands={"interest_expended": interest_expended, "operating_expenses": operating_expenses, "provisions": prov},
                    calculated_value=calc_exp,
                    reported_value=total_expenditure,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

            # Check 3: Total Income - Total Expenditure ≈ Net Profit before Minority Interest
            net_profit_before_mi = (
                self._extract_period_num(data, "net_profit_for_the_year", period) or
                self._extract_period_num(data, "operating_profit", period) or
                self._extract_period_num(data, "net_profit", period)
            )
            if total_income is not None and total_expenditure is not None and net_profit_before_mi is not None:
                calc_profit = round(total_income - total_expenditure, 2)
                is_match, variance = numbers_approx_equal(calc_profit, net_profit_before_mi, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"net_profit_before_minority_interest_check{suffix}",
                    formula="total_income - total_expenditure",
                    operands={"total_income": total_income, "total_expenditure": total_expenditure},
                    calculated_value=calc_profit,
                    reported_value=net_profit_before_mi,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

            # Check 4: Profit before MI - Minority Interest (+ Associates) ≈ Consolidated Net Profit
            minority_interest = self._extract_period_num(data, "minority_interest", period)
            share_associates = self._extract_period_num(data, "share_in_profits_of_associates", period) or 0.0
            consolidated_net_profit = self._extract_period_num(data, "consolidated_net_profit", period)

            if net_profit_before_mi is not None and minority_interest is not None and consolidated_net_profit is not None:
                calc_group_profit = round(net_profit_before_mi - minority_interest + share_associates, 2)
                is_match, variance = numbers_approx_equal(calc_group_profit, consolidated_net_profit, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"consolidated_net_profit_check{suffix}",
                    formula="profit_before_minority_interest - minority_interest + share_of_associates",
                    operands={"profit_before_minority_interest": net_profit_before_mi, "minority_interest": minority_interest, "share_of_associates": share_associates},
                    calculated_value=calc_group_profit,
                    reported_value=consolidated_net_profit,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

            # Check 5: Current Profit + Brought Forward Profit (+ Amalgamation) ≈ Total Available for Appropriation
            brought_forward = self._extract_period_num(data, "brought_forward_profit", period)
            total_appropriations = self._extract_period_num(data, "total_appropriations", period)
            amalgamation_profit = (
                self._extract_period_num(data, "profit_on_amalgamation", period) or
                self._extract_period_num(data, "brought_forward_on_amalgamation", period) or 0.0
            )
            profit_basis = consolidated_net_profit or net_profit_before_mi
            if profit_basis is not None and brought_forward is not None and total_appropriations is not None:
                calc_approp = round(profit_basis + brought_forward + amalgamation_profit, 2)
                is_match, variance = numbers_approx_equal(calc_approp, total_appropriations, self.tolerance)
                operands_dict = {"current_profit": profit_basis, "brought_forward_profit": brought_forward}
                if amalgamation_profit != 0:
                    operands_dict["amalgamation_profit"] = amalgamation_profit
                checks.append(ValidationCheck(
                    name=f"appropriation_total_check{suffix}",
                    formula="current_profit + brought_forward_profit" + (" + amalgamation_profit" if amalgamation_profit else ""),
                    operands=operands_dict,
                    calculated_value=calc_approp,
                    reported_value=total_appropriations,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))

        return checks

    # -------------------------------------------------------------------------
    # 4. CASH FLOW STATEMENT VALIDATIONS
    # -------------------------------------------------------------------------
    def _validate_cash_flow(self, data: Dict[str, Any]) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        periods = self._get_periods(data)

        for period in periods:
            suffix = f" ({period})" if period else ""

            operating = self._extract_period_num(data, "operating_cash_flow", period)
            investing = self._extract_period_num(data, "investing_cash_flow", period)
            financing = self._extract_period_num(data, "financing_cash_flow", period)
            fx_adj = self._extract_period_num(data, "fx_translation_adjustment", period) or 0.0
            amalgamation = self._extract_period_num(data, "cash_on_amalgamation", period) or 0.0
            net_increase = self._extract_period_num(data, "net_change_in_cash", period) or self._extract_period_num(data, "net_increase_in_cash", period)

            # Check 1: Operating + Investing + Financing + FX + Amalgamation ≈ Net Increase in Cash
            if operating is not None and investing is not None and financing is not None and net_increase is not None:
                calc_increase = round(operating + investing + financing + fx_adj + amalgamation, 2)
                is_match, variance = numbers_approx_equal(calc_increase, net_increase, self.tolerance)
                operands_dict = {"operating": operating, "investing": investing, "financing": financing, "fx": fx_adj}
                if amalgamation != 0:
                    operands_dict["amalgamation"] = amalgamation
                formula_str = "operating + investing + financing + fx" + (" + amalgamation" if amalgamation else "")
                checks.append(ValidationCheck(
                    name=f"net_cash_flow_sum_check{suffix}",
                    formula=formula_str,
                    operands=operands_dict,
                    calculated_value=calc_increase,
                    reported_value=net_increase,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"net_cash_flow_sum_check{suffix}",
                    formula="operating + investing + financing + fx",
                    operands={"operating": operating, "investing": investing, "financing": financing},
                    calculated_value=None,
                    reported_value=net_increase,
                    variance=None,
                    status="NOT_APPLICABLE"
                ))

            # Check 2: Opening Cash + Net Increase ≈ Closing Cash
            opening_cash = self._extract_period_num(data, "opening_cash", period)
            closing_cash = self._extract_period_num(data, "closing_cash", period)

            if opening_cash is not None and net_increase is not None and closing_cash is not None:
                calc_closing = round(opening_cash + net_increase, 2)
                # In rare cases where amalgamation was not part of net_increase:
                if not numbers_approx_equal(calc_closing, closing_cash, self.tolerance)[0] and amalgamation:
                    if numbers_approx_equal(round(calc_closing + amalgamation, 2), closing_cash, self.tolerance)[0]:
                        calc_closing = round(calc_closing + amalgamation, 2)

                is_match, variance = numbers_approx_equal(calc_closing, closing_cash, self.tolerance)
                checks.append(ValidationCheck(
                    name=f"cash_reconciliation_check{suffix}",
                    formula="opening_cash + net_increase_in_cash",
                    operands={"opening_cash": opening_cash, "net_increase": net_increase},
                    calculated_value=calc_closing,
                    reported_value=closing_cash,
                    variance=variance,
                    status="PASS" if is_match else "FAIL"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"cash_reconciliation_check{suffix}",
                    formula="opening_cash + net_increase + adjustments",
                    operands={"opening_cash": opening_cash, "net_increase": net_increase},
                    calculated_value=None,
                    reported_value=closing_cash,
                    variance=None,
                    status="NOT_APPLICABLE"
                ))

        return checks

    # -------------------------------------------------------------------------
    # HELPER PARSERS
    # -------------------------------------------------------------------------
    def _extract_num(self, data: Dict[str, Any], key: str) -> Optional[float]:
        """Extracts numerical value from flat or grounded dictionary."""
        val = data.get(key)
        if isinstance(val, dict):
            return parse_financial_number(val.get("value"))
        return parse_financial_number(val)

    def _extract_period_num(self, data: Dict[str, Any], key: str, period: Optional[str]) -> Optional[float]:
        """Extracts numerical value for a specific period or falls back to flat key."""
        if period and "comparative_periods" in data and period in data["comparative_periods"]:
            period_data = data["comparative_periods"][period]
            val = period_data.get(key)
            if isinstance(val, dict):
                return parse_financial_number(val.get("value"))
            return parse_financial_number(val)

        return self._extract_num(data, key)

    def _get_periods(self, data: Dict[str, Any]) -> List[Optional[str]]:
        """Finds distinct comparative periods if present (e.g. 31-Mar-17, 31-Mar-16)."""
        comparative = data.get("comparative_periods")
        if isinstance(comparative, dict) and comparative:
            return list(comparative.keys())
        return [None]
