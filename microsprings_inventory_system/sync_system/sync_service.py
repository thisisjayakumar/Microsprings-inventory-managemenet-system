import threading
import queue
import os
import logging
from django.db import connections
from django.core.serializers import serialize
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DBSyncService:
    def __init__(self):
        self.sync_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        self.last_sync = None
        
    def start_sync_service(self):
        """Start the background sync service"""
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._sync_worker, daemon=True)
        self.worker_thread.start()
        logger.info("Database sync service started")
    
    def stop_sync_service(self):
        """Stop the sync service"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("Database sync service stopped")
    
    def queue_for_sync(self, model, instance, operation):
        """Queue an operation for synchronization"""
        sync_data = {
            'model': f"{model._meta.app_label}.{model._meta.model_name}",
            'instance_id': instance.pk,
            'operation': operation,  # 'create', 'update', 'delete'
            'timestamp': datetime.now().isoformat(),
            'data': self._serialize_instance(instance) if operation != 'delete' else None
        }
        self.sync_queue.put(sync_data)
    
    def _serialize_instance(self, instance):
        """Serialize instance to JSON"""
        from django.core.serializers import serialize
        return json.loads(serialize('json', [instance]))[0]
    
    def _sync_worker(self):
        """Background worker that processes sync queue"""
        batch = []
        batch_size = 50
        max_wait = 5  # seconds
        
        while self.is_running:
            try:
                # Wait for items with timeout
                item = self.sync_queue.get(timeout=max_wait)
                batch.append(item)
                
                # Process batch when full or timeout
                if len(batch) >= batch_size:
                    self._process_batch(batch)
                    batch = []
                    
            except queue.Empty:
                # Process remaining items if any
                if batch:
                    self._process_batch(batch)
                    batch = []
    
    def _process_batch(self, batch):
        """Process a batch of sync operations"""
        try:
            with connections['remote'].cursor() as cursor:
                for item in batch:
                    self._apply_operation(cursor, item)
                connections['remote'].commit()
            self.last_sync = datetime.now()
            logger.info(f"Successfully synced {len(batch)} operations")
        except Exception as e:
            logger.error(f"Sync batch failed: {e}")
            connections['remote'].rollback()
    
    def _apply_operation(self, cursor, item):
        """Apply a single operation to remote database"""
        if item['operation'] == 'delete':
            cursor.execute(f"DELETE FROM {self._get_table_name(item['model'])} WHERE id = %s", 
                          [item['instance_id']])
        else:
            # Handle create/update operations
            self._upsert_instance(cursor, item)
    
    def _upsert_instance(self, cursor, item):
        # This is a simplified version
        table_name = self._get_table_name(item['model'])
        fields = item['data']['fields']
        pk = item['data']['pk']

        # Get actual database column names for this table
        cursor.execute(f"DESCRIBE {table_name}")
        db_column_info = {row[0]: row[1] for row in cursor.fetchall()}

        # Map Django field names to database column names
        db_columns = ['id']
        db_values = [pk]

        for field_name, field_value in fields.items():
            # Check if this field exists in the database
            if field_name in db_column_info:
                db_columns.append(field_name)
                db_values.append(field_value)
            elif f"{field_name}_id" in db_column_info:
                # Try with _id suffix for foreign keys
                db_columns.append(f"{field_name}_id")
                db_values.append(field_value)
            else:
                # Skip fields that don't exist in the database
                logger.warning(f"Skipping field {field_name} for table {table_name} - not found in database")
                continue

        # Build INSERT ... ON DUPLICATE KEY UPDATE query
        placeholders = ['%s'] * len(db_columns)
        updates = [f"{col}=VALUES({col})" for col in db_columns if col != 'id']

        query = f"""
            INSERT INTO {table_name} ({', '.join(db_columns)})
            VALUES ({', '.join(placeholders)})
            ON DUPLICATE KEY UPDATE {', '.join(updates)}
        """

        cursor.execute(query, db_values)
    
    def _get_table_name(self, model_path):
        """Convert model path to database table name"""
        app_label, model_name = model_path.split('.')
        return f"{app_label}_{model_name}"

class PersistentDBSyncService(DBSyncService):
    def __init__(self):
        super().__init__()
        self.persistence_file = 'sync_queue.json'
        self._load_persisted_queue()
    
    def _load_persisted_queue(self):
        """Load queue from file on startup"""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    persisted = json.load(f)
                    for item in persisted:
                        self.sync_queue.put(item)
                os.remove(self.persistence_file)  # Clean up after loading
        except Exception as e:
            logger.error(f"Failed to load persisted queue: {e}")
    
    def _persist_queue(self):
        """Save current queue to file (call this periodically)"""
        try:
            queue_items = list(self.sync_queue.queue)
            with open(self.persistence_file, 'w') as f:
                json.dump(queue_items, f)
        except Exception as e:
            logger.error(f"Failed to persist queue: {e}")

# Create a singleton instance
sync_service = PersistentDBSyncService()