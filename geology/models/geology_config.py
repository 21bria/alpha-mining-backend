from django.db import models
from django.contrib.auth import get_user_model
from master.models import SampleType,Material

class ProductionsConfig(models.Model):
    key       = models.CharField(max_length=100, unique=True)
    value     = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "geology_productions_config"

        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["value"]),
        ]

   
class QualityConfig(models.Model):
    name = models.CharField(max_length=50)
    adjust_sale = models.CharField(max_length=50, unique=True)

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_configs"
    )

    selling_sample_type = models.ForeignKey(
        SampleType,
            on_delete=models.PROTECT,
            null=True,
            blank=True,
            related_name="quality_selling_configs",
        )

    monitoring_sample_type = models.ForeignKey(
        SampleType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quality_monitoring_configs",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "master_quality_config"
        indexes = [
            models.Index(fields=["adjust_sale"]),
            models.Index(fields=["is_active"]),
        ]