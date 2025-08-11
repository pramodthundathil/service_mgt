from django.db import models


class Brand(models.Model):
    name = models.CharField(max_length=50)
    image = models.FileField(upload_to='brand_image',null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

class VehicleVariant(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="brand_variants")
    variant_name = models.CharField(max_length=30)
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