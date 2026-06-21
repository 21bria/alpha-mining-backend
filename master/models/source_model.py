from django.db import models
from django.contrib.gis.db import models as geomodels
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
# For Mines Sources (Pit/Area)
class SourceMines(BaseTenantModel):
    code_source_field = "sources_area"
    sources_area = models.CharField(max_length=50)
    description  = models.CharField(max_length=255, null=True, blank=True)
    latitude     = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude    = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    geometry     = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.sources_area} ({self.iup.iup_code if self.iup else '-'})"

    class Meta:
        db_table = "master_mine_sources"
        constraints = [
            models.UniqueConstraint(fields=["iup", "sources_area"], name="uq_sources_area_per_iup"),
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["sources_area"]),
            models.Index(fields=["code"]),
        ]

class SourceMinesLoading(BaseTenantModel):
    code_source_field = "loading_point"

    loading_point = models.CharField(max_length=50)
    description   = models.CharField(max_length=255, null=True, blank=True)
    category      = models.CharField(max_length=25, null=True, blank=True)

    source = models.ForeignKey(
        SourceMines,
        related_name="loading_points",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_sources",
    )

    status        = models.IntegerField(null=True, blank=True)
    latitude      = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude     = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    geometry      = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.loading_point} ({self.iup.iup_code if self.iup else '-'})"

    class Meta:
        db_table = "master_mine_sources_point_loading"
        constraints = [
            models.UniqueConstraint(fields=["iup", "loading_point"], name="uq_loading_point_per_iup"),
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["loading_point"]),
            models.Index(fields=["code"]),
        ]

class SourceMinesDumping(BaseTenantModel):
    code_source_field = "dumping_point"
    dumping_point = models.CharField(max_length=50)
    description   = models.CharField(max_length=255, null=True, blank=True)
    category      = models.CharField(max_length=25, null=True, blank=True)
    compositing   = models.CharField(max_length=5, null=True, blank=True)
    status        = models.IntegerField(null=True, blank=True)
    geometry      = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    latitude      = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude     = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.dumping_point} ({self.iup.iup_code if self.iup else '-'})"

    class Meta:
        db_table = "master_mine_sources_point_dumping"
        constraints = [
            models.UniqueConstraint(fields=["iup", "dumping_point"], name="uq_dumping_point_per_iup"),
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["dumping_point"]),
            models.Index(fields=["code"]),
        ]

class SourceMinesDome(BaseTenantModel):
    code_source_field = "pile_id"

    pile_id     = models.CharField(max_length=50)
    description = models.CharField(max_length=255, null=True, blank=True)
    category    = models.CharField(max_length=25, null=True, blank=True)
    compositing = models.CharField(max_length=15, null=True, blank=True)
    dome_finish = models.CharField(max_length=25, null=True, blank=True)
    status_dome = models.CharField(max_length=15, null=True, blank=True)
    plan_ni_min = models.FloatField(null=True, blank=True)
    plan_ni_max = models.FloatField(null=True, blank=True)
    status      = models.IntegerField(null=True, blank=True)
    direct_sale = models.CharField(max_length=10, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    dumping = models.ForeignKey(
        SourceMinesDumping,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domes",
        db_column="id_dumping",
    )

    latitude    = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude   = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    geometry    = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.pile_id} ({self.iup.iup_code if self.iup else '-'})"

    class Meta:
        db_table = "master_mine_sources_point_dome"
        constraints = [
            models.UniqueConstraint(fields=["iup", "pile_id"], name="uq_pile_id_per_iup"),
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["pile_id"]),
            models.Index(fields=["code"]),
        ]

class SourcePitDome(models.Model):
    DOME_TYPES = (
        ("TEMP", "Temporary"),
        ("SELECTIVE", "Selective"),
        ("ROM", "ROM"),
        ("STOCK", "Stock"),
    )

    dome_type = models.CharField(
        max_length=20,
        choices=DOME_TYPES,
        default="TEMP",
    )

    dome        = models.CharField(max_length=50)
    description = models.CharField(max_length=255, null=True, blank=True)
    compositing = models.CharField(max_length=15, null=True, blank=True)
    status_dome = models.CharField(max_length=15, null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    direct_sale = models.CharField(max_length=10, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    loading_point = models.ForeignKey(
        SourceMinesLoading,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="domes",
        db_column="id_loading",
    )

    latitude    = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude   = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    geometry    = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)  

    class Meta:
        db_table = "master_mine_sources_pit_dome"
        constraints = [
            models.UniqueConstraint(
                fields=["loading_point", "dome"],
                name="uq_loading_dome",
            )
        ]
        indexes = [
            models.Index(fields=["dome"]),
            models.Index(fields=["loading_point", "dome"]),
            models.Index(fields=["dome_type"]),
            models.Index(fields=["is_active"]),
        ]

class detailsDome(models.Model):
    pile_id       = models.CharField(max_length=50,default=None, null=True, blank=True)
    dumping_point = models.CharField(max_length=50,default=None, null=True, blank=True)
    description   = models.CharField(max_length=255, default=None, null=True, blank=True)
    category      = models.CharField(max_length=25, default=None, null=True, blank=True)
    compositing   = models.CharField(max_length=15, default=None, null=True, blank=True)
    dome_finish   = models.CharField(max_length=25, default=None, null=True, blank=True)
    status_dome   = models.CharField(max_length=15, default=None, null=True, blank=True)
    plan_ni_min   = models.FloatField(default=None, null=True, blank=True)
    plan_ni_max   = models.FloatField(default=None, null=True, blank=True)
    status        = models.IntegerField(default=None, null=True, blank=True)
    direct_sale   = models.CharField(max_length=10,default=None, null=True, blank=True)
    id_dumping    = models.BigIntegerField(default=None, null=True, blank=True)

    class Meta:
        managed   = False
        db_table  = 'view_master_dome_point_details'
    

