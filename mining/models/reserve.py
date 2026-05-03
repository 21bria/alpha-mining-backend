from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class MiningReserve(BaseTenantModel):
    ORE_TYPE_CHOICES = [
        ("ALL", "All Type"),
        ("LIM", "Limonite"),
        ("SAP", "Saprolite"),
    ]

    id_reserve = models.AutoField(primary_key=True)

    block_model = models.CharField(max_length=100, null=True, blank=True)
    pit_name    = models.CharField(max_length=100, null=True, blank=True)
    domain      = models.CharField(max_length=50, null=True, blank=True)

    ore_type = models.CharField(max_length=20, choices=ORE_TYPE_CHOICES, default="ALL", null=True, blank=True)

    tonnage   = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    ni_grade  = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    fe_grade  = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    co_grade  = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    mgo_grade = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    sio2_grade= models.DecimalField(max_digits=6, decimal_places=3, default=0)

    strip_ratio  = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    cutoff_grade = models.DecimalField(max_digits=6, decimal_places=3, default=1)

    date_estimated = models.DateField()
    estimated_by   = models.CharField(max_length=100)
    description    = models.TextField(null=True, blank=True)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


    class Meta:
        db_table = "mining_reserve"
        ordering = ["-date_estimated"]
        indexes = [
            models.Index(fields=["iup", "date_estimated"]),
            models.Index(fields=["iup", "pit_name"]),
        ]