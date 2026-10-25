
from django.urls import path

from .views import calculate_payroll_view


urlpatterns = [
    path(
        "calculate/",
        calculate_payroll_view,
        name="calculate-payroll",
    ),
]
