from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class PlanProduction(BaseTenantModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    date_plan = models.DateField( null=True,blank=True)
    category = models.CharField(max_length=25,null=True, blank=True)
    source_code = models.CharField(max_length=50,null=True,blank=True)
    vendor_code = models.CharField(max_length=50,null=True, blank=True)
    ref_plan = models.CharField( max_length=150,null=True, blank=True)
    task_id = models.CharField( max_length=255,null=True, blank=True)
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, blank=True)

    class Meta:
        db_table = "mining_plan_production"
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["date_plan"]),
            models.Index(fields=["category"]),
            models.Index(fields=["source_code"]),
            models.Index(fields=["vendor_code"]),
            models.Index(fields=["ref_plan"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "iup",
                    "date_plan",
                    "category",
                    "source_code",
                    "vendor_code",
                ],
                name="uq_plan_production_daily_source_vendor",
            )
        ]


class PlanProductionDetail(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    plan = models.ForeignKey(PlanProduction,related_name="details",on_delete=models.CASCADE)
    material_code = models.CharField( max_length=50 )
    material_name = models.CharField(max_length=100,null=True,blank=True)
    tonnage = models.FloatField(default=0)

    class Meta:
        db_table = "mining_plan_production_details"
        indexes = [
            models.Index(fields=["plan"]),
            models.Index(fields=["material_code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "plan",
                    "material_code",
                ],
                name="uq_plan_production_detail_material",
            )
        ]