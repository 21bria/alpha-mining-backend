from celery import shared_task
from django.utils import timezone
from django_tenants.utils import schema_context

from imports.models import ImportJob, ImportJobRow
from ..utils.import_parsers import read_file
from ..importers.registry import IMPORTER_REGISTRY
from ..importers.header_registry import HEADER_REGISTRY


@shared_task(bind=True)
def run_import_job(self, schema_name: str, job_id: str):
    with schema_context(schema_name):
        job = ImportJob.objects.get(id=job_id)

        job.status = "running"
        job.started_at = timezone.now()
        job.progress = 1
        job.message = None
        job.save(update_fields=["status", "started_at", "progress", "message"])

        try:
            # 1. ambil importer
            ImporterCls = IMPORTER_REGISTRY.get(job.module)
            if not ImporterCls:
                raise ValueError(f"Unknown module: {job.module}")

            # 2. ambil header config sesuai module
            header_conf = HEADER_REGISTRY.get(job.module, {})
            required_headers = header_conf.get("required", None)
            allowed_headers = header_conf.get("allowed", None)
            aliases = header_conf.get("aliases", None)

            # 3. baca file + validasi header
            rows = read_file(
                job.file.path,
                required_headers=required_headers,
                allowed_headers=allowed_headers,
                aliases=aliases,
            )

            job.total_rows = len(rows)
            job.save(update_fields=["total_rows"])

            # 4. jalankan importer
            importer = ImporterCls()
            result = importer.run(rows, user=job.created_by)

            # 5. simpan detail error row
            if result.errors:
                ImportJobRow.objects.bulk_create(
                    [
                        ImportJobRow(
                            job=job,
                            row_number=row_no,
                            status="failed",
                            payload=payload,
                            error=err,
                        )
                        for (row_no, payload, err) in result.errors
                    ],
                    batch_size=500,
                )

            # 6. update job result
            job.success_rows = result.success
            job.failed_rows = result.failed
            job.progress = 100
            job.status = "success" if result.failed == 0 else "failed"
            job.finished_at = timezone.now()

            if result.failed > 0:
                job.message = f"Import selesai dengan {result.failed} baris gagal."
            else:
                job.message = "Import selesai."

            job.save(
                update_fields=[
                    "success_rows",
                    "failed_rows",
                    "progress",
                    "status",
                    "finished_at",
                    "message",
                ]
            )

        except Exception as e:
            job.status = "failed"
            job.message = str(e)
            job.finished_at = timezone.now()
            job.progress = 100
            job.save(
                update_fields=[
                    "status",
                    "message",
                    "finished_at",
                    "progress",
                ]
            )
            raise