
from django.db import models


class PayrollRecord(models.Model):
    employee_reference = models.CharField(max_length=100)
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()

    gross_pay = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    deductions = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    net_pay = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    rule_snapshot = models.JSONField(default=dict)
    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee_reference} - {self.net_pay}"

class PayrollAuditLog(models.Model):
    payroll_record = models.ForeignKey(
        PayrollRecord,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    event_type = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.event_type} - "
            f"Payroll record {self.payroll_record_id}"
        )
