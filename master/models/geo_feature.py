from django.db import models
from django.contrib.gis.db import models as geomodels
from django.contrib.postgres.indexes import GistIndex
from .feature_type import FeatureType
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class GeoFeature(BaseTenantModel):
    code_source_field = "name"

    feature_type = models.ForeignKey(
        FeatureType,
        on_delete=models.PROTECT,
        related_name="features"
    )

    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, null=True, blank=True)

    geometry = geomodels.GeometryField(srid=4326, null=True, blank=True)

    extra_properties = models.JSONField(null=True, blank=True)
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = "master_geo_features"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "feature_type", "name"],
                name="uq_feature_per_iup_type_name"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["feature_type"]),
            GistIndex(fields=["geometry"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.feature_type.code}) - {self.iup.iup_code}"