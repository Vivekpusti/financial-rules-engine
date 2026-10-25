
from datetime import date
from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status
from payroll.models import PayrollRecord
from django.test import SimpleTestCase, TestCase
from payroll.models import PayrollAuditLog, PayrollRecord

from rules.models import FinancialRule
from .services import (
    calculate_payroll,
    calculate_rule_based_deduction,
    money,
)


class PayrollCalculationTests(SimpleTestCase):

    def test_calculates_net_pay(self):
        result = calculate_payroll("5000.00", "750.00")

        self.assertEqual(result["gross_pay"], Decimal("5000.00"))
        self.assertEqual(result["deductions"], Decimal("750.00"))
        self.assertEqual(result["net_pay"], Decimal("4250.00"))

    def test_rounds_money_to_two_decimal_places(self):
        self.assertEqual(money("100.125"), Decimal("100.13"))

    def test_rejects_negative_gross_pay(self):
        with self.assertRaises(ValueError):
            calculate_payroll("-100.00", "0.00")

    def test_rejects_negative_deductions(self):
        with self.assertRaises(ValueError):
            calculate_payroll("100.00", "-10.00")

    def test_rejects_deductions_greater_than_gross_pay(self):
        with self.assertRaises(ValueError):
            calculate_payroll("100.00", "150.00")

    def test_zero_pay(self):
        result = calculate_payroll("0.00", "0.00")

        self.assertEqual(result["net_pay"], Decimal("0.00"))


class RuleBasedDeductionTests(TestCase):

    def setUp(self):
        self.rule = FinancialRule.objects.create(
            name="STANDARD_DEDUCTION",
            version=1,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            configuration={
                "rate": "0.10",
                "description": "Demo deduction rate of 10 percent",
            },
            is_active=True,
        )

    def test_uses_configured_rule_rate(self):
        result = calculate_rule_based_deduction(
            "5000.00",
            date(2026, 10, 25),
        )

        self.assertEqual(result["rule_name"], self.rule.name)
        self.assertEqual(result["rule_version"], 1)
        self.assertEqual(result["gross_pay"], Decimal("5000.00"))
        self.assertEqual(result["rate"], "0.10")
        self.assertEqual(result["deduction"], Decimal("500.00"))

    def test_rejects_negative_gross_pay(self):
        with self.assertRaises(ValueError):
            calculate_rule_based_deduction(
                "-100.00",
                date(2026, 10, 25),
            )

    def test_fails_when_no_applicable_rule_exists(self):
        with self.assertRaises(FinancialRule.DoesNotExist):
            calculate_rule_based_deduction(
                "5000.00",
                date(2025, 1, 1),
            )

    def test_selects_rule_version_effective_on_date(self):
        FinancialRule.objects.create(
            name="STANDARD_DEDUCTION",
            version=2,
            effective_from=date(2026, 7, 1),
            effective_to=None,
            configuration={"rate": "0.15"},
            is_active=True,
        )

        result = calculate_rule_based_deduction(
            "5000.00",
            date(2026, 10, 25),
        )

        self.assertEqual(result["rule_version"], 2)
        self.assertEqual(result["rate"], "0.15")
        self.assertEqual(result["deduction"], Decimal("750.00"))

    def test_old_rule_applies_before_new_version_starts(self):
        FinancialRule.objects.create(
            name="STANDARD_DEDUCTION",
            version=2,
            effective_from=date(2026, 7, 1),
            effective_to=None,
            configuration={"rate": "0.15"},
            is_active=True,
        )

        result = calculate_rule_based_deduction(
            "5000.00",
            date(2026, 3, 1),
        )

        self.assertEqual(result["rule_version"], 1)
        self.assertEqual(result["rate"], "0.10")
        self.assertEqual(result["deduction"], Decimal("500.00"))

class PayrollAPITests(APITestCase):


    def test_creates_audit_log_for_new_payroll(self):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="audit-test-001",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PayrollRecord.objects.count(), 1)
        self.assertEqual(PayrollAuditLog.objects.count(), 1)

        audit = PayrollAuditLog.objects.get()
        self.assertEqual(audit.event_type, "CALCULATION_CREATED")
        self.assertEqual(
            audit.details["rule_name"],
            "STANDARD_DEDUCTION",
        )
        self.assertEqual(audit.details["rule_version"], 1)
        self.assertEqual(audit.details["gross_pay"], "5000.00")
        self.assertEqual(audit.details["deductions"], "500.00")
        self.assertEqual(audit.details["net_pay"], "4500.00")

    def test_retry_does_not_create_duplicate_audit_log(self):
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "audit-retry-001",
        }

        first = self.client.post(
            self.url,
            self.payload,
            format="json",
            **headers,
        )
        second = self.client.post(
            self.url,
            self.payload,
            format="json",
            **headers,
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(PayrollRecord.objects.count(), 1)
        self.assertEqual(PayrollAuditLog.objects.count(), 1)

    def test_conflicting_retry_does_not_create_audit_log(self):
        headers = {
            "HTTP_IDEMPOTENCY_KEY": "audit-conflict-001",
        }

        self.client.post(
            self.url,
            self.payload,
            format="json",
            **headers,
        )

        changed_payload = {
            **self.payload,
            "gross_pay": "7000.00",
        }

        response = self.client.post(
            self.url,
            changed_payload,
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(PayrollRecord.objects.count(), 1)
        self.assertEqual(PayrollAuditLog.objects.count(), 1)


    def setUp(self):
        FinancialRule.objects.create(
            name="STANDARD_DEDUCTION",
            version=1,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            configuration={"rate": "0.10"},
            is_active=True,
        )

        self.url = "/api/payroll/calculate/"
        self.payload = {
            "employee_reference": "EMP-API-001",
            "pay_period_start": "2026-10-01",
            "pay_period_end": "2026-10-31",
            "gross_pay": "5000.00",
        }

    def test_calculates_and_saves_payroll(self):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="api-test-key-001",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["gross_pay"], "5000.00")
        self.assertEqual(response.data["deductions"], "500.00")
        self.assertEqual(response.data["net_pay"], "4500.00")
        self.assertEqual(
            response.data["rule_snapshot"]["rule_version"], 1
        )
        self.assertEqual(PayrollRecord.objects.count(), 1)

    def test_rejects_missing_idempotency_key(self):
        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PayrollRecord.objects.count(), 0)

    def test_reuses_record_for_identical_retry(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "api-test-retry-001"}

        first = self.client.post(
            self.url, self.payload, format="json", **headers
        )
        second = self.client.post(
            self.url, self.payload, format="json", **headers
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(PayrollRecord.objects.count(), 1)

    def test_rejects_same_key_with_different_payload(self):
        headers = {"HTTP_IDEMPOTENCY_KEY": "api-test-conflict-001"}

        self.client.post(
            self.url, self.payload, format="json", **headers
        )

        changed_payload = {**self.payload, "gross_pay": "7000.00"}
        response = self.client.post(
            self.url, changed_payload, format="json", **headers
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(PayrollRecord.objects.count(), 1)

    def test_rejects_invalid_pay_period(self):
        payload = {
            **self.payload,
            "pay_period_start": "2026-11-01",
            "pay_period_end": "2026-10-01",
        }

        response = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="api-test-invalid-001",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PayrollRecord.objects.count(), 0)
