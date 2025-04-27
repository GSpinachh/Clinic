from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class ClinicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinic'
    verbose_name = _('Управление клиникой')

    def ready(self):
        import clinic.signals
        
        self.init_scheduled_tasks()

        self.configure_logging()

    def init_scheduled_tasks(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore
            from clinic.tasks import send_appointment_reminders
            
            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), 'default')
            
            scheduler.add_job(
                send_appointment_reminders,
                'interval',
                hours=1,
                id='appointment_reminders',
                replace_existing=True,
            )
            
            scheduler.start()
        except ImportError:
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to start scheduler: {e}")

    def configure_logging(self):
        import logging
        import logging.config
        from django.conf import settings
        
        LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '{levelname} {asctime} {module} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.FileHandler',
                    'filename': settings.BASE_DIR / 'logs' / 'clinic.log',
                    'formatter': 'verbose',
                },
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'clinic': {
                    'handlers': ['file', 'console'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
            },
        }
        
        logging.config.dictConfig(LOGGING_CONFIG)

    @property
    def clinic_settings(self):
        from django.conf import settings
        return getattr(settings, 'CLINIC_SETTINGS', {})