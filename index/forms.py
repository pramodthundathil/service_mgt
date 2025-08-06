from django import forms
from django.utils import timezone
from .models import CustomUser, ServiceCenter, LicenseKey, Subscription
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ServiceCenter



class BaseFormControlMixin:
    """Apply form-control class and placeholder to all fields"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Enter {name.replace("_", " ").capitalize()}'
            })


# forms.py
from django import forms
from django.utils import timezone
from .models import ServiceCenter

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


class ServiceCenterRegistrationForm(BaseFormControlMixin, forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter password',
        }),
        min_length=8,
        help_text="Password for the admin user (minimum 8 characters)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm password',
        }),
        min_length=8,
        help_text="Confirm the admin password"
    )

    class Meta:
        model = ServiceCenter
        fields = [
            'name', 'address', 'email', 'phone',
            'password', 'confirm_password'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'ABC Service Center'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': '123 Main Street, City, ZIP'}),
            'email': forms.EmailInput(attrs={'placeholder': 'contact@servicecenter.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+1234567890'}),
        }
        labels = {
            'name': 'Service Center Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'address': 'Full Address',
            'password': 'Password',
            'confirm_password': 'Confirm Password',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if ServiceCenter.objects.filter(email=email).exists():
            raise forms.ValidationError("Service center with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        try:
            validate_password(password)
        except ValidationError as e:
            self.add_error('password', e)

        return cleaned_data

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


