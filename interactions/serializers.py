# serializers.py
from rest_framework import serializers
from .models import Brand, VehicleVariant


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
        return obj.vehiclevariant_set.count()


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


# For nested variants within brand detail
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
        source='vehiclevariant_set', 
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
        return obj.vehiclevariant_set.count()


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
        return obj.vehiclevariant_set.count()
        
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
    
    # For display in list/detail views
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
        
        # For updates, exclude current instance
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