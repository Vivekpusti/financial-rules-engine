from django.contrib import admin
from .models import PayrollRecord, PayrollAuditLog


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "employee_reference",
        "gross_pay",
        "deductions",
        "net_pay",
        "created_at",
    )
    search_fields = ("employee_reference", "idempotency_key")


@admin.register(PayrollAuditLog)
class PayrollAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payroll_record",
        "event_type",
        "created_at",
    )
    list_filter = ("event_type",)