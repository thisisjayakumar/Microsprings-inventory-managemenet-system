from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from patrol.models import PatrolDuty, PatrolUpload, PatrolAlert


class Command(BaseCommand):
    help = 'Check and create patrol alerts (missed uploads, duty ending soon)'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking patrol alerts...')
        
        # Check for missed uploads
        self.check_missed_uploads()
        
        # Check for duties ending soon (8hr and 4hr alerts)
        self.check_duties_ending_soon()
        
        # Auto-complete ended duties
        self.auto_complete_duties()
        
        self.stdout.write(self.style.SUCCESS('Patrol alerts check completed'))
    
    def check_missed_uploads(self):
        """Mark uploads as missed if not submitted within window"""
        now = timezone.now()
        today = date.today()
        
        # Get pending uploads where window has closed
        pending_uploads = PatrolUpload.objects.filter(
            status='pending',
            scheduled_date=today,
            duty__status='active'
        )
        
        missed_count = 0
        for upload in pending_uploads:
            if not upload.is_upload_window_open:
                upload.mark_as_missed()
                missed_count += 1
                
                # Create alert for missed upload
                PatrolAlert.objects.get_or_create(
                    upload=upload,
                    alert_type='upload_missed',
                    recipient=upload.duty.patrol_user,
                    defaults={
                        'message': f"Missed QC upload for {upload.process_name} at {upload.scheduled_time.strftime('%H:%M')} on {upload.scheduled_date}"
                    }
                )
        
        if missed_count > 0:
            self.stdout.write(f'Marked {missed_count} uploads as missed')
    
    def check_duties_ending_soon(self):
        """Create alerts for duties ending soon"""
        now = timezone.now()
        
        active_duties = PatrolDuty.objects.filter(status='active')
        
        for duty in active_duties:
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(duty.end_date, duty.shift_end_time)
            )
            
            time_remaining = end_datetime - now
            
            # 8-hour alert
            if timedelta(hours=7, minutes=45) <= time_remaining <= timedelta(hours=8, minutes=15):
                # Check if alert already sent
                alert_exists = PatrolAlert.objects.filter(
                    duty=duty,
                    alert_type='duty_ending_8hr',
                    created_at__gte=now - timedelta(hours=1)
                ).exists()
                
                if not alert_exists:
                    PatrolAlert.objects.create(
                        duty=duty,
                        alert_type='duty_ending_8hr',
                        recipient=duty.created_by,
                        message=f"{duty.patrol_user.full_name} patrol assignment will complete at {duty.shift_end_time.strftime('%I:%M %p')} today."
                    )
                    self.stdout.write(f'Created 8-hour alert for duty {duty.id}')
            
            # 4-hour alert
            elif timedelta(hours=3, minutes=45) <= time_remaining <= timedelta(hours=4, minutes=15):
                # Check if alert already sent
                alert_exists = PatrolAlert.objects.filter(
                    duty=duty,
                    alert_type='duty_ending_4hr',
                    created_at__gte=now - timedelta(hours=1)
                ).exists()
                
                if not alert_exists:
                    PatrolAlert.objects.create(
                        duty=duty,
                        alert_type='duty_ending_4hr',
                        recipient=duty.created_by,
                        message=f"{duty.patrol_user.full_name} patrol assignment will complete at {duty.shift_end_time.strftime('%I:%M %p')} today."
                    )
                    self.stdout.write(f'Created 4-hour alert for duty {duty.id}')
    
    def auto_complete_duties(self):
        """Auto-complete duties that have ended"""
        completed_count = 0
        
        active_duties = PatrolDuty.objects.filter(status='active')
        
        for duty in active_duties:
            if duty.auto_complete_if_ended():
                completed_count += 1
                
                # Create completion alert
                PatrolAlert.objects.create(
                    duty=duty,
                    alert_type='duty_completed',
                    recipient=duty.created_by,
                    message=f"Patrol duty for {duty.patrol_user.full_name} has been automatically completed (ended on {duty.end_date})."
                )
        
        if completed_count > 0:
            self.stdout.write(f'Auto-completed {completed_count} duties')

