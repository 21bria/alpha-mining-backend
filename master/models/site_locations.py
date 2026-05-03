from django.db import models
from django.contrib.gis.db import models as geomodels
from django.core.exceptions import ValidationError
from core.models import BaseTenantModel
from .location_types import LocationType
from django.contrib.auth import get_user_model

User = get_user_model()
class SiteLocation(BaseTenantModel):
    code_source_field = "name"
    name = models.CharField(max_length=150)
    location_type = models.ForeignKey(
        LocationType,
        on_delete=models.PROTECT,
        related_name="locations"
    )

    geometry = geomodels.GeometryField(srid=4326, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    extra_properties = models.JSONField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        if not self.geometry or not self.location_type:
            return

        geom_type = self.geometry.geom_type.upper()
        expected = self.location_type.geom_kind

        if expected == "POINT" and geom_type not in ["POINT", "MULTIPOINT"]:
            raise ValidationError("Geometry harus Point/MultiPoint")

        if expected == "LINE" and geom_type not in ["LINESTRING", "MULTILINESTRING"]:
            raise ValidationError("Geometry harus LineString/MultiLineString")

        if expected == "POLYGON" and geom_type not in ["POLYGON", "MULTIPOLYGON"]:
            raise ValidationError("Geometry harus Polygon/MultiPolygon")

    class Meta:
        db_table = "master_site_locations"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "location_type", "name"],
                name="uq_location_per_iup_type_name"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["location_type"]),
        ]