"""
Management command to check supervisor attendance and auto-assign backup if needed
Run daily at check-in deadline time (e.g., 9:15 AM) via cron job

Usage:
    python manage.py check_supervisor_attendance
    python manage.py check_supervisor_attendance --date=2025-10-12  # For specific date
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, date, time
import logging

from processes.models import WorkCenterMaster, DailySupervisorStatus, SupervisorActivityLog
from authentication.models import LoginSession

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check supervisor attendance and auto-assign backup if needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to check (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate daily status even if it exists',
        )

    def handle(self, *args, **options):
        # Get date to process
        if options['date']:
            try:
                check_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            check_date = timezone.now().date()
        
        force = options.get('force', False)
        
        self.stdout.write(f"Checking supervisor attendance for {check_date}...")
        
        # Get all active work centers
        work_centers = WorkCenterMaster.objects.filter(is_active=True).select_related(
            'work_center', 'default_supervisor', 'backup_supervisor'
        )
        
        if not work_centers.exists():
            self.stdout.write(self.style.WARNING('No active work centers found'))
            return
        
        created_count = 0
        updated_count = 0
        backup_assigned_count = 0
        
        for wc_master in work_centers:
            try:
                # Check if status already exists for this date
                status, created = DailySupervisorStatus.objects.get_or_create(
                    date=check_date,
                    work_center=wc_master.work_center,
                    defaults={
                        'default_supervisor': wc_master.default_supervisor,
                        'active_supervisor': wc_master.default_supervisor,  # Initially default
                        'is_present': False,
                        'check_in_deadline': wc_master.check_in_deadline,
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created status for {wc_master.work_center.name}'
                        )
                    )
                elif force:
                    # Force update
                    status.default_supervisor = wc_master.default_supervisor
                    status.check_in_deadline = wc_master.check_in_deadline
                    status.save()
                    updated_count += 1
                
                # Check if default supervisor has logged in before deadline
                login_time = self._get_supervisor_login_time(
                    wc_master.default_supervisor,
                    check_date
                )
                
                if login_time:
                    # Compare login time with deadline
                    deadline_dt = datetime.combine(check_date, wc_master.check_in_deadline)
                    login_dt = datetime.combine(check_date, login_time)
                    
                    if login_dt <= deadline_dt:
                        # Supervisor logged in on time
                        status.is_present = True
                        status.login_time = login_time
                        status.active_supervisor = wc_master.default_supervisor
                        status.save()
                        
                        self.stdout.write(
                            f'  ✓ {wc_master.work_center.name}: '
                            f'{wc_master.default_supervisor.get_full_name()} '
                            f'logged in at {login_time} (on time)'
                        )
                    else:
                        # Supervisor logged in but late
                        status.is_present = False
                        status.login_time = login_time
                        status.active_supervisor = wc_master.backup_supervisor
                        status.save()
                        backup_assigned_count += 1
                        
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠ {wc_master.work_center.name}: '
                                f'{wc_master.default_supervisor.get_full_name()} '
                                f'logged in late at {login_time}. '
                                f'Backup assigned: {wc_master.backup_supervisor.get_full_name()}'
                            )
                        )
                else:
                    # No login found - assign backup
                    status.is_present = False
                    status.login_time = None
                    status.active_supervisor = wc_master.backup_supervisor
                    status.save()
                    backup_assigned_count += 1
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ✗ {wc_master.work_center.name}: '
                            f'{wc_master.default_supervisor.get_full_name()} '
                            f'not logged in. '
                            f'Backup assigned: {wc_master.backup_supervisor.get_full_name()}'
                        )
                    )
                
                # Initialize activity log for this work center
                self._initialize_activity_log(status)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing {wc_master.work_center.name}: {str(e)}'
                    )
                )
                logger.error(f'Error in check_supervisor_attendance: {str(e)}', exc_info=True)
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(f'Date: {check_date}')
        self.stdout.write(f'Total work centers: {work_centers.count()}')
        self.stdout.write(f'New statuses created: {created_count}')
        self.stdout.write(f'Existing statuses updated: {updated_count}')
        self.stdout.write(f'Backup supervisors assigned: {backup_assigned_count}')
        
        self.stdout.write(self.style.SUCCESS('\nSupervisor attendance check completed!'))
    
    def _get_supervisor_login_time(self, supervisor, check_date):
        """
        Get the first login time for supervisor on the given date
        Uses the LoginSession model
        """
        # Get the first login session for this supervisor on this date
        login_session = LoginSession.objects.filter(
            user=supervisor,
            login_time__date=check_date
        ).order_by('login_time').first()
        
        if login_session:
            return login_session.login_time.time()
        
        return None
    
    def _initialize_activity_log(self, daily_status):
        """
        Initialize or update supervisor activity log for the day
        """
        try:
            log, created = SupervisorActivityLog.objects.get_or_create(
                date=daily_status.date,
                work_center=daily_status.work_center,
                active_supervisor=daily_status.active_supervisor,
                defaults={
                    'mos_handled': 0,
                    'total_operations': 0,
                    'operations_completed': 0,
                    'operations_in_progress': 0,
                    'total_processing_time_minutes': 0,
                }
            )
            
            if created:
                logger.info(
                    f'Initialized activity log for {daily_status.work_center.name} - '
                    f'{daily_status.active_supervisor.get_full_name()}'
                )
        except Exception as e:
            logger.error(f'Error initializing activity log: {str(e)}', exc_info=True)

