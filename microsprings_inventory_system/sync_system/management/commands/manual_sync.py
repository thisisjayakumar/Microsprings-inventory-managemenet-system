"""
Manual Database Sync Command

This command provides comprehensive manual synchronization between local and remote databases.
Perfect for initial sync after recreating the cloud database.

Usage:
    python manage.py manual_sync --action sync                    # Full sync
    python manage.py manual_sync --action sync --dry-run         # Test run
    python manage.py manual_sync --action sync --app inventory   # Sync specific app
    python manage.py manual_sync --action sync --model products.product  # Sync specific model
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connections
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Manual database synchronization with progress tracking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['sync', 'validate', 'compare'],
            default='sync',
            help='Action to perform'
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Sync specific app only'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Sync specific model only (format: app.model)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for syncing records'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if validation fails'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.batch_size = options['batch_size']
        self.force = options['force']
        
        # Test database connections
        if not self._test_connections():
            return
        
        # Get models to sync
        models = self._get_models_to_sync(options)
        
        if not models:
            self.stdout.write(self.style.WARNING("No models found to sync"))
            return
        
        self.stdout.write(f"Found {len(models)} models to process")
        
        # Execute action
        if options['action'] == 'sync':
            self._sync_models(models)
        elif options['action'] == 'validate':
            self._validate_sync(models)
        elif options['action'] == 'compare':
            self._compare_databases(models)

    def _test_connections(self):
        """Test database connections"""
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("✓ Local database connection: OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Local database connection failed: {e}"))
            return False
        
        try:
            with connections['remote'].cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("✓ Remote database connection: OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Remote database connection failed: {e}"))
            return False
        
        return True

    def _get_models_to_sync(self, options):
        """Get list of models to sync based on options"""
        all_models = []
        
        for app_config in apps.get_app_configs():
            if options.get('app') and app_config.label != options['app']:
                continue
            
            for model in app_config.get_models():
                model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                
                if options.get('model') and model_name != options['model']:
                    continue
                
                all_models.append(model)
        
        return all_models

    def _sync_models(self, models):
        """Sync models from local to remote database"""
        self.stdout.write(self.style.WARNING("🔄 Starting manual sync..."))
        
        sync_results = {
            'total_models': len(models),
            'synced_models': 0,
            'failed_models': [],
            'total_records_synced': 0,
            'errors': []
        }
        
        for model in tqdm(models, desc="Syncing models", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            try:
                records_synced = self._sync_model(model)
                sync_results['total_records_synced'] += records_synced
                sync_results['synced_models'] += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Synced {model_name}: {records_synced} records")
                )
                
            except Exception as e:
                sync_results['failed_models'].append(model_name)
                sync_results['errors'].append(f"{model_name}: {e}")
                
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to sync {model_name}: {e}")
                )
        
        self._display_sync_results(sync_results)

    def _sync_model(self, model):
        """Sync a specific model from local to remote"""
        table_name = model._meta.db_table
        records_synced = 0
        
        if self.dry_run:
            self.stdout.write(f"[DRY RUN] Would sync {table_name}")
            return 0
        
        try:
            # Get all local records
            with connections['default'].cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table_name}")
                local_records = cursor.fetchall()
            
            if not local_records:
                return 0
            
            # Get field names
            field_names = [field.name for field in model._meta.fields]
            
            # Sync records in batches
            with connections['remote'].cursor() as cursor:
                for i in tqdm(range(0, len(local_records), self.batch_size), 
                             desc=f"Syncing {table_name}", leave=False):
                    batch = local_records[i:i + self.batch_size]
                    
                    for record in batch:
                        record_dict = dict(zip(field_names, record))
                        self._upsert_record(cursor, table_name, record_dict)
                        records_synced += 1
                
                connections['remote'].commit()
        
        except Exception as e:
            connections['remote'].rollback()
            raise e
        
        return records_synced

    def _upsert_record(self, cursor, table_name, record_data):
        """Upsert a record into the remote database"""
        # Get actual database column names for this table
        cursor.execute(f"DESCRIBE {table_name}")
        db_column_info = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Map Django field names to database column names
        db_columns = []
        db_values = []
        
        for field_name, field_value in record_data.items():
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
        
        if not db_columns:
            logger.warning(f"No valid columns found for table {table_name}")
            return
        
        placeholders = ['%s'] * len(db_columns)
        updates = [f"{col}=VALUES({col})" for col in db_columns if col != 'id']
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(db_columns)})
            VALUES ({', '.join(placeholders)})
            ON DUPLICATE KEY UPDATE {', '.join(updates)}
        """
        
        cursor.execute(query, db_values)

    def _validate_sync(self, models):
        """Validate sync by comparing record counts"""
        self.stdout.write(self.style.WARNING("🔍 Validating sync..."))
        
        validation_results = {
            'total_models': len(models),
            'validated_models': 0,
            'mismatched_models': [],
            'errors': []
        }
        
        for model in tqdm(models, desc="Validating models", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            try:
                local_count, remote_count = self._get_record_counts(model)
                
                if local_count == remote_count:
                    validation_results['validated_models'] += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {model_name}: {local_count} records (synced)")
                    )
                else:
                    validation_results['mismatched_models'].append({
                        'model': model_name,
                        'local_count': local_count,
                        'remote_count': remote_count
                    })
                    self.stdout.write(
                        self.style.WARNING(f"⚠ {model_name}: Local={local_count}, Remote={remote_count}")
                    )
                
            except Exception as e:
                validation_results['errors'].append(f"{model_name}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to validate {model_name}: {e}")
                )
        
        self._display_validation_results(validation_results)

    def _get_record_counts(self, model):
        """Get record counts for local and remote databases"""
        table_name = model._meta.db_table
        
        with connections['default'].cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            local_count = cursor.fetchone()[0]
        
        with connections['remote'].cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            remote_count = cursor.fetchone()[0]
        
        return local_count, remote_count

    def _compare_databases(self, models):
        """Generate detailed comparison report"""
        self.stdout.write(self.style.WARNING("📊 Generating database comparison..."))
        
        comparison_results = {
            'timestamp': self._get_timestamp(),
            'models': {}
        }
        
        for model in tqdm(models, desc="Comparing models", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            comparison_results['models'][model_name] = self._get_model_comparison(model)
        
        self._display_comparison_results(comparison_results)

    def _get_model_comparison(self, model):
        """Get detailed comparison for a single model"""
        table_name = model._meta.db_table
        results = {
            'local_count': 0,
            'remote_count': 0,
            'missing_ids': [],
            'extra_ids': [],
            'mismatched_records': []
        }
        
        try:
            # Get counts
            results['local_count'], results['remote_count'] = self._get_record_counts(model)
            
            # Get ID lists
            with connections['default'].cursor() as cursor:
                cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
                local_ids = set(row[0] for row in cursor.fetchall())
            
            with connections['remote'].cursor() as cursor:
                cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
                remote_ids = set(row[0] for row in cursor.fetchall())
            
            # Find differences
            results['missing_ids'] = list(local_ids - remote_ids)
            results['extra_ids'] = list(remote_ids - local_ids)
            
        except Exception as e:
            logger.error(f"Error comparing model {table_name}: {e}")
        
        return results

    def _display_sync_results(self, results):
        """Display sync results summary"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("SYNC RESULTS")
        self.stdout.write("="*60)
        self.stdout.write(f"Models Synced: {results['synced_models']}/{results['total_models']}")
        self.stdout.write(f"Total Records Synced: {results['total_records_synced']}")
        
        if results['failed_models']:
            self.stdout.write(f"\nFailed Models ({len(results['failed_models'])}):")
            for model in results['failed_models']:
                self.stdout.write(f"  - {model}")
        
        if results['errors']:
            self.stdout.write(f"\nErrors:")
            for error in results['errors']:
                self.stdout.write(f"  - {error}")

    def _display_validation_results(self, results):
        """Display validation results summary"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("VALIDATION RESULTS")
        self.stdout.write("="*60)
        self.stdout.write(f"Models Validated: {results['validated_models']}/{results['total_models']}")
        
        if results['mismatched_models']:
            self.stdout.write(f"\nMismatched Models ({len(results['mismatched_models'])}):")
            for mismatch in results['mismatched_models']:
                self.stdout.write(f"  - {mismatch['model']}: Local={mismatch['local_count']}, Remote={mismatch['remote_count']}")

    def _display_comparison_results(self, results):
        """Display comparison results summary"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("DATABASE COMPARISON")
        self.stdout.write("="*60)
        
        total_models = len(results['models'])
        synced_models = sum(1 for model_data in results['models'].values() 
                           if model_data['local_count'] == model_data['remote_count'])
        
        self.stdout.write(f"Models Compared: {total_models}")
        self.stdout.write(f"Fully Synced: {synced_models}")
        self.stdout.write(f"Sync Status: {synced_models/total_models*100:.1f}%")
        
        # Show detailed results for mismatched models
        for model_name, model_data in results['models'].items():
            if model_data['local_count'] != model_data['remote_count']:
                self.stdout.write(f"\n{model_name}:")
                self.stdout.write(f"  Local: {model_data['local_count']} records")
                self.stdout.write(f"  Remote: {model_data['remote_count']} records")
                if model_data['missing_ids']:
                    self.stdout.write(f"  Missing IDs: {len(model_data['missing_ids'])}")
                if model_data['extra_ids']:
                    self.stdout.write(f"  Extra IDs: {len(model_data['extra_ids'])}")

    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
