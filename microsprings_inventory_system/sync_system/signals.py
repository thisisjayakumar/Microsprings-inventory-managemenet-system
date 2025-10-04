
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .sync_service import sync_service

@receiver(post_save)
def track_save_operations(sender, **kwargs):
    """Track all save operations for sync"""
    if not getattr(settings, 'ENABLE_DB_SYNC', False):
        return
    
    instance = kwargs['instance']
    operation = 'update' if kwargs['created'] is False else 'create'
    
    # Save to file first to ensure persistence
    sync_service._persist_queue()
    
    # Queue for synchronization
    sync_service.queue_for_sync(sender, instance, operation)

@receiver(post_delete)
def track_delete_operations(sender, **kwargs):
    """Track all delete operations for sync"""
    if not getattr(settings, 'ENABLE_DB_SYNC', False):
        return
    
    instance = kwargs['instance']
    
    # Save to file first to ensure persistence
    sync_service._persist_queue()
    
    sync_service.queue_for_sync(sender, instance, 'delete')