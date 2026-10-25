
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from rules.services import get_applicable_rule

CENT = Decimal("0.01")


def money(value):
    """Convert a value to a two-decimal monetary amount."""
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def calculate_payroll(gross_pay, deductions):
    """Calculate net pay using validated monetary values."""
    gross = money(gross_pay)
    deduction_amount = money(deductions)

    if gross < Decimal("0.00"):
        raise ValueError("Gross pay cannot be negative.")

    if deduction_amount < Decimal("0.00"):
        raise ValueError("Deductions cannot be negative.")

    if deduction_amount > gross:
        raise ValueError("Deductions cannot exceed gross pay.")

    net = money(gross - deduction_amount)

    return {
        "gross_pay": gross,
        "deductions": deduction_amount,
        "net_pay": net,
    }

def calculate_rule_based_deduction(gross_pay, effective_date: date):
    """Calculate a demo deduction using the applicable stored rule."""
    gross = money(gross_pay)

    if gross < Decimal("0.00"):
        raise ValueError("Gross pay cannot be negative.")

    rule = get_applicable_rule(
        "STANDARD_DEDUCTION",
        effective_date,
    )

    rate = Decimal(rule.configuration["rate"])

    if rate < Decimal("0.00") or rate > Decimal("1.00"):
        raise ValueError("Rule rate must be between 0 and 1.")

    deduction = money(gross * rate)

    return {
        "rule_name": rule.name,
        "rule_version": rule.version,
        "gross_pay": gross,
        "rate": str(rate),
        "deduction": deduction,
    }

def calculate_payroll_from_rules(gross_pay, effective_date: date):
    """Calculate payroll using the configured deduction rule."""
    deduction_result = calculate_rule_based_deduction(
        gross_pay,
        effective_date,
    )

    payroll_result = calculate_payroll(
        deduction_result["gross_pay"],
        deduction_result["deduction"],
    )

    return {
        **payroll_result,
        "rule_name": deduction_result["rule_name"],
        "rule_version": deduction_result["rule_version"],
        "rate": deduction_result["rate"],
    }
