
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import PayrollRecord, PayrollAuditLog
from .serializers import PayrollCalculationSerializer
from .services import calculate_payroll_from_rules


@api_view(["POST"])
def calculate_payroll_view(request):
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        return Response(
            {"detail": "Idempotency-Key header is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PayrollCalculationSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    try:
        result = calculate_payroll_from_rules(
            data["gross_pay"],
            data["pay_period_end"],
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        # A missing applicable rule should be reported clearly.
        from rules.models import FinancialRule

        if isinstance(exc, FinancialRule.DoesNotExist):
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raise

    with transaction.atomic():
        record = PayrollRecord.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if record:
            same_request = (
                record.employee_reference == data["employee_reference"]
                and record.pay_period_start == data["pay_period_start"]
                and record.pay_period_end == data["pay_period_end"]
                and record.gross_pay == result["gross_pay"]
                and record.deductions == result["deductions"]
            )

            if not same_request:
                return Response(
                    {
                        "detail": (
                            "Idempotency key was already used "
                            "with different request data."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            created = False

        else:
            record = PayrollRecord.objects.create(
                employee_reference=data["employee_reference"],
                pay_period_start=data["pay_period_start"],
                pay_period_end=data["pay_period_end"],
                gross_pay=result["gross_pay"],
                deductions=result["deductions"],
                net_pay=result["net_pay"],
                rule_snapshot={
                    "rule_name": result["rule_name"],
                    "rule_version": result["rule_version"],
                    "rate": result["rate"],
                },
                idempotency_key=idempotency_key,
            )

            PayrollAuditLog.objects.create(
                payroll_record=record,
                event_type="CALCULATION_CREATED",
                details={
                    "rule_name": result["rule_name"],
                    "rule_version": result["rule_version"],
                    "gross_pay": str(result["gross_pay"]),
                    "deductions": str(result["deductions"]),
                    "net_pay": str(result["net_pay"]),
                },
            )

            created = True


    return Response(
        {
            "id": record.id,
            "employee_reference": record.employee_reference,
            "pay_period_start": record.pay_period_start,
            "pay_period_end": record.pay_period_end,
            "gross_pay": str(record.gross_pay),
            "deductions": str(record.deductions),
            "net_pay": str(record.net_pay),
            "rule_snapshot": record.rule_snapshot,
            "created_at": record.created_at,
        },
        status=(
            status.HTTP_201_CREATED
            if created
            else status.HTTP_200_OK
        ),
    )
