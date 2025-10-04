# routers.py
import threading
from django.db import models
from queue import Queue
import logging

logger = logging.getLogger(__name__)

class SyncRouter:
    """
    Routes writes to both local and remote, reads from local
    """
    route_app_labels = {'your_app_names'}
    
    def db_for_read(self, model, **hints):
        return 'default'  # Always read from local

    def db_for_write(self, model, **hints):
        return 'default'  # Primary write to local

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True