"""
Database Validation Command

This command provides comprehensive validation and verification of database sync.
Perfect for checking data integrity, structure mismatches, and sync completeness.

Usage:
    python manage.py db_validate --action validate                    # Full validation
    python manage.py db_validate --action validate --app inventory   # Validate specific app
    python manage.py db_validate --action structure                  # Check structure only
    python manage.py db_validate --action data                       # Check data only
    python manage.py db_validate --action report --output report.json # Generate report
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connections
from tqdm import tqdm
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Comprehensive database validation and verification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['validate', 'structure', 'data', 'report'],
            default='validate',
            help='Validation action to perform'
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Validate specific app only'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Validate specific model only (format: app.model)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file for report (JSON format)'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed validation results'
        )
        parser.add_argument(
            '--fix-suggestions',
            action='store_true',
            help='Show suggestions for fixing issues'
        )

    def handle(self, *args, **options):
        self.detailed = options['detailed']
        self.fix_suggestions = options['fix_suggestions']
        
        # Test database connections
        if not self._test_connections():
            return
        
        # Get models to validate
        models = self._get_models_to_validate(options)
        
        if not models:
            self.stdout.write(self.style.WARNING("No models found to validate"))
            return
        
        self.stdout.write(f"Found {len(models)} models to validate")
        
        # Execute validation action
        if options['action'] == 'validate':
            results = self._full_validation(models)
        elif options['action'] == 'structure':
            results = self._structure_validation(models)
        elif options['action'] == 'data':
            results = self._data_validation(models)
        elif options['action'] == 'report':
            results = self._generate_report(models)
        
        # Display results
        self._display_results(results, options['action'])
        
        # Save report if requested
        if options['output']:
            self._save_report(results, options['output'])

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

    def _get_models_to_validate(self, options):
        """Get list of models to validate based on options"""
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

    def _full_validation(self, models):
        """Perform full validation (structure + data)"""
        self.stdout.write(self.style.WARNING("🔍 Starting full validation..."))
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'full',
            'total_models': len(models),
            'structure_results': {},
            'data_results': {},
            'summary': {
                'structure_issues': 0,
                'data_issues': 0,
                'models_validated': 0,
                'models_with_issues': 0
            }
        }
        
        for model in tqdm(models, desc="Validating models", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            # Structure validation
            structure_result = self._validate_model_structure(model)
            results['structure_results'][model_name] = structure_result
            
            # Data validation
            data_result = self._validate_model_data(model)
            results['data_results'][model_name] = data_result
            
            # Update summary
            if structure_result['has_issues']:
                results['summary']['structure_issues'] += 1
            if data_result['has_issues']:
                results['summary']['data_issues'] += 1
            
            if not structure_result['has_issues'] and not data_result['has_issues']:
                results['summary']['models_validated'] += 1
            else:
                results['summary']['models_with_issues'] += 1
        
        return results

    def _structure_validation(self, models):
        """Validate database structure only"""
        self.stdout.write(self.style.WARNING("🏗️ Validating database structure..."))
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'structure',
            'total_models': len(models),
            'structure_results': {},
            'summary': {
                'structure_issues': 0,
                'models_validated': 0
            }
        }
        
        for model in tqdm(models, desc="Validating structure", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            structure_result = self._validate_model_structure(model)
            results['structure_results'][model_name] = structure_result
            
            if structure_result['has_issues']:
                results['summary']['structure_issues'] += 1
            else:
                results['summary']['models_validated'] += 1
        
        return results

    def _data_validation(self, models):
        """Validate data integrity only"""
        self.stdout.write(self.style.WARNING("📊 Validating data integrity..."))
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'data',
            'total_models': len(models),
            'data_results': {},
            'summary': {
                'data_issues': 0,
                'models_validated': 0
            }
        }
        
        for model in tqdm(models, desc="Validating data", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            data_result = self._validate_model_data(model)
            results['data_results'][model_name] = data_result
            
            if data_result['has_issues']:
                results['summary']['data_issues'] += 1
            else:
                results['summary']['models_validated'] += 1
        
        return results

    def _validate_model_structure(self, model):
        """Validate structure for a single model"""
        table_name = model._meta.db_table
        result = {
            'table_name': table_name,
            'has_issues': False,
            'issues': [],
            'local_columns': [],
            'remote_columns': [],
            'missing_columns': [],
            'extra_columns': [],
            'type_mismatches': []
        }
        
        try:
            # Get local table structure
            with connections['default'].cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                local_columns = {row[0]: row[1] for row in cursor.fetchall()}
                result['local_columns'] = list(local_columns.keys())
            
            # Get remote table structure
            with connections['remote'].cursor() as cursor:
                cursor.execute(f"DESCRIBE {table_name}")
                remote_columns = {row[0]: row[1] for row in cursor.fetchall()}
                result['remote_columns'] = list(remote_columns.keys())
            
            # Compare structures
            missing_columns = set(local_columns.keys()) - set(remote_columns.keys())
            extra_columns = set(remote_columns.keys()) - set(local_columns.keys())
            
            result['missing_columns'] = list(missing_columns)
            result['extra_columns'] = list(extra_columns)
            
            # Check for type mismatches
            common_columns = set(local_columns.keys()) & set(remote_columns.keys())
            for col in common_columns:
                if local_columns[col] != remote_columns[col]:
                    result['type_mismatches'].append({
                        'column': col,
                        'local_type': local_columns[col],
                        'remote_type': remote_columns[col]
                    })
            
            # Determine if there are issues
            result['has_issues'] = bool(missing_columns or extra_columns or result['type_mismatches'])
            
            if result['has_issues']:
                if missing_columns:
                    result['issues'].append(f"Missing columns: {', '.join(missing_columns)}")
                if extra_columns:
                    result['issues'].append(f"Extra columns: {', '.join(extra_columns)}")
                if result['type_mismatches']:
                    result['issues'].append(f"Type mismatches: {len(result['type_mismatches'])} columns")
        
        except Exception as e:
            result['has_issues'] = True
            result['issues'].append(f"Error validating structure: {e}")
        
        return result

    def _validate_model_data(self, model):
        """Validate data integrity for a single model"""
        table_name = model._meta.db_table
        result = {
            'table_name': table_name,
            'has_issues': False,
            'issues': [],
            'local_count': 0,
            'remote_count': 0,
            'missing_ids': [],
            'extra_ids': [],
            'data_mismatches': [],
            'sync_status': 'unknown'
        }
        
        try:
            # Get record counts
            with connections['default'].cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result['local_count'] = cursor.fetchone()[0]
            
            with connections['remote'].cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result['remote_count'] = cursor.fetchone()[0]
            
            # Get ID lists for comparison
            with connections['default'].cursor() as cursor:
                cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
                local_ids = set(row[0] for row in cursor.fetchall())
            
            with connections['remote'].cursor() as cursor:
                cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
                remote_ids = set(row[0] for row in cursor.fetchall())
            
            # Find differences
            missing_ids = local_ids - remote_ids
            extra_ids = remote_ids - local_ids
            
            result['missing_ids'] = list(missing_ids)
            result['extra_ids'] = list(extra_ids)
            
            # Determine sync status
            if result['local_count'] == result['remote_count'] and not missing_ids and not extra_ids:
                result['sync_status'] = 'synced'
            elif result['local_count'] > result['remote_count']:
                result['sync_status'] = 'behind'
            elif result['local_count'] < result['remote_count']:
                result['sync_status'] = 'ahead'
            else:
                result['sync_status'] = 'mismatched'
            
            # Check for issues
            if missing_ids:
                result['issues'].append(f"Missing {len(missing_ids)} records in remote")
            if extra_ids:
                result['issues'].append(f"Extra {len(extra_ids)} records in remote")
            if result['local_count'] != result['remote_count']:
                result['issues'].append(f"Count mismatch: Local={result['local_count']}, Remote={result['remote_count']}")
            
            result['has_issues'] = bool(result['issues'])
        
        except Exception as e:
            result['has_issues'] = True
            result['issues'].append(f"Error validating data: {e}")
        
        return result

    def _generate_report(self, models):
        """Generate comprehensive validation report"""
        self.stdout.write(self.style.WARNING("📋 Generating comprehensive report..."))
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'report',
            'total_models': len(models),
            'models': {},
            'summary': {
                'total_models': len(models),
                'structure_issues': 0,
                'data_issues': 0,
                'fully_synced': 0,
                'partially_synced': 0,
                'not_synced': 0
            }
        }
        
        for model in tqdm(models, desc="Generating report", unit="model"):
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            # Get both structure and data validation
            structure_result = self._validate_model_structure(model)
            data_result = self._validate_model_data(model)
            
            results['models'][model_name] = {
                'structure': structure_result,
                'data': data_result,
                'overall_status': 'unknown'
            }
            
            # Determine overall status
            if not structure_result['has_issues'] and not data_result['has_issues']:
                results['models'][model_name]['overall_status'] = 'synced'
                results['summary']['fully_synced'] += 1
            elif structure_result['has_issues'] or data_result['has_issues']:
                results['models'][model_name]['overall_status'] = 'issues'
                if structure_result['has_issues']:
                    results['summary']['structure_issues'] += 1
                if data_result['has_issues']:
                    results['summary']['data_issues'] += 1
                
                if data_result['sync_status'] == 'synced':
                    results['summary']['partially_synced'] += 1
                else:
                    results['summary']['not_synced'] += 1
        
        return results

    def _display_results(self, results, action):
        """Display validation results"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"{action.upper()} RESULTS")
        self.stdout.write("="*60)
        
        if action == 'validate':
            self._display_full_validation_results(results)
        elif action == 'structure':
            self._display_structure_results(results)
        elif action == 'data':
            self._display_data_results(results)
        elif action == 'report':
            self._display_report_results(results)

    def _display_full_validation_results(self, results):
        """Display full validation results"""
        summary = results['summary']
        
        self.stdout.write(f"Models Validated: {summary['models_validated']}/{results['total_models']}")
        self.stdout.write(f"Structure Issues: {summary['structure_issues']}")
        self.stdout.write(f"Data Issues: {summary['data_issues']}")
        
        if self.detailed:
            self._display_detailed_results(results)

    def _display_structure_results(self, results):
        """Display structure validation results"""
        summary = results['summary']
        
        self.stdout.write(f"Models with Structure Issues: {summary['structure_issues']}/{results['total_models']}")
        
        if self.detailed:
            for model_name, result in results['structure_results'].items():
                if result['has_issues']:
                    self.stdout.write(f"\n{model_name}:")
                    for issue in result['issues']:
                        self.stdout.write(f"  - {issue}")

    def _display_data_results(self, results):
        """Display data validation results"""
        summary = results['summary']
        
        self.stdout.write(f"Models with Data Issues: {summary['data_issues']}/{results['total_models']}")
        
        if self.detailed:
            for model_name, result in results['data_results'].items():
                if result['has_issues']:
                    self.stdout.write(f"\n{model_name}:")
                    self.stdout.write(f"  Status: {result['sync_status']}")
                    for issue in result['issues']:
                        self.stdout.write(f"  - {issue}")

    def _display_report_results(self, results):
        """Display comprehensive report results"""
        summary = results['summary']
        
        self.stdout.write(f"Total Models: {summary['total_models']}")
        self.stdout.write(f"Fully Synced: {summary['fully_synced']}")
        self.stdout.write(f"Partially Synced: {summary['partially_synced']}")
        self.stdout.write(f"Not Synced: {summary['not_synced']}")
        self.stdout.write(f"Structure Issues: {summary['structure_issues']}")
        self.stdout.write(f"Data Issues: {summary['data_issues']}")
        
        sync_percentage = (summary['fully_synced'] / summary['total_models']) * 100
        self.stdout.write(f"Sync Status: {sync_percentage:.1f}%")
        
        if self.detailed:
            self._display_detailed_report(results)

    def _display_detailed_results(self, results):
        """Display detailed validation results"""
        self.stdout.write("\nDetailed Results:")
        
        for model_name in results.get('structure_results', {}):
            structure_result = results['structure_results'][model_name]
            data_result = results['data_results'][model_name]
            
            if structure_result['has_issues'] or data_result['has_issues']:
                self.stdout.write(f"\n{model_name}:")
                
                if structure_result['has_issues']:
                    self.stdout.write("  Structure Issues:")
                    for issue in structure_result['issues']:
                        self.stdout.write(f"    - {issue}")
                
                if data_result['has_issues']:
                    self.stdout.write("  Data Issues:")
                    for issue in data_result['issues']:
                        self.stdout.write(f"    - {issue}")

    def _display_detailed_report(self, results):
        """Display detailed report results"""
        self.stdout.write("\nDetailed Report:")
        
        for model_name, model_data in results['models'].items():
            if model_data['overall_status'] != 'synced':
                self.stdout.write(f"\n{model_name} ({model_data['overall_status']}):")
                
                if model_data['structure']['has_issues']:
                    self.stdout.write("  Structure Issues:")
                    for issue in model_data['structure']['issues']:
                        self.stdout.write(f"    - {issue}")
                
                if model_data['data']['has_issues']:
                    self.stdout.write("  Data Issues:")
                    for issue in model_data['data']['issues']:
                        self.stdout.write(f"    - {issue}")

    def _save_report(self, results, output_file):
        """Save validation report to file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.stdout.write(self.style.SUCCESS(f"✓ Report saved to {output_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to save report: {e}"))
