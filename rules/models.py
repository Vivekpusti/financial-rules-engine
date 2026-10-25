
from django.db import models


class FinancialRule(models.Model):
    name = models.CharField(max_length=100)
    version = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="unique_financial_rule_version",
            ),
        ]
        ordering = ["name", "-version"]

    def __str__(self):
        return f"{self.name} v{self.version}"
