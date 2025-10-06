from rest_framework import serializers
from django.db import transaction
from products.models import Product
from .models import RMStockBalance, RawMaterial


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.SerializerMethodField()
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    finishing_display = serializers.CharField(source='get_finishing_display', read_only=True)
    available_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'material_code', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'thickness_mm', 'finishing', 'finishing_display', 'weight_kg', 'available_quantity',
            'length_mm', 'breadth_mm', 'quantity'
        ]
        read_only_fields = fields
    
    def get_material_name_display(self, obj):  # pragma: no cover - simple accessor
        """Provide a consistent display label for material name"""
        return obj.material_name

    def get_available_quantity(self, obj):
        """Get available quantity from RMStockBalance"""
        stock_balance = RMStockBalance.objects.filter(raw_material=obj).first()
        if stock_balance:
            return float(stock_balance.available_quantity)
        return 0.0


class ProductListSerializer(serializers.ModelSerializer):
    """Product serializer for list view with stock balance"""
    material_details = RawMaterialBasicSerializer(source='material', read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    spring_type_display = serializers.CharField(source='get_spring_type_display', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    stock_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type', 
            'product_type_display', 'spring_type', 'spring_type_display',
            'material_details', 'customer_name', 'customer_id', 'stock_balance', 
            'grams_per_product', 'length_mm', 'breadth_mm',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_stock_balance(self, obj):
        """Get stock balance for the product"""
        try:
            stock_balance = obj.stock_balances.first()
            if stock_balance:
                return {
                    'available_quantity': stock_balance.available_quantity,
                    'last_updated': stock_balance.last_updated
                }
            return {
                'available_quantity': 0,
                'last_updated': None
            }
        except:
            return {
                'available_quantity': 0,
                'last_updated': None
            }


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Product serializer for create/update operations"""
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type', 
            'spring_type', 'material', 'customer_c_id', 'grams_per_product',
            'length_mm', 'breadth_mm'
        ]
        read_only_fields = ['id']
    
    def validate_internal_product_code(self, value):
        """Validate internal product code uniqueness"""
        if value:
            instance = getattr(self, 'instance', None)
            if instance:
                # Update case - exclude current instance
                if Product.objects.filter(internal_product_code=value).exclude(id=instance.id).exists():
                    raise serializers.ValidationError("Internal product code already exists.")
            else:
                # Create case
                if Product.objects.filter(internal_product_code=value).exists():
                    raise serializers.ValidationError("Internal product code already exists.")
        return value
    
    def validate_product_code(self, value):
        """Validate product code uniqueness"""
        instance = getattr(self, 'instance', None)
        if instance:
            # Update case - exclude current instance
            if Product.objects.filter(product_code=value).exclude(id=instance.id).exists():
                raise serializers.ValidationError("Product code already exists.")
        else:
            # Create case
            if Product.objects.filter(product_code=value).exists():
                raise serializers.ValidationError("Product code already exists.")
        return value
    
    def create(self, validated_data):
        """Create product with audit trail"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class RMStockBalanceSerializer(serializers.ModelSerializer):
    """RMStockBalance serializer for CRUD operations"""
    raw_material_details = RawMaterialBasicSerializer(source='raw_material', read_only=True)
    material_code = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = RMStockBalance
        fields = [
            'id', 'raw_material', 'raw_material_details', 'material_code',
            'available_quantity', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def validate_available_quantity(self, value):
        """Validate available quantity is not negative"""
        if value < 0:
            raise serializers.ValidationError("Available quantity cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create or update stock balance using update_or_create"""
        material_code = validated_data.pop('material_code', None)
        
        if material_code:
            try:
                raw_material = RawMaterial.objects.only("id").get(material_code=material_code)
                validated_data['raw_material'] = raw_material
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError({"material_code": "Raw material with this code does not exist."})
        
        raw_material = validated_data['raw_material']
        available_quantity = validated_data['available_quantity']
        
        # Use update_or_create for upsert behavior
        stock_balance, created = RMStockBalance.objects.update_or_create(
            raw_material=raw_material,
            defaults={'available_quantity': available_quantity}
        )
        
        return stock_balance
    
    def update(self, instance, validated_data):
        """Update stock balance"""
        material_code = validated_data.pop('material_code', None)
        
        if material_code:
            try:
                raw_material = RawMaterial.objects.only("id").get(material_code=material_code)
                validated_data['raw_material'] = raw_material
            except RawMaterial.DoesNotExist:
                raise serializers.ValidationError({"material_code": "Raw material with this code does not exist."})
        
        return super().update(instance, validated_data)


class RMStockBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for bulk stock balance updates using material_code"""
    material_code = serializers.CharField(max_length=120)
    available_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=0)
    
    def validate_material_code(self, value):
        """Validate that raw material exists"""
        try:
            RawMaterial.objects.only("id").get(material_code=value)
        except RawMaterial.DoesNotExist:
            raise serializers.ValidationError("Raw material with this code does not exist.")
        return value


class ProductStockDashboardSerializer(serializers.ModelSerializer):
    """Combined serializer for RM Store dashboard showing products with stock"""
    material = RawMaterialBasicSerializer(read_only=True)
    material_name = serializers.CharField(read_only=True)
    material_type_display = serializers.CharField(read_only=True)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    spring_type_display = serializers.CharField(source='get_spring_type_display', read_only=True)
    customer_name = serializers.CharField(source='customer_c_id.name', read_only=True)
    customer_id = serializers.CharField(source='customer_c_id.c_id', read_only=True)
    stock_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'internal_product_code', 'product_code', 'product_type',
            'product_type_display', 'spring_type', 'spring_type_display',
            'material', 'material_name', 'material_type_display', 'customer_name', 
            'customer_id', 'stock_info'
        ]
    
    def get_stock_info(self, obj):
        """Get comprehensive stock information from material's stock balance"""
        try:
            # Access stock balance through the material relationship
            if obj.material and hasattr(obj.material, 'stock_balances'):
                stock_balance = obj.material.stock_balances.first()
                if stock_balance:
                    return {
                        'available_quantity': stock_balance.available_quantity,
                        'last_updated': stock_balance.last_updated,
                        'stock_status': 'in_stock' if stock_balance.available_quantity > 0 else 'out_of_stock'
                    }
            return {
                'available_quantity': 0,
                'last_updated': None,
                'stock_status': 'no_stock_record'
            }
        except Exception as e:
            return {
                'available_quantity': 0,
                'last_updated': None,
                'stock_status': 'error'
            }
