from django.db import models
from core.models import BaseTenantModel
from .materials import Material 
from django.contrib.auth import get_user_model

User = get_user_model()
class OreTruckFactor(BaseTenantModel):
    type_tf = models.CharField(max_length=150, null=True, blank=True)

    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    density  = models.FloatField(null=True, blank=True)
    bcm      = models.FloatField(null=True, blank=True)
    ton      = models.FloatField(null=True, blank=True)
    status   = models.IntegerField(null=True, blank=True)
    user     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = "master_ore_truck_factors"
        constraints = [
            # aman: reference_tf boleh sama antar IUP
            models.UniqueConstraint(
                fields=["iup", "type_tf","material"],
                name="uq_truck_factor_ref_per_iup"
            ),
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["type_tf"]),
            models.Index(fields=["material"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        prefix = self.iup.iup_code if self.iup else "NO-IUP"
        return f"{prefix} - {self.type_tf}"