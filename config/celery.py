import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


# Set zona waktu
app.conf.timezone = settings.TIME_ZONE
app.conf.enable_utc = True

app.conf.beat_schedule = {
    # CLEAN  FILE 
    'cleanup-import-files-daily': {
        'task': 'imports.tasks.clean_up.cleanup_old_import_files_all_schemas',
        'schedule': crontab(hour=3, minute=30),
        'args': (14,),
    },
    'cleanup-export-files-daily': {
        'task': 'analytics.tasks.cleanup_old_export_files_all_schemas',
        'schedule': crontab(hour=3, minute=0),
        'args': (7,),  # hapus >7 hari
    },

    # existing kamu
    # 'clean-duplicate-files-daily': {
    #     'task': 'kqms.task.cleanup.clean_temp_duplicates',
    #     'schedule': crontab(hour=2, minute=0),
    # },

    # 'truncate-task-imports-daily': {
    #     'task': 'kqms.task.cleanup.truncate_old_task_imports',
    #     'schedule': crontab(hour=2, minute=30),
    #     'args': (1,),
    # },

    # 'auto-sync-dome-status-every-1-hour': {
    #     'task': 'kqms.task.auto_sync.auto_sync_dome_status_task',
    #     'schedule': crontab(minute=0, hour='*/1'),
    # },
}