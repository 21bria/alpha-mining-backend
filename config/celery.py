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

# manual import task bot
import analytics.services.bot.tasks.production_review

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

}