
from rest_framework import serializers


class PayrollCalculationSerializer(serializers.Serializer):
    employee_reference = serializers.CharField(max_length=100)
    pay_period_start = serializers.DateField()
    pay_period_end = serializers.DateField()

    gross_pay = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
    )

    def validate(self, attrs):
        if attrs["pay_period_end"] < attrs["pay_period_start"]:
            raise serializers.ValidationError({
                "pay_period_end": (
                    "Pay period end must be on or after the start date."
                )
            })

        return attrs
