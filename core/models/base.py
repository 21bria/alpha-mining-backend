from django.db import models
from django.utils.text import slugify


def make_code(iup_code: str, value: str) -> str:
    return f"{iup_code}-{slugify(value)}".upper()

class IUPScopedModel(models.Model):
    iup = models.ForeignKey("master.MineIUP", on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class IUPCodeModel(IUPScopedModel):
    code = models.CharField(max_length=255, unique=True, editable=False)
    code_source_field: str = ""  # override di subclass

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.iup and self.code_source_field:
            raw = getattr(self, self.code_source_field, None)
            if raw:
                self.code = make_code(self.iup.iup_code, str(raw))
        super().save(*args, **kwargs)