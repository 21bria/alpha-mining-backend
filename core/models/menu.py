from django.db import models

class MenuItem(models.Model):
    heading = models.CharField(max_length=100)
    title = models.CharField(max_length=100)

    icon = models.CharField(max_length=80, blank=True)
    link = models.CharField(max_length=200, blank=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE
    )

    order = models.IntegerField(default=0)

    required_perms = models.JSONField(default=list, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "core_menu_items"
        ordering = ["heading", "order"]        