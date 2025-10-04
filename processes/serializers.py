from rest_framework import serializers
from .models import Process, SubProcess, ProcessStep, BOM
from inventory.models import RawMaterial


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.CharField(source='get_material_name_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'material_code', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'weight_kg', 'thickness_mm', 'quantity'
        ]
        read_only_fields = fields


class ProcessListSerializer(serializers.ModelSerializer):
    """Optimized serializer for Process list view"""
    subprocess_count = serializers.SerializerMethodField()
    process_step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Process
        fields = [
            'id', 'name', 'code', 'description', 'is_active', 
            'created_at', 'updated_at', 'subprocess_count', 'process_step_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_subprocess_count(self, obj):
        return obj.subprocesses.count()
    
    def get_process_step_count(self, obj):
        return obj.process_steps.count()


class ProcessDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Process create/update/detail view"""
    subprocesses = serializers.SerializerMethodField()
    process_steps = serializers.SerializerMethodField()
    subprocess_count = serializers.SerializerMethodField()
    process_step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Process
        fields = [
            'id', 'name', 'code', 'description', 'is_active', 
            'created_at', 'updated_at', 'subprocesses', 'process_steps',
            'subprocess_count', 'process_step_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_subprocesses(self, obj):
        from .serializers import SubProcessListSerializer
        return SubProcessListSerializer(obj.subprocesses.all(), many=True).data
    
    def get_process_steps(self, obj):
        from .serializers import ProcessStepListSerializer
        return ProcessStepListSerializer(obj.process_steps.all(), many=True).data
    
    def get_subprocess_count(self, obj):
        return obj.subprocesses.count()
    
    def get_process_step_count(self, obj):
        return obj.process_steps.count()


class SubProcessListSerializer(serializers.ModelSerializer):
    """Optimized serializer for SubProcess list view"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    process_code = serializers.IntegerField(source='process.code', read_only=True)
    process_step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SubProcess
        fields = [
            'id', 'name', 'description', 'process', 'process_name', 
            'process_code', 'created_at', 'process_step_count'
        ]
        read_only_fields = ['created_at']
    
    def get_process_step_count(self, obj):
        return obj.process_steps.count()


class SubProcessDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for SubProcess create/update/detail view"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    process_code = serializers.IntegerField(source='process.code', read_only=True)
    process_steps = serializers.SerializerMethodField()
    process_step_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SubProcess
        fields = [
            'id', 'name', 'description', 'process', 'process_name', 
            'process_code', 'created_at', 'process_steps', 'process_step_count'
        ]
        read_only_fields = ['created_at']
    
    def get_process_steps(self, obj):
        from .serializers import ProcessStepListSerializer
        return ProcessStepListSerializer(obj.process_steps.all(), many=True).data
    
    def get_process_step_count(self, obj):
        return obj.process_steps.count()


class ProcessStepListSerializer(serializers.ModelSerializer):
    """Optimized serializer for ProcessStep list view"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    subprocess_name = serializers.CharField(source='subprocess.name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    
    class Meta:
        model = ProcessStep
        fields = [
            'id', 'step_name', 'step_code', 'process', 'process_name',
            'subprocess', 'subprocess_name', 'sequence_order', 'description',
            'created_at', 'full_path'
        ]
        read_only_fields = ['created_at', 'full_path']


class ProcessStepDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ProcessStep create/update/detail view"""
    process_name = serializers.CharField(source='process.name', read_only=True)
    subprocess_name = serializers.CharField(source='subprocess.name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    bom_items = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessStep
        fields = [
            'id', 'step_name', 'step_code', 'process', 'process_name',
            'subprocess', 'subprocess_name', 'sequence_order', 'description',
            'created_at', 'full_path', 'bom_items'
        ]
        read_only_fields = ['created_at', 'full_path']
    
    def get_bom_items(self, obj):
        from .serializers import BOMListSerializer
        return BOMListSerializer(obj.bom_set.all(), many=True).data
    
    def validate(self, data):
        """Validate that subprocess belongs to the selected process"""
        subprocess = data.get('subprocess')
        process = data.get('process')
        
        if subprocess and process and subprocess.process != process:
            raise serializers.ValidationError(
                "Subprocess must belong to the selected process"
            )
        
        return data


class BOMListSerializer(serializers.ModelSerializer):
    """Optimized serializer for BOM list view"""
    process_step_name = serializers.CharField(source='process_step.step_name', read_only=True)
    process_step_full_path = serializers.CharField(source='process_step.full_path', read_only=True)
    material = RawMaterialBasicSerializer(read_only=True)
    main_process_name = serializers.CharField(source='main_process.name', read_only=True)
    subprocess_name = serializers.CharField(source='subprocess.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = BOM
        fields = [
            'id', 'product_code', 'type', 'type_display', 'process_step',
            'process_step_name', 'process_step_full_path', 'material',
            'main_process_name', 'subprocess_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BOMDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for BOM create/update/detail view"""
    process_step_name = serializers.CharField(source='process_step.step_name', read_only=True)
    process_step_full_path = serializers.CharField(source='process_step.full_path', read_only=True)
    material = RawMaterialBasicSerializer(read_only=True)
    main_process_name = serializers.CharField(source='main_process.name', read_only=True)
    subprocess_name = serializers.CharField(source='subprocess.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    # Write-only field for creation/update
    material_code = serializers.CharField(write_only=True)
    
    class Meta:
        model = BOM
        fields = [
            'id', 'product_code', 'type', 'type_display', 'process_step',
            'process_step_name', 'process_step_full_path', 'material', 'material_code',
            'main_process_name', 'subprocess_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create BOM with material reference"""
        material_code = validated_data.pop('material_code')
        
        try:
            material = RawMaterial.objects.get(material_code=material_code)
        except RawMaterial.DoesNotExist:
            raise serializers.ValidationError("Invalid material code reference")
        
        validated_data['material'] = material
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Update BOM with material reference"""
        if 'material_code' in validated_data:
            material_code = validated_data.pop('material_code')
            try:
                material = RawMaterial.objects.get(material_code=material_code)
                validated_data['material'] = material
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError("Invalid material code reference")
        
        return super().update(instance, validated_data)


# Utility serializers for dropdown/select options
class ProcessDropdownSerializer(serializers.ModelSerializer):
    """Serializer for process dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Process
        fields = ['id', 'name', 'code', 'display_name', 'is_active']
    
    def get_display_name(self, obj):
        return f"{obj.name} ({obj.code})"


class SubProcessDropdownSerializer(serializers.ModelSerializer):
    """Serializer for subprocess dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SubProcess
        fields = ['id', 'name', 'process', 'display_name']
    
    def get_display_name(self, obj):
        return f"{obj.process.name} -> {obj.name}"


class ProcessStepDropdownSerializer(serializers.ModelSerializer):
    """Serializer for process step dropdown options"""
    display_name = serializers.CharField(source='full_path', read_only=True)
    
    class Meta:
        model = ProcessStep
        fields = ['id', 'step_name', 'step_code', 'process', 'subprocess', 'display_name']


class RawMaterialDropdownSerializer(serializers.ModelSerializer):
    """Serializer for raw material dropdown options"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = ['id', 'material_code', 'material_name', 'material_type', 'grade', 'display_name']
    
    def get_display_name(self, obj):
        return str(obj)  # Uses the __str__ method from the model
