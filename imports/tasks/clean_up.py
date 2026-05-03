# imports/tasks.py
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.utils import timezone
from django_tenants.utils import schema_context, get_tenant_model

from imports.models import ImportJob
# python manage.py shell
# from imports.tasks.clean_up import cleanup_old_import_files_all_schemas
# cleanup_old_import_files_all_schemas(0)

def _cleanup_empty_parent_dirs(file_path: str, stop_dir_name: str = "imports"):
    """
    Hapus folder kosong berantai ke atas sampai stop_dir_name.
    Contoh:
    imports/2026/04/13/file.xlsx
    -> hapus 13 jika kosong
    -> hapus 04 jika kosong
    -> hapus 2026 jika kosong
    -> stop di imports
    """
    current = Path(file_path).parent

    while current.exists() and current.is_dir():
        if current.name == stop_dir_name:
            break

        try:
            next(current.iterdir())
            break
        except StopIteration:
            current.rmdir()
            current = current.parent


@shared_task
def cleanup_old_import_files(schema_name, days=14):
    with schema_context(schema_name):
        limit = timezone.now() - timedelta(days=days)

        jobs = ImportJob.objects.filter(
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
                    _cleanup_empty_parent_dirs(file_path, stop_dir_name="imports")
                except Exception:
                    pass

        return f"{total} import files cleaned in schema {schema_name}"


@shared_task
def cleanup_old_import_files_all_schemas(days=14):
    TenantModel = get_tenant_model()

    total = 0

    for tenant in TenantModel.objects.all():
        schema_name = tenant.schema_name
        cleanup_old_import_files(schema_name, days)
        total += 1

    return f"Import cleanup executed for {total} tenants"