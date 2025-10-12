from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Process, SubProcess, ProcessStep, BOM,
    WorkCenterMaster, DailySupervisorStatus, SupervisorActivityLog
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = fields


class ProcessBasicSerializer(serializers.ModelSerializer):
    """Basic process serializer"""
    class Meta:
        model = Process
        fields = ['id', 'name', 'code', 'is_active']
        read_only_fields = fields


class WorkCenterMasterListSerializer(serializers.ModelSerializer):
    """Serializer for Work Center Master list view"""
    work_center = ProcessBasicSerializer(read_only=True)
    default_supervisor = UserBasicSerializer(read_only=True)
    backup_supervisor = UserBasicSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    updated_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = WorkCenterMaster
        fields = [
            'id', 'work_center', 'default_supervisor', 'backup_supervisor',
            'check_in_deadline', 'is_active', 'created_at', 'created_by',
            'updated_at', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at']


class WorkCenterMasterDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Work Center Master create/update"""
    work_center_details = ProcessBasicSerializer(source='work_center', read_only=True)
    default_supervisor_details = UserBasicSerializer(source='default_supervisor', read_only=True)
    backup_supervisor_details = UserBasicSerializer(source='backup_supervisor', read_only=True)
    
    # Write-only fields for creation/update
    work_center_id = serializers.IntegerField(write_only=True)
    default_supervisor_id = serializers.IntegerField(write_only=True)
    backup_supervisor_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = WorkCenterMaster
        fields = [
            'id', 'work_center', 'work_center_id', 'work_center_details',
            'default_supervisor', 'default_supervisor_id', 'default_supervisor_details',
            'backup_supervisor', 'backup_supervisor_id', 'backup_supervisor_details',
            'check_in_deadline', 'is_active', 'created_at', 'created_by',
            'updated_at', 'updated_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def validate(self, data):
        """Validate that default and backup supervisors are different"""
        default_id = data.get('default_supervisor_id')
        backup_id = data.get('backup_supervisor_id')
        
        if default_id and backup_id and default_id == backup_id:
            raise serializers.ValidationError(
                "Default and backup supervisors must be different users"
            )
        
        return data
    
    def create(self, validated_data):
        """Create Work Center Master"""
        work_center_id = validated_data.pop('work_center_id')
        default_supervisor_id = validated_data.pop('default_supervisor_id')
        backup_supervisor_id = validated_data.pop('backup_supervisor_id')
        
        try:
            work_center = Process.objects.get(id=work_center_id)
            default_supervisor = User.objects.get(id=default_supervisor_id)
            backup_supervisor = User.objects.get(id=backup_supervisor_id)
        except (Process.DoesNotExist, User.DoesNotExist) as e:
            raise serializers.ValidationError(f"Invalid reference: {str(e)}")
        
        # Check if work center master already exists
        if WorkCenterMaster.objects.filter(work_center=work_center).exists():
            raise serializers.ValidationError(
                f"Work Center Master already exists for {work_center.name}"
            )
        
        validated_data.update({
            'work_center': work_center,
            'default_supervisor': default_supervisor,
            'backup_supervisor': backup_supervisor,
            'created_by': self.context['request'].user
        })
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update Work Center Master"""
        if 'work_center_id' in validated_data:
            work_center_id = validated_data.pop('work_center_id')
            try:
                instance.work_center = Process.objects.get(id=work_center_id)
            except Process.DoesNotExist:
                raise serializers.ValidationError("Invalid work center reference")
        
        if 'default_supervisor_id' in validated_data:
            supervisor_id = validated_data.pop('default_supervisor_id')
            try:
                instance.default_supervisor = User.objects.get(id=supervisor_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid default supervisor reference")
        
        if 'backup_supervisor_id' in validated_data:
            supervisor_id = validated_data.pop('backup_supervisor_id')
            try:
                instance.backup_supervisor = User.objects.get(id=supervisor_id)
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid backup supervisor reference")
        
        instance.updated_by = self.context['request'].user
        
        return super().update(instance, validated_data)


class DailySupervisorStatusSerializer(serializers.ModelSerializer):
    """Serializer for Daily Supervisor Status"""
    work_center = ProcessBasicSerializer(read_only=True)
    work_center_name = serializers.CharField(source='work_center.name', read_only=True)
    default_supervisor = UserBasicSerializer(read_only=True)
    default_supervisor_name = serializers.CharField(source='default_supervisor.get_full_name', read_only=True)
    active_supervisor = UserBasicSerializer(read_only=True)
    active_supervisor_name = serializers.CharField(source='active_supervisor.get_full_name', read_only=True)
    manually_updated_by = UserBasicSerializer(read_only=True)
    status_color = serializers.ReadOnlyField()
    
    class Meta:
        model = DailySupervisorStatus
        fields = [
            'id', 'date', 'work_center', 'work_center_name', 'default_supervisor',
            'default_supervisor_name', 'is_present', 'active_supervisor',
            'active_supervisor_name', 'login_time', 'check_in_deadline',
            'manually_updated', 'manually_updated_by', 'manually_updated_at',
            'manual_update_reason', 'status_color', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'login_time', 'manually_updated',
            'manually_updated_by', 'manually_updated_at'
        ]


class DailySupervisorStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for manual supervisor status update"""
    active_supervisor_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DailySupervisorStatus
        fields = ['active_supervisor_id', 'manual_update_reason']
    
    def update(self, instance, validated_data):
        """Manually update active supervisor"""
        supervisor_id = validated_data.pop('active_supervisor_id')
        
        try:
            supervisor = User.objects.get(id=supervisor_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid supervisor reference")
        
        instance.active_supervisor = supervisor
        instance.manually_updated = True
        instance.manually_updated_by = self.context['request'].user
        instance.manually_updated_at = timezone.now()
        instance.manual_update_reason = validated_data.get('manual_update_reason', '')
        instance.save()
        
        return instance


class SupervisorActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for Supervisor Activity Log"""
    work_center = ProcessBasicSerializer(read_only=True)
    work_center_name = serializers.CharField(source='work_center.name', read_only=True)
    active_supervisor = UserBasicSerializer(read_only=True)
    active_supervisor_name = serializers.CharField(source='active_supervisor.get_full_name', read_only=True)
    
    class Meta:
        model = SupervisorActivityLog
        fields = [
            'id', 'date', 'work_center', 'work_center_name', 'active_supervisor',
            'active_supervisor_name', 'mos_handled', 'total_operations',
            'operations_completed', 'operations_in_progress',
            'total_processing_time_minutes', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
