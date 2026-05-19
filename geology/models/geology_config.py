from django.db import models
from django.contrib.auth import get_user_model

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

   
