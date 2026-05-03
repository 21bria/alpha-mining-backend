from django.db import models
from django.contrib.auth.models import AbstractUser

ROLE_CHOICES = (
    ("SYSTEM", "System Admin"),          # internal full control
    ("MANAGEMENT", "Management"),        # bisa lihat banyak IUP
    ("GLOBAL_VIEWER", "Global Viewer"),  # read only semua IUP
    ("SITE_USER", "Site User"),          # hanya IUP sendiri
)


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="SITE_USER"
    )

    default_iup_id = models.BigIntegerField(null=True, blank=True)
    allowed_iup_ids = models.JSONField(default=list, blank=True)

    # Helper properties biar enak dipakai di API
    @property
    def is_system(self):
        return self.role == "SYSTEM" or self.is_superuser

    @property
    def is_management(self):
        return self.role == "MANAGEMENT"

    @property
    def is_global_viewer(self):
        return self.role == "GLOBAL_VIEWER"

    @property
    def is_site_user(self):
        return self.role == "SITE_USER"
    
    