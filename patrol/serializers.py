from rest_framework import serializers
from .models import PatrolDuty, PatrolUpload, PatrolAlert
from authentication.models import CustomUser
from django.utils import timezone
from datetime import timedelta


class PatrolUserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for patrol assignments"""
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']


class PatrolDutyListSerializer(serializers.ModelSerializer):
    """List serializer for patrol duties"""
    patrol_user_name = serializers.CharField(source='patrol_user.full_name', read_only=True)
    patrol_user_email = serializers.EmailField(source='patrol_user.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_ending_soon = serializers.BooleanField(read_only=True)
    process_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PatrolDuty
        fields = [
            'id', 'patrol_user', 'patrol_user_name', 'patrol_user_email',
            'created_by', 'created_by_name', 'process_names', 'process_count',
            'frequency_hours', 'shift_start_time', 'shift_end_time', 'shift_type',
            'start_date', 'end_date', 'status', 'remarks',
            'is_active', 'is_ending_soon',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_process_count(self, obj):
        return len(obj.process_names) if obj.process_names else 0


class PatrolDutyDetailSerializer(serializers.ModelSerializer):
    """Detail serializer with nested uploads"""
    patrol_user_detail = PatrolUserSerializer(source='patrol_user', read_only=True)
    created_by_detail = PatrolUserSerializer(source='created_by', read_only=True)
    expected_upload_slots = serializers.SerializerMethodField()
    upload_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = PatrolDuty
        fields = [
            'id', 'patrol_user', 'patrol_user_detail',
            'created_by', 'created_by_detail',
            'process_names', 'frequency_hours',
            'shift_start_time', 'shift_end_time', 'shift_type',
            'start_date', 'end_date', 'status', 'remarks',
            'expected_upload_slots', 'upload_summary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_expected_upload_slots(self, obj):
        """Get expected time slots for today"""
        return [slot.strftime('%H:%M') for slot in obj.get_expected_upload_slots()]
    
    def get_upload_summary(self, obj):
        """Get summary of uploads"""
        uploads = obj.uploads.all()
        return {
            'total': uploads.count(),
            'submitted': uploads.filter(status='submitted').count(),
            'missed': uploads.filter(status='missed').count(),
            'pending': uploads.filter(status='pending').count(),
        }


class PatrolDutyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating patrol duties"""
    
    class Meta:
        model = PatrolDuty
        fields = [
            'id', 'patrol_user', 'process_names', 'frequency_hours',
            'shift_start_time', 'shift_end_time', 'shift_type',
            'start_date', 'end_date', 'status', 'remarks'
        ]
    
    def validate(self, data):
        """Validate patrol duty data"""
        # Validate date range
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        # Validate frequency
        if data.get('frequency_hours'):
            if data['frequency_hours'] < 1 or data['frequency_hours'] > 12:
                raise serializers.ValidationError({
                    'frequency_hours': 'Frequency must be between 1 and 12 hours'
                })
        
        # Validate process names
        if data.get('process_names'):
            if not isinstance(data['process_names'], list) or len(data['process_names']) == 0:
                raise serializers.ValidationError({
                    'process_names': 'At least one process must be assigned'
                })
        
        return data
    
    def create(self, validated_data):
        """Create patrol duty and initialize upload slots"""
        duty = super().create(validated_data)
        
        # Generate upload slots for the duty period
        self._generate_upload_slots(duty)
        
        return duty
    
    def _generate_upload_slots(self, duty):
        """Generate PatrolUpload records for all expected time slots"""
        from datetime import date, timedelta
        
        current_date = duty.start_date
        while current_date <= duty.end_date:
            # Get time slots for this date
            time_slots = duty.get_expected_upload_slots(current_date)
            
            # Create upload records for each process and time slot
            for process_name in duty.process_names:
                for time_slot in time_slots:
                    PatrolUpload.objects.get_or_create(
                        duty=duty,
                        process_name=process_name,
                        scheduled_date=current_date,
                        scheduled_time=time_slot,
                        defaults={
                            'status': 'pending'
                        }
                    )
            
            current_date += timedelta(days=1)


class PatrolUploadSerializer(serializers.ModelSerializer):
    """Serializer for patrol uploads"""
    patrol_user_name = serializers.CharField(source='duty.patrol_user.full_name', read_only=True)
    process_name = serializers.CharField(read_only=True)
    scheduled_date = serializers.DateField(read_only=True)
    scheduled_time = serializers.TimeField(read_only=True)
    is_upload_window_open = serializers.BooleanField(read_only=True)
    can_reupload = serializers.BooleanField(read_only=True)
    is_locked = serializers.BooleanField(read_only=True)
    qc_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PatrolUpload
        fields = [
            'id', 'duty', 'patrol_user_name', 'process_name',
            'scheduled_date', 'scheduled_time',
            'qc_image', 'qc_image_url', 'upload_timestamp',
            'status', 'patrol_remarks',
            'is_reuploaded', 'first_upload_time', 'reupload_deadline',
            'is_upload_window_open', 'can_reupload', 'is_locked',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'upload_timestamp', 'first_upload_time', 'reupload_deadline',
            'is_reuploaded', 'created_at', 'updated_at'
        ]
    
    def get_qc_image_url(self, obj):
        """Get full URL for QC image"""
        if obj.qc_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qc_image.url)
        return None
    
    def validate(self, data):
        """Validate upload data"""
        upload = self.instance
        
        if upload:
            # Check if upload window is open
            if not upload.is_upload_window_open and upload.status == 'pending':
                raise serializers.ValidationError(
                    'Upload window is not open. You can only upload 15 minutes before to 30 minutes after the scheduled time.'
                )
            
            # Check if upload is locked
            if upload.is_locked:
                raise serializers.ValidationError(
                    'This upload is locked and cannot be modified.'
                )
            
            # Check reupload permission
            if upload.first_upload_time and not upload.can_reupload:
                raise serializers.ValidationError(
                    'Reupload window has expired (10 minutes from first upload).'
                )
        
        return data


class PatrolUploadSubmitSerializer(serializers.Serializer):
    """Serializer for submitting QC image upload"""
    qc_image = serializers.ImageField(required=True)
    patrol_remarks = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    
    def validate_qc_image(self, value):
        """Validate image file"""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Image file size must not exceed 10MB')
        
        # Check file format
        allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if value.content_type not in allowed_formats:
            raise serializers.ValidationError('Only JPEG, PNG, and WebP images are allowed')
        
        return value


class PatrolAlertSerializer(serializers.ModelSerializer):
    """Serializer for patrol alerts"""
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True)
    duty_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = PatrolAlert
        fields = [
            'id', 'duty', 'duty_detail', 'upload',
            'alert_type', 'recipient', 'recipient_name',
            'message', 'is_read', 'is_action_taken',
            'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_duty_detail(self, obj):
        """Get minimal duty details"""
        if obj.duty:
            return {
                'id': obj.duty.id,
                'patrol_user': obj.duty.patrol_user.full_name,
                'start_date': obj.duty.start_date,
                'end_date': obj.duty.end_date,
            }
        return None


class PatrolStatisticsSerializer(serializers.Serializer):
    """Serializer for patrol statistics"""
    active_duties = serializers.IntegerField()
    total_uploads_today = serializers.IntegerField()
    submitted_today = serializers.IntegerField()
    missed_today = serializers.IntegerField()
    pending_today = serializers.IntegerField()
    compliance_rate = serializers.FloatField()

