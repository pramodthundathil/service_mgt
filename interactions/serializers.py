# serializers.py - FIXED VERSION
from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Brand, VehicleVariant, Customer, VehicleOnService, ServiceEntry
from index.models import CustomUser, ServiceCenter


# ============= USER SERIALIZERS (Read-Only) =============

class BrandUserSerializer(serializers.ModelSerializer):
    """Read-only serializer for users to view brands"""
    
    image_url = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'image_url', 'variants_count']
        
    def get_image_url(self, obj):
        """Return the appropriate image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url
        
    def get_variants_count(self, obj):
        """Return count of variants for this brand"""
        return obj.brand_variants.count()  # Fixed: was brand_variants_set


class VehicleVariantUserSerializer(serializers.ModelSerializer):
    """Read-only serializer for users to view vehicle variants"""
    
    brand = BrandUserSerializer(read_only=True)
    body_type_display = serializers.CharField(
        source='get_body_type_display', 
        read_only=True
    )
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleVariant
        fields = [
            'id', 
            'brand', 
            'variant_name', 
            'body_type',
            'body_type_display',
            'full_name'
        ]
        
    def get_full_name(self, obj):
        """Return brand name + variant name"""
        return f"{obj.brand.name} {obj.variant_name}"


class VehicleVariantNestedSerializer(serializers.ModelSerializer):
    """Lightweight variant serializer for nesting in brand details"""
    
    body_type_display = serializers.CharField(
        source='get_body_type_display', 
        read_only=True
    )
    
    class Meta:
        model = VehicleVariant
        fields = ['id', 'variant_name', 'body_type', 'body_type_display']


class BrandDetailUserSerializer(serializers.ModelSerializer):
    """Detailed brand serializer with nested variants"""
    
    image_url = serializers.SerializerMethodField()
    variants = VehicleVariantNestedSerializer(
        source='brand_variants',  # Fixed: was brand_variants_set
        many=True, 
        read_only=True
    )
    variants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'image_url', 'variants', 'variants_count']
        
    def get_image_url(self, obj):
        """Return the appropriate image URL"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url
        
    def get_variants_count(self, obj):
        """Return count of variants"""
        return obj.brand_variants.count() 
# ============= ADMIN SERIALIZERS (Full CRUD) =============

class BrandAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for brand management"""
    
    image_display_url = serializers.SerializerMethodField(read_only=True)
    variants_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'image', 'image_url', 'image_display_url', 'variants_count']
        
    def get_image_display_url(self, obj):
        """Return the current image URL for display"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url
        
    def get_variants_count(self, obj):
        """Return count of variants"""
        return obj.brand_variants_set.count()
        
    def validate(self, data):
        """Ensure at least one image source is provided"""
        image = data.get('image')
        image_url = data.get('image_url')
        
        if not image and not image_url:
            raise serializers.ValidationError(
                "Either upload an image or provide an image URL."
            )
        
        return data


class VehicleVariantAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for vehicle variant management"""
    
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    body_type_display = serializers.CharField(
        source='get_body_type_display', 
        read_only=True
    )
    
    class Meta:
        model = VehicleVariant
        fields = [
            'id',
            'brand',
            'brand_name',
            'variant_name',
            'body_type',
            'body_type_display'
        ]
        
    def validate_variant_name(self, value):
        """Clean and validate variant name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Variant name must be at least 2 characters long."
            )
        return value.strip().title()
        
    def validate(self, data):
        """Check for duplicate variants within the same brand"""
        brand = data.get('brand')
        variant_name = data.get('variant_name', '').strip()
        
        queryset = VehicleVariant.objects.filter(
            brand=brand, 
            variant_name__iexact=variant_name
        )
        
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise serializers.ValidationError(
                "A variant with this name already exists for this brand."
            )
        
        return data


# ============= SERVICE CENTER SERIALIZERS =============

class BrandReadOnlySerializer(serializers.ModelSerializer):
    """Read-only serializer for Brand model"""
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'image', 'image_url', 'created_at']
        # FIXED: Use list instead of string
        read_only_fields = ['id', 'name', 'image', 'image_url', 'created_at']


class VehicleVariantReadOnlySerializer(serializers.ModelSerializer):
    """Read-only serializer for VehicleVariant model"""
    
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand_id = serializers.IntegerField(source='brand.id', read_only=True)
    
    class Meta:
        model = VehicleVariant
        fields = ['id', 'brand_id', 'brand_name', 'variant_name', 'body_type', 'created_at']
        # FIXED: Use list instead of '__all__' string
        read_only_fields = ['id', 'brand_id', 'brand_name', 'variant_name', 'body_type', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model with CRUD operations"""
    
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    vehicle_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'service_center', 
            'service_center_name', 'vehicle_count', 'date_added', 'date_updated'
        ]
        # FIXED: Use list instead of string
        read_only_fields = ['id', 'service_center', 'service_center_name', 'vehicle_count', 'date_added', 'date_updated']
    
    def get_vehicle_count(self, obj):
        """Get total number of vehicles for this customer"""
        return obj.customer_vehicles.count()
    
    def validate_phone(self, value):
        """Validate phone number format and uniqueness within service center"""
        if not value.isdigit() or len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits and contain only numbers")
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center:
                existing_customer = Customer.objects.filter(
                    phone=value, 
                    service_center=service_center
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_customer.exists():
                    raise serializers.ValidationError("A customer with this phone number already exists in your service center")
        
        return value
    
    def create(self, validated_data):
        """Create customer with service center from authenticated user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center:
                validated_data['service_center'] = service_center
        return super().create(validated_data)


class VehicleOnServiceSerializer(serializers.ModelSerializer):
    """Serializer for VehicleOnService model with CRUD operations"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_type.variant_name', read_only=True)
    brand_name = serializers.CharField(source='vehicle_type.brand.name', read_only=True)
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    last_service_info = serializers.SerializerMethodField()
    next_service_due = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleOnService
        fields = [
            'id', 'customer', 'customer_name', 'customer_phone', 'vehicle_type', 
            'vehicle_type_name', 'brand_name', 'service_center', 'service_center_name',
            'vehicle_model', 'vehicle_number', 'transport_type', 'last_service_date',
            'last_service_info', 'next_service_due', 'date_added', 'date_updated'
        ]
        # FIXED: Use list instead of string
        read_only_fields = [
            'id', 'service_center', 'customer_name', 'customer_phone', 
            'vehicle_type_name', 'brand_name', 'service_center_name',
            'last_service_info', 'next_service_due', 'date_added', 'date_updated'
        ]
    
    def get_last_service_info(self, obj):
        """Get information about the last service"""
        last_service = obj.vehicle_services.first()
        if last_service:
            return {
                'service_date': last_service.service_date,
                'service_type': last_service.get_service_type_display(),
                'price': last_service.price
            }
        return None
    
    def get_next_service_due(self, obj):
        """Get next service due information"""
        last_service = obj.vehicle_services.first()
        if last_service:
            return {
                'due_date': last_service.next_service_due_date,
                'days_remaining': last_service.days_until_next_service,
                'is_overdue': last_service.is_overdue
            }
        return None
    
    def validate_vehicle_number(self, value):
        """Validate vehicle number format and uniqueness"""
        if not value:
            raise serializers.ValidationError("Vehicle number is required")
        
        clean_number = value.replace(' ', '').upper()
        
        if len(clean_number) < 4:
            raise serializers.ValidationError("Vehicle number is too short")
        
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center:
                existing_vehicle = VehicleOnService.objects.filter(
                    vehicle_number=clean_number,
                    service_center=service_center
                ).exclude(pk=self.instance.pk if self.instance else None)
                
                if existing_vehicle.exists():
                    raise serializers.ValidationError("A vehicle with this number already exists in your service center")
        
        return clean_number
    
    def validate_customer(self, value):
        """Validate that customer belongs to the same service center"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center and value.service_center != service_center:
                raise serializers.ValidationError("Customer must belong to your service center")
        return value
    
    def validate_vehicle_model(self, value):
        """Validate vehicle model year"""
        current_year = timezone.now().year
        if value < 1980 or value > current_year + 1:
            raise serializers.ValidationError(f"Vehicle model year must be between 1980 and {current_year + 1}")
        return value
    
    def create(self, validated_data):
        """Create vehicle with service center from authenticated user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center:
                validated_data['service_center'] = service_center
        return super().create(validated_data)


class ServiceEntrySerializer(serializers.ModelSerializer):
    """Serializer for ServiceEntry model with CRUD operations"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    vehicle_model = serializers.CharField(source='vehicle.vehicle_model', read_only=True)
    service_center_name = serializers.CharField(source='service_center.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    days_until_next_service = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = ServiceEntry
        fields = [
            'id', 'customer', 'customer_name', 'customer_phone', 'vehicle',
            'vehicle_number', 'vehicle_model', 'service_center', 'service_center_name',
            'date_of_entry', 'service_date', 'service_type', 'service_type_display',
            'description', 'price', 'next_service_due_date', 'performed_by',
            'performed_by_name', 'days_until_next_service', 'is_overdue',
            'created_at', 'updated_at'
        ]
        # FIXED: Use list instead of string
        read_only_fields = [
            'id', 'service_center', 'date_of_entry', 'customer_name', 'customer_phone',
            'vehicle_number', 'vehicle_model', 'service_center_name', 'performed_by_name',
            'service_type_display', 'days_until_next_service', 'is_overdue',
            'created_at', 'updated_at'
        ]
    
    def validate_customer(self, value):
        """Validate that customer belongs to the same service center"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center and value.service_center != service_center:
                raise serializers.ValidationError("Customer must belong to your service center")
        return value
    
    def validate_vehicle(self, value):
        """Validate that vehicle belongs to the same service center"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center and value.service_center != service_center:
                raise serializers.ValidationError("Vehicle must belong to your service center")
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        customer = attrs.get('customer')
        vehicle = attrs.get('vehicle')
        service_date = attrs.get('service_date')
        next_service_due_date = attrs.get('next_service_due_date')
        
        if customer and vehicle and vehicle.customer != customer:
            raise serializers.ValidationError("Vehicle must belong to the selected customer")
        
        if service_date and service_date > timezone.now().date():
            raise serializers.ValidationError("Service date cannot be in the future")
        
        if service_date and next_service_due_date and next_service_due_date <= service_date:
            raise serializers.ValidationError("Next service date must be after the service date")
        
        return attrs
    
    def validate_price(self, value):
        """Validate service price"""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        if value > 999999.99:
            raise serializers.ValidationError("Price is too high")
        return value
    
    def create(self, validated_data):
        """Create service entry with service center and performed_by from authenticated user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            service_center = getattr(request.user, 'service_center', None)
            if service_center:
                validated_data['service_center'] = service_center
                validated_data['performed_by'] = request.user
        return super().create(validated_data)


class CustomerVehicleSerializer(serializers.ModelSerializer):
    """Serializer for getting customer's vehicles list"""
    
    vehicle_display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleOnService
        fields = ['id', 'vehicle_number', 'vehicle_model', 'vehicle_display_name']
        # FIXED: Use list instead of '__all__'
        read_only_fields = ['id', 'vehicle_number', 'vehicle_model', 'vehicle_display_name']
    
    def get_vehicle_display_name(self, obj):
        """Create a display name for vehicle selection"""
        variant_name = obj.vehicle_type.variant_name if obj.vehicle_type else "Unknown"
        brand_name = obj.vehicle_type.brand.name if obj.vehicle_type and obj.vehicle_type.brand else "Unknown"
        return f"{obj.vehicle_number} - {brand_name} {variant_name} ({obj.vehicle_model})"


class ServiceSummarySerializer(serializers.Serializer):
    """FIXED: Serializer for service center dashboard summary"""
    
    total_customers = serializers.IntegerField()
    total_vehicles = serializers.IntegerField()
    total_services = serializers.IntegerField()
    services_this_month = serializers.IntegerField()
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    overdue_services = serializers.IntegerField()
    upcoming_services = serializers.IntegerField()
    top_service_types = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    # FIXED: Avoid recursive reference by using ListField instead of ServiceEntrySerializer
    recent_services = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )