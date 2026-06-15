from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.utils import timezone
from django_tenants.utils import schema_context, get_tenant_model

from analytics.models import ExportJob
from analytics.export_registry import get_exporter

# penting: import module exporter supaya registry terisi
from analytics.services.export.raw import export_geology_sample  # noqa: F401
from analytics.services.export.raw import export_geology_ore
from analytics.services.export.raw import export_geology_waybills
from analytics.services.export.raw import export_lab_assay_roa
from analytics.services.export.raw import export_lab_assay_mral
from analytics.services.export.raw import export_geology_sample_dome
from analytics.services.export.raw import export_geology_sample_psi

from analytics.services.export.raw import export_mining_plan_productions
from analytics.services.export.raw import export_mining_productions
from analytics.services.export.raw import export_fuel_consumption 
from analytics.services.export.raw import export_mining_weather 
from analytics.services.export.raw import export_mining_rainfall 

from analytics.services.export.raw import export_selling_barging 
from analytics.services.export.raw import export_selling_temporary 
from analytics.services.export.raw import export_selling_sample 
from analytics.services.export.raw import export_selling_official 
# Master
from analytics.services.export.raw import export_master_selling_code 
from analytics.services.export.raw import export_master_units 


@shared_task
def run_export_job(schema_name, job_id):
    with schema_context(schema_name):
        job = ExportJob.objects.get(pk=job_id)

        try:
            job.status = "processing"
            job.progress = 20
            job.save(update_fields=["status", "progress"])

            exporter = get_exporter(job.module)
            export_file = exporter(job)

            job.file = export_file
            job.status = "done"
            job.progress = 100
            job.finished_at = timezone.now()
            job.save(update_fields=["file", "status", "progress", "finished_at"])

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.save(update_fields=["status", "error"])
            raise

def _cleanup_empty_parent_dirs(file_path: str, stop_dir_name: str = "exports"):
    """
    Hapus folder kosong berantai ke atas sampai stop_dir_name.
    Contoh:
    exports/2026/04/13/file.xlsx
    -> hapus 13 jika kosong
    -> hapus 04 jika kosong
    -> hapus 2026 jika kosong
    -> stop di exports
    """
    current = Path(file_path).parent

    while current.exists() and current.is_dir():
        if current.name == stop_dir_name:
            break

        try:
            # folder masih ada isi, stop
            next(current.iterdir())
            break
        except StopIteration:
            # folder kosong, hapus lalu naik ke parent
            current.rmdir()
            current = current.parent


@shared_task
def cleanup_old_export_files(schema_name, days=7):
    with schema_context(schema_name):
        limit = timezone.now() - timedelta(days=days)

        jobs = ExportJob.objects.filter(
            created_at__lt=limit,
            file__isnull=False,
        )

        total = 0

        for job in jobs.iterator():
            file_path = None

            if job.file:
                try:
                    file_path = job.file.path
                except Exception:
                    file_path = None

                job.file.delete(save=False)

            job.file = None
            job.save(update_fields=["file"])
            total += 1

            if file_path:
                try:
                    _cleanup_empty_parent_dirs(file_path, stop_dir_name="exports")
                except Exception:
                    pass

        return f"{total} export files cleaned in schema {schema_name}"


@shared_task
def cleanup_old_export_files_all_schemas(days=7):
    TenantModel = get_tenant_model()

    total = 0

    for tenant in TenantModel.objects.all():
        schema_name = tenant.schema_name
        cleanup_old_export_files(schema_name, days)
        total += 1

    return f"Cleanup executed for {total} tenants"