
from datetime import date

from django.db.models import Q

from .models import FinancialRule


def get_applicable_rule(name: str, effective_date: date):
    """
    Return the highest-version active rule applicable
    on the requested date.
    """
    rule = (
        FinancialRule.objects.filter(
            name=name,
            is_active=True,
            effective_from__lte=effective_date,
        )
        .filter(
            Q(effective_to__isnull=True)
            | Q(effective_to__gte=effective_date)
        )
        .order_by("-version")
        .first()
    )

    if rule is None:
        raise FinancialRule.DoesNotExist(
            f"No applicable rule '{name}' for {effective_date}."
        )

    return rule
