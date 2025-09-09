# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from index.models import CustomUser, ServiceCenter


class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.FileField(upload_to='brand_images/', null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'

    def __str__(self):
        return self.name


class VehicleVariant(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="brand_variants")
    variant_name = models.CharField(max_length=50)
    BODY_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('hatchback', 'Hatchback'),
        ('suv', 'SUV'),
        ('coupe', 'Coupe'),
        ('convertible', 'Convertible'),
        ('wagon', 'Wagon'),
        ('pickup', 'Pickup'),
        ('van', 'Van'),
        ('minivan', 'Minivan'),
        ('crossover', 'Crossover'),
        ('other', 'Other'),
    ]
    body_type = models.CharField(
        max_length=20,
        choices=BODY_TYPE_CHOICES,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['brand__name', 'variant_name']
        unique_together = ['brand', 'variant_name']
        verbose_name = 'Vehicle Variant'
        verbose_name_plural = 'Vehicle Variants'

    def __str__(self):
        return f'{self.brand.name} - {self.variant_name}'


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)  # Changed from PositiveBigIntegerField
    email = models.EmailField(null=True, blank=True)
    service_center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, related_name='customers')
    date_added = models.DateTimeField(auto_now_add=True)  # Changed to DateTime
    date_updated = models.DateTimeField(auto_now=True)   # Changed to DateTime

    class Meta:
        ordering = ['-date_added']
        unique_together = ['phone', 'service_center']  # Prevent duplicate phone in same center
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f"{self.name} - {self.service_center.name}"


class VehicleOnService(models.Model):  # Renamed to follow Python naming conventions
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_vehicles')
    vehicle_type = models.ForeignKey(VehicleVariant, on_delete=models.SET_NULL, null=True, blank=True)
    service_center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, related_name='vehicles')
    
    vehicle_model = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1980),
            MaxValueValidator(timezone.now().year + 1)
        ],
        help_text="Vehicle manufacturing year"
    )
    vehicle_number = models.CharField(max_length=20)
    
    
    TRANSPORT_TYPE_CHOICES = [
        ('private', 'Private'),
        ('goods_transport', 'Goods Transport'),
        ('passenger_transport', 'Passenger Transport'),
        ('commercial', 'Commercial'),
        ('other', 'Other'),
    ]
    transport_type = models.CharField(
        max_length=50,
        choices=TRANSPORT_TYPE_CHOICES,
        default='private',
    )
    
    last_service_date = models.DateField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_added']
        unique_together = ['vehicle_number', 'service_center']  # Prevent duplicate vehicle numbers in same center
        verbose_name = 'Vehicle on Service'
        verbose_name_plural = 'Vehicles on Service'

    def save(self, *args, **kwargs):
        # Ensure vehicle_number is uppercase and clean
        if self.vehicle_number:
            self.vehicle_number = self.vehicle_number.replace(' ', '').upper()
        
        # Ensure service_center matches customer's service_center
        if self.customer:
            self.service_center = self.customer.service_center
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vehicle_number} - {self.customer.name}"


class ServiceEntry(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer_services')
    vehicle = models.ForeignKey(VehicleOnService, on_delete=models.CASCADE, related_name='vehicle_services')
    service_center = models.ForeignKey(ServiceCenter, on_delete=models.CASCADE, related_name='service_entries')
    
    date_of_entry = models.DateTimeField(auto_now_add=True)
    service_date = models.DateField(default=timezone.now)
    kilometer = models.IntegerField( null=True, blank=True)
    next_kilometer = models.IntegerField()
    WHEEL_SERVICE_CHOICES = [
        ('alignment', 'Wheel Alignment'),
        ('balancing', 'Wheel Balancing'),
        ('rotation', 'Wheel Rotation'),
        ('change', 'Wheel Change'),
        ('repair', 'Wheel Repair'),
        ('inspection', 'Wheel Inspection'),
        ('other', 'Other'),
    ]
    service_type = models.CharField(
        max_length=20,
        choices=WHEEL_SERVICE_CHOICES,
        default='alignment',
    )
    
    description = models.TextField(blank=True, help_text="Additional service details")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        default=0.0
    )
    next_service_due_date = models.DateField()
    
    # Staff who performed the service
    performed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='performed_services'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-service_date', '-created_at']
        verbose_name = 'Service Entry'
        verbose_name_plural = 'Service Entries'

    def save(self, *args, **kwargs):
        # Ensure service_center matches customer's and vehicle's service_center
        if self.customer:
            self.service_center = self.customer.service_center
            
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure customer and vehicle belong to the same service center
        if self.customer and self.vehicle:
            if self.vehicle.customer != self.customer:
                raise ValidationError("Vehicle must belong to the selected customer")
            if self.customer.service_center != self.vehicle.service_center:
                raise ValidationError("Customer and vehicle must belong to the same service center")
        
        # Ensure service date is not in the future
        if self.service_date and self.service_date > timezone.now().date():
            raise ValidationError("Service date cannot be in the future")
            
        # Ensure next service date is after service date
        if self.service_date and self.next_service_due_date:
            if self.next_service_due_date <= self.service_date:
                raise ValidationError("Next service date must be after the service date")

    @property
    def days_until_next_service(self):
        """Calculate days until next service"""
        if self.next_service_due_date:
            today = timezone.now().date()
            delta = self.next_service_due_date - today
            return delta.days
        return None

    @property
    def is_overdue(self):
        """Check if service is overdue"""
        if self.next_service_due_date:
            return timezone.now().date() > self.next_service_due_date
        return False

    def __str__(self):
        return f"{self.get_service_type_display()} - {self.vehicle.vehicle_number} - {self.service_date}"


