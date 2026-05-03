from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.auth import get_user_model
from django.db import models
from core.models import BaseTenantModel
from master.models import SourceMinesDome,SourceMinesDumping

User = get_user_model()


class DomeMerge(BaseTenantModel):
    original_dome = models.ForeignKey(
        SourceMinesDome,
        on_delete=models.CASCADE,
        related_name="merge_sources"
    )
    tonnage_primary = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    dome_second = models.ForeignKey(
        SourceMinesDome,
        on_delete=models.CASCADE,
        related_name="merge_targets"
    )
    tonnage_second = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    ref_id = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default="MERGED")
    is_undone = models.BooleanField(default=False)
    undone_at = models.DateTimeField(null=True, blank=True)
    undone_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="dome_merge_undo_users")
    undo_notes = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "geology_dome_compositing"
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["ref_id"]),
        ]

# class StockpileMerge(BaseTenantModel):
#     stockpile_ori = models.ForeignKey(
#         SourceMinesDumping,
#         on_delete=models.CASCADE,
#         related_name="merge_sources"
#     )
#     tonnage_primary = models.DecimalField(max_digits=18, decimal_places=4, default=0)

#     stockpile_second = models.ForeignKey(
#         SourceMinesDumping,
#         on_delete=models.CASCADE,
#         related_name="merge_targets"
#     )
#     tonnage_second = models.DecimalField(max_digits=18, decimal_places=4, default=0)

#     ref_id = models.CharField(max_length=50, null=True, blank=True)
#     status = models.CharField(max_length=20, default="MERGED")
#     is_undone = models.BooleanField(default=False)
#     undone_at = models.DateTimeField(null=True, blank=True)
#     undone_by = models.ForeignKey(
#         User,
#         null=True,
#         blank=True,
#         on_delete=models.SET_NULL,
#         related_name="stockpile_merge_undo_users"
#     )
#     undo_notes = models.TextField(null=True, blank=True)

#     description = models.TextField(null=True, blank=True)
#     user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

#     class Meta:
#         db_table = "geology_stockpiles_compositing"
#         indexes = [
#             models.Index(fields=["iup"]),
#             models.Index(fields=["ref_id"]),
#         ]