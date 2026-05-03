from django.db import models
from core.models import BaseTenantModel
from .materials import Material
from django.contrib.auth import get_user_model

User = get_user_model()
class OreClass(BaseTenantModel):
    ore_class = models.CharField(max_length=20)
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    ni_min = models.FloatField(null=True, blank=True)
    ni_max = models.FloatField(null=True, blank=True)

    mgo_min = models.FloatField(null=True, blank=True)
    mgo_max = models.FloatField(null=True, blank=True)

    fe_min  = models.FloatField(null=True, blank=True)
    fe_max  = models.FloatField(null=True, blank=True)
    
    status = models.BooleanField(default=True)
    user   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "master_ore_classes"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "material", "ore_class"],
                name="uq_oreclass_per_iup_material"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["material"]),
            models.Index(fields=["ore_class"]),
        ]

    def __str__(self):
        return f"{self.iup.iup_code} - {self.material.name} - {self.ore_class}"
    