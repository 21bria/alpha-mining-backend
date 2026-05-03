from django.conf import settings
from django.db import models

class UserIUPAccess(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    allowed_iups = models.ManyToManyField(
        "master.MineIUP",
        blank=True
    )

    default_iup = models.ForeignKey(
        "master.MineIUP",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    class Meta:
        db_table  = 'master_user_iup_access'

