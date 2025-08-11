from django import forms
from django.utils import timezone
from index.models import CustomUser, ServiceCenter, LicenseKey, Subscription
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction


class BaseFormControlMixin:
    """Apply form-control class and placeholder to all fields"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {name.replace("_", " ").capitalize()}'
            })




class BaseFormControlMixin:
    """Mixin to add Bootstrap classes to form fields"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'custom-control-input'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, forms.DateTimeInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'datetime-local'
                })
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'type': 'date'
                })
            else:
                field.widget.attrs.update({'class': 'form-control'})

class ServiceCenterForm(BaseFormControlMixin, forms.ModelForm):
    class Meta:
        model = ServiceCenter
        fields = ['name', 'email', 'phone', 'address', 'trial_ends_at']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'trial_ends_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            
        }
        labels = {
            'name': 'Service Center Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'address': 'Full Address',
            'trial_ends_at': 'Trial End Date & Time',
            
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required")

        queryset = ServiceCenter.objects.filter(email=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("A service center with this email already exists.")
        return email

    def clean_trial_ends_at(self):
        trial_ends_at = self.cleaned_data.get('trial_ends_at')
        if trial_ends_at and trial_ends_at < timezone.now():
            raise forms.ValidationError("Trial end date must be in the future")
        return trial_ends_at


  # if you store it in mixins.py



class ServiceCenterRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter password',
            'class': 'form-control'
        }),
        min_length=8,
        help_text="Password for the admin user (minimum 8 characters)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
            'class': 'form-control'
        }),
        min_length=8,
        help_text="Confirm the admin password"
    )

    class Meta:
        model = ServiceCenter
        fields = [
            'name', 'address', 'email', 'phone'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'ABC Service Center',
                'class': 'form-control'
            }),
            'address': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': '123 Main Street, City, ZIP',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'contact@servicecenter.com',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+1234567890',
                'class': 'form-control'
            }),
        }
        labels = {
            'name': 'Service Center Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'address': 'Full Address',
        }

    def clean_email(self):
        """Validate that email is unique for service centers"""
        email = self.cleaned_data.get('email')
        if ServiceCenter.objects.filter(email=email).exists():
            raise forms.ValidationError("Service center with this email already exists.")
        return email

    def clean(self):
        """Custom validation for password matching and strength"""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Check if passwords match
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")

            # Validate password strength
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        """Create service center, admin user, license key, and trial subscription"""
        # Get the password before saving the service center
        password = self.cleaned_data.get('password')
        
        # Create Service Center (don't save yet to modify if needed)
        service_center = super().save(commit=False)
        
        if commit:
            # Save the service center first
            service_center.save()
            
            # Extract admin user data
            admin_data = {
                'email': service_center.email,
                'phone_number': service_center.phone or '',
                'password': password,
                'role': 'centeradmin',
                'service_center': service_center
            }
            
            # Create Admin User
            admin_user = CustomUser.objects.create_user(**admin_data)
            
            # Create License Key
            license_key = LicenseKey.objects.create(
                assigned_to=service_center,
                is_used=True
            )
            
            # Create Trial Subscription (15 days)
            trial_end_date = timezone.now() + timezone.timedelta(days=15)
            trial_subscription = Subscription.objects.create(
                service_center=service_center,
                status='trial',
                started_at=timezone.now(),
                expires_at=trial_end_date,
                amount=0.00,
                currency='INR'
            )
            
            # Update service center trial_ends_at if it wasn't set automatically
            if not service_center.trial_ends_at:
                service_center.trial_ends_at = trial_end_date
                service_center.save(update_fields=['trial_ends_at'])

        return service_center
    

class CustomUserForm(BaseFormControlMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password'}),
        min_length=8,
        help_text="Minimum 8 characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'}),
        min_length=8
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'phone_number', 'role',
            'service_center', 'is_active', 'password', 'confirm_password'
        ]

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email is already in use")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data


class LicenseKeyForm(BaseFormControlMixin, forms.ModelForm):
    class Meta:
        model = LicenseKey
        exclude = ['key', 'created_at', 'valid_until', 'is_used']  # Auto-handled


class SubscriptionForm(BaseFormControlMixin, forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            'service_center', 'status', 'started_at', 'expires_at',
            'razorpay_payment_id', 'razorpay_order_id', 'razorpay_signature',
            'amount', 'currency'
        ]

    def clean_expires_at(self):
        start = self.cleaned_data.get('started_at')
        end = self.cleaned_data.get('expires_at')
        if start and end and end < start:
            raise forms.ValidationError("Expiration must be after start date")
        return end


# brand and variant

from interactions.models import Brand, VehicleVariant




class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'image', 'image_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Brand Name'
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Image URL'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip().title()
            # Check if brand name already exists (excluding current instance if editing)
            existing_brand = Brand.objects.filter(name__iexact=name)
            if self.instance.pk:
                existing_brand = existing_brand.exclude(pk=self.instance.pk)
            if existing_brand.exists():
                raise forms.ValidationError(f'Brand "{name}" already exists.')
        return name

class VehicleVariantForm(forms.ModelForm):
    class Meta:
        model = VehicleVariant
        fields = ['brand', 'variant_name', 'body_type']
        widgets = {
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'variant_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Variant Name'
            }),
            'body_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        brand = kwargs.pop('brand', None)
        super().__init__(*args, **kwargs)
        
        # If brand is provided, hide the brand field and set it as initial
        if brand:
            self.fields['brand'].widget = forms.HiddenInput()
            self.fields['brand'].initial = brand

    def clean_variant_name(self):
        variant_name = self.cleaned_data.get('variant_name')
        brand = self.cleaned_data.get('brand')
        
        if variant_name and brand:
            variant_name = variant_name.strip().title()
            # Check if variant name already exists for this brand
            existing_variant = VehicleVariant.objects.filter(
                brand=brand, 
                variant_name__iexact=variant_name
            )
            if self.instance.pk:
                existing_variant = existing_variant.exclude(pk=self.instance.pk)
            if existing_variant.exists():
                raise forms.ValidationError(
                    f'Variant "{variant_name}" already exists for {brand.name}.'
                )
        return variant_name

# Separate form for adding variants (without brand field)
class AddVariantForm(forms.ModelForm):
    class Meta:
        model = VehicleVariant
        fields = ['variant_name', 'body_type']
        widgets = {
            'variant_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter Variant Name',
                'required': True
            }),
            'body_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.brand = kwargs.pop('brand', None)
        super().__init__(*args, **kwargs)

    def clean_variant_name(self):
        variant_name = self.cleaned_data.get('variant_name')
        
        if variant_name and self.brand:
            variant_name = variant_name.strip().title()
            # Check if variant name already exists for this brand
            if VehicleVariant.objects.filter(
                brand=self.brand, 
                variant_name__iexact=variant_name
            ).exists():
                raise forms.ValidationError(
                    f'Variant "{variant_name}" already exists for {self.brand.name}.'
                )
        return variant_name

    def save(self, commit=True):
        variant = super().save(commit=False)
        if self.brand:
            variant.brand = self.brand
        if commit:
            variant.save()
        return variant