from django.db import models
from django.db.models import Q
from core.models.base_tenant import BaseTenantModel
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class BodWeeklyReport(BaseTenantModel):
    code_source_field = "report_code"

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Published", "Published"),
        ("Archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report_code = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=150, default="Operations Scorecard")

    year = models.PositiveIntegerField()
    week = models.PositiveIntegerField()

    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Draft")

    summary_cards = models.JSONField(default=list, blank=True)
    notes = models.JSONField(default=dict, blank=True)

    remarks = models.TextField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "bod_weekly_report"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "year", "week"],
                condition=Q(is_deleted=False),
                name="unique_bod_weekly_report_by_iup_year_week_active",
            )
        ]
        indexes = [
            models.Index(fields=["iup", "year", "week"]),
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.year} W{self.week}"

class BodWeeklyMining(models.Model):
    DATA_SOURCE_CHOICES = [
        ("MANUAL", "Manual"),
        ("AUTO", "Auto"),
    ]

    GROUP_CHOICES = [
        ("ORE", "Ore"),
        ("WASTE", "Waste"),
        ("BARGING", "Barging"),
        ("TOTAL", "Total"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(BodWeeklyReport,on_delete=models.CASCADE,related_name="mining_rows")

    material = models.CharField(max_length=100)

    weekly_plan = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    achievement = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    status = models.CharField(max_length=30, null=True, blank=True)
     
    group = models.CharField(
        max_length=30,
        choices=GROUP_CHOICES,
        default="PRODUCTION",
    )
    is_total = models.BooleanField(default=False)
    is_grand_total = models.BooleanField(default=False)

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL"
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "bod_weekly_mining"
        indexes = [
            models.Index(fields=["report", "sort_order"]),
            models.Index(fields=["material"]),
        ]

    def __str__(self):
        return f"{self.material} - {self.report}"


class BodWeeklyMetric(models.Model):
    DATA_SOURCE_CHOICES = [
        ("MANUAL", "Manual"),
        ("AUTO", "Auto"),
    ]

    SECTION_CHOICES = [
        ("SUMMARY", "Summary"),
        ("HSE", "HSE"),
        ("FLEET", "Fleet"),
        ("BARGING", "Barging"),
        ("INVENTORY", "Inventory"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(BodWeeklyReport,on_delete=models.CASCADE,related_name="metrics")

    section = models.CharField(max_length=50, choices=SECTION_CHOICES, default="SUMMARY")

    title = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    suffix = models.CharField(max_length=20, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL"
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "bod_weekly_metric"
        indexes = [
            models.Index(fields=["report", "section", "sort_order"]),
            models.Index(fields=["section"]),
        ]

    def __str__(self):
        return f"{self.section} - {self.title}"


class BodWeeklyManpower(models.Model):
    DATA_SOURCE_CHOICES = [
        ("MANUAL", "Manual"),
        ("AUTO", "Auto"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey( BodWeeklyReport,on_delete=models.CASCADE,related_name="manpower_rows")

    contractor = models.CharField(max_length=100)
    personnel = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=200, null=True, blank=True)

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL"
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "bod_weekly_manpower"
        indexes = [
            models.Index(fields=["report", "sort_order"]),
            models.Index(fields=["contractor"]),
        ]

    def __str__(self):
        return f"{self.contractor} - {self.personnel}"


class BodWeeklyDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("PDF", "PDF"),
        ("EXCEL", "Excel"),
        ("IMAGE", "Image"),
        ("LINK", "Link"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(BodWeeklyReport,on_delete=models.CASCADE, related_name="documents",)

    title = models.CharField(max_length=150,null=True,blank=True)

    document_date = models.DateField(null=True, blank=True)

    file_name = models.CharField(max_length=150, null=True, blank=True)
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        default="PDF",
        null=True,
        blank=True
    )

    file = models.FileField(upload_to="bod/weekly-reports/%Y/%m/", null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "bod_weekly_document"
        indexes = [
            models.Index(fields=["report", "sort_order"]),
            models.Index(fields=["document_type"]),
            models.Index(fields=["document_date"]),
        ]

    def __str__(self):
        return self.title or self.file_name or str(self.id)

    def delete(self, *args, **kwargs):
        if self.file:
            self.file.delete(save=False)

        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = BodWeeklyDocument.objects.get(pk=self.pk)

                if old.file and old.file != self.file:
                    old.file.delete(save=False)

            except BodWeeklyDocument.DoesNotExist:
                pass

        super().save(*args, **kwargs)