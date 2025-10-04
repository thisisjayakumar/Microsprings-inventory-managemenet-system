from django.apps import AppConfig

class SyncSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'microsprings_inventory_system.sync_system'
    verbose_name = 'Database Sync System'
    
    def ready(self):
        from . import signals