from rest_framework import serializers
from django.db import transaction
from products.models import Product
from .models import RMStockBalance, RawMaterial


class RawMaterialBasicSerializer(serializers.ModelSerializer):
    """Basic raw material serializer for nested relationships"""
    material_name_display = serializers.CharField(source='get_material_name_display', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)
    finishing_display = serializers.CharField(source='get_finishing_display', read_only=True)
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'material_code', 'material_name', 'material_name_display',
            'material_type', 'material_type_display', 'grade', 'wire_diameter_mm',
            'thickness_mm', 'finishing', 'finishing_display', 'weight_kg', 'quantity'
        ]
        read_only_fields = fields


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
            'spring_type', 'material', 'customer_c_id'
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
    product_details = ProductListSerializer(source='product', read_only=True)
    product_internal_code = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = RMStockBalance
        fields = [
            'id', 'product', 'product_details', 'product_internal_code',
            'available_quantity', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated']
    
    def validate_available_quantity(self, value):
        """Validate available quantity is not negative"""
        if value < 0:
            raise serializers.ValidationError("Available quantity cannot be negative.")
        return value
    
    def create(self, validated_data):
        """Create or update stock balance using bulk_create with conflict handling"""
        product_internal_code = validated_data.pop('product_internal_code', None)
        
        if product_internal_code:
            try:
                product = Product.objects.only("id").get(internal_product_code=product_internal_code)
                validated_data['product'] = product
            except Product.DoesNotExist:
                raise serializers.ValidationError({"product_internal_code": "Product with this internal code does not exist."})
        
        product = validated_data['product']
        available_quantity = validated_data['available_quantity']
        
        # Use bulk_create with update_conflicts for upsert behavior
        stock_balance, created = RMStockBalance.objects.update_or_create(
            product=product,
            defaults={'available_quantity': available_quantity}
        )
        
        return stock_balance
    
    def update(self, instance, validated_data):
        """Update stock balance"""
        product_internal_code = validated_data.pop('product_internal_code', None)
        
        if product_internal_code:
            try:
                product = Product.objects.only("id").get(internal_product_code=product_internal_code)
                validated_data['product'] = product
            except Product.DoesNotExist:
                raise serializers.ValidationError({"product_internal_code": "Product with this internal code does not exist."})
        
        return super().update(instance, validated_data)


class RMStockBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for bulk stock balance updates using internal_product_code"""
    internal_product_code = serializers.CharField(max_length=120)
    available_quantity = serializers.IntegerField(min_value=0)
    
    def validate_internal_product_code(self, value):
        """Validate that product exists"""
        try:
            Product.objects.only("id").get(internal_product_code=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product with this internal code does not exist.")
        return value


class ProductStockDashboardSerializer(serializers.ModelSerializer):
    """Combined serializer for RM Store dashboard showing products with stock"""
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
            'material_name', 'material_type_display', 'customer_name', 
            'customer_id', 'stock_info'
        ]
    
    def get_stock_info(self, obj):
        """Get comprehensive stock information"""
        try:
            stock_balance = obj.stock_balances.first()
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
        except:
            return {
                'available_quantity': 0,
                'last_updated': None,
                'stock_status': 'error'
            }
