from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class mineProductions(BaseTenantModel):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_production = models.DateField(default=None, null=True, blank=True)
    vendors         = models.CharField(max_length=25, default=None, null=True, blank=True)
    shift           = models.CharField(max_length=10, default=None, null=True, blank=True)
    loader          = models.CharField(max_length=25, default=None, null=True, blank=True)
    hauler          = models.CharField(max_length=25, default=None, null=True, blank=True)
    hauler_class    = models.CharField(max_length=25, default=None, null=True, blank=True)
    sources_area    = models.BigIntegerField(default=None, null=True, blank=True)
    loading_point   = models.BigIntegerField(default=None, null=True, blank=True)
    dumping_point   = models.BigIntegerField(default=None, null=True, blank=True)
    dome_id         = models.BigIntegerField(default=None, null=True, blank=True)
    distance        = models.CharField(max_length=250, default=None, null=True, blank=True)
    category_mine   = models.CharField(max_length=25, default=None, null=True, blank=True)
    time_dumping    = models.CharField(max_length=25,default=None, null=True, blank=True)
    time_loading    = models.TimeField(default=None, null=True, blank=True)
    left_loading    = models.CharField(max_length=2,default=None, null=True, blank=True)
    block_id        = models.CharField(max_length=250,default=None, null=True, blank=True)
    from_rl         = models.CharField(max_length=15, default=None, null=True, blank=True)
    to_rl           = models.CharField(max_length=15, default=None, null=True, blank=True)
    id_material     = models.IntegerField(default=None, null=True, blank=True)
    bucket          = models.IntegerField(default=0, null=True, blank=True)
    ritase          = models.IntegerField(default=None, null=True, blank=True)
    bcm             = models.FloatField(default=None, null=True, blank=True)
    tonnage         = models.FloatField(default=None, null=True, blank=True)
    remarks         = models.TextField(default=None, null=True, blank=True)
    hauler_type     = models.CharField(max_length=15, default=None, null=True, blank=True)
    ref_materials   = models.CharField(max_length=150, default=None, null=True, blank=True)
    no_production   = models.CharField(max_length=150, default=None, null=True, blank=True)
    task_id         = models.CharField(max_length=255, default=None, null=True, blank=True)
    direct          = models.CharField(max_length=15, default='No', null=True, blank=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table   = 'mining_productions'
        indexes = [
            models.Index(
                fields=[
                    'iup','date_production', 'hauler', 'time_loading',
                    'id_material', 'dome_id', 'sources_area',
                    'loading_point', 'dumping_point'
                ],
                name='idx_mine_productions'
            )
    ]


# Mine Productions Quick
class mineQuickProductions(BaseTenantModel):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_production = models.DateField(default=None, null=True, blank=True)
    vendors         = models.CharField(max_length=25, default=None, null=True, blank=True)
    shift           = models.CharField(max_length=10, default=None, null=True, blank=True)
    loader          = models.CharField(max_length=25, default=None, null=True, blank=True)
    hauler          = models.CharField(max_length=25, default=None, null=True, blank=True)
    hauler_class    = models.CharField(max_length=25, default=None, null=True, blank=True)
    sources         = models.IntegerField(default=None, null=True, blank=True)
    loading_point   = models.IntegerField(default=None, null=True, blank=True)
    dumping_point   = models.IntegerField(default=None, null=True, blank=True)
    dome_id         = models.IntegerField(default=None, null=True, blank=True)
    distance        = models.CharField(max_length=250, default=None, null=True, blank=True)
    category_mine   = models.CharField(max_length=25, default=None, null=True, blank=True)
    block_id        = models.BigIntegerField(default=None, null=True, blank=True)
    from_rl         = models.CharField(max_length=15, default=None, null=True, blank=True)
    to_rl           = models.CharField(max_length=15, default=None, null=True, blank=True)
    id_material     = models.IntegerField(default=None, null=True, blank=True)
    ritase          = models.IntegerField(default=None, null=True, blank=True)
    bcm             = models.FloatField(default=None, null=True, blank=True)
    tonnage         = models.FloatField(default=None, null=True, blank=True)
    time_loading    = models.CharField(max_length=2,default=None, null=True, blank=True)
    remarks         = models.TextField(default=None, null=True, blank=True)
    hauler_type     = models.CharField(max_length=15, default=None, null=True, blank=True)
    ref_materials   = models.CharField(max_length=150, default=None, null=True, blank=True)
    ref_plan_truck  = models.CharField(max_length=150, default=None, null=True, blank=True)
    task_id         = models.CharField(max_length=255, default=None, null=True, blank=True)
    no_production   = models.CharField(max_length=25, default=None, null=True, blank=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table   = 'mining_productions_quick'
