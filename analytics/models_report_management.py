from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.models.base_tenant import BaseTenantModel
import uuid

User = get_user_model()


class ReportManagement(BaseTenantModel):
    code_source_field = "report_code"

    PERIOD_TYPE_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("range", "Custom range"),
    ]

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Published", "Published"),
        ("Archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report_code = models.CharField(max_length=80, null=True, blank=True)
    title = models.CharField(max_length=150, default="Operations Management Report")

    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default="weekly",
    )

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(null=True, blank=True)
    week = models.PositiveIntegerField(null=True, blank=True)

    period_key = models.CharField(max_length=30)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Draft")

    summary_cards = models.JSONField(default=list, blank=True)
    notes = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(null=True, blank=True)

     # Summary Cards
    hse_incidents = models.IntegerField(default=0)

    total_production = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    total_barging = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    total_movement = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    total_inventory = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    avg_ni = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    stockpile_count = models.IntegerField(default=0)

    # Sync
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    published_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_management_reports",
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "report_management"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "period_type", "period_key"],
                condition=Q(is_deleted=False),
                name="unique_report_management_period_active",
            )
        ]
        indexes = [
            models.Index(fields=["iup", "period_type", "period_key"]),
            models.Index(fields=["year", "month", "week"]),
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.period_key:
            if self.period_type == "weekly":
                self.period_key = f"{self.year}-W{str(self.week).zfill(2)}"

            elif self.period_type == "monthly":
                self.period_key = f"{self.year}-{str(self.month).zfill(2)}"

            elif self.period_type == "yearly":
                self.period_key = str(self.year)

            elif self.period_type == "range":
                self.period_key = f"{self.period_start}_{self.period_end}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.period_type} {self.period_key}"
    
class ReportManagementMining(models.Model):
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

    report = models.ForeignKey(
        ReportManagement,
        on_delete=models.CASCADE,
        related_name="mining_rows",
    )

    material = models.CharField(max_length=100)

    plan = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    actual = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    achievement = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    status = models.CharField(max_length=30, null=True, blank=True)

    group = models.CharField(
        max_length=30,
        choices=GROUP_CHOICES,
        default="ORE",
    )

    is_total = models.BooleanField(default=False)
    is_grand_total = models.BooleanField(default=False)

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL",
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "report_management_mining"
        indexes = [
            models.Index(fields=["report", "sort_order"]),
            models.Index(fields=["material"]),
            models.Index(fields=["group"]),
        ]

    def __str__(self):
        return f"{self.material} - {self.report}"

class ReportManagementMetric(models.Model):
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
        ("QUALITY", "Quality"),
        ("MAINTENANCE", "Maintenance"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    report = models.ForeignKey(
        ReportManagement,
        on_delete=models.CASCADE,
        related_name="metrics",
    )

    code = models.CharField(
        max_length=30,
        blank=True,
        default="",
        db_index=True,
    )

    section = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES,
        default="SUMMARY",
    )

    title = models.CharField(max_length=100)

    value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    suffix = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL",
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "report_management_metric"
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["report", "section", "sort_order"]),
            models.Index(fields=["report", "code"]),
            models.Index(fields=["section"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "code"],
                condition=~models.Q(code=""),
                name="unique_report_management_metric_code",
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = str(self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.section} - {self.code or self.title}"
    
class ReportManagementTarget(BaseTenantModel):
    report = models.ForeignKey(
        ReportManagement,
        on_delete=models.CASCADE,
        related_name="targets",
    )

    code = models.CharField(
        max_length=30,
        db_index=True,
    )

    title = models.CharField(max_length=100)

    plan = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    unit = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    class Meta:
        db_table = "report_management_target"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["report", "code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "code"],
                name="unique_report_management_target_code",
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = str(self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"

class ReportManagementManpower(models.Model):
    DATA_SOURCE_CHOICES = [
        ("MANUAL", "Manual"),
        ("AUTO", "Auto"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(
        ReportManagement,
        on_delete=models.CASCADE,
        related_name="manpower_rows",
    )

    contractor = models.CharField(max_length=100)
    personnel = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=200, null=True, blank=True)

    source_module = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL",
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "report_management_manpower"
        indexes = [
            models.Index(fields=["report", "sort_order"]),
            models.Index(fields=["contractor"]),
        ]

    def __str__(self):
        return f"{self.contractor} - {self.personnel}"

class ReportManagementDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("PDF", "PDF"),
        ("EXCEL", "Excel"),
        ("IMAGE", "Image"),
        ("LINK", "Link"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(
        ReportManagement,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(max_length=150, null=True, blank=True)
    document_date = models.DateField(null=True, blank=True)

    file_name = models.CharField(max_length=150, null=True, blank=True)
    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
        default="PDF",
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="reports/management/%Y/%m/",
        null=True,
        blank=True,
    )
    external_url = models.URLField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "report_management_document"
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
                old = ReportManagementDocument.objects.get(pk=self.pk)
                if old.file and old.file != self.file:
                    old.file.delete(save=False)
            except ReportManagementDocument.DoesNotExist:
                pass

        super().save(*args, **kwargs)