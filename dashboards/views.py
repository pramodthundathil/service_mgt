
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.
# webview form templates  ===========================================================
from django.contrib.auth import authenticate, login, logout
from dashboards.decorators import admin_only, unauthenticated_user
from django.http import HttpResponseNotFound
from dashboards.forms import ServiceCenterForm,ServiceCenterRegistrationForm
from index.models import ServiceCenter, CustomUser, LicenseKey, Subscription

def landing_page(request):
    return render(request,"landing_page.html")

def user_profile(request):
    return render(request, '')

def auth_sign_out(request):
    logout(request)
    return redirect("landing_page")

@unauthenticated_user
def admin_login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(request, email=email, password=password)
        if user is not None:
            # Allow only if user is admin role or superuser
            if user.is_superuser or getattr(user, 'role', None) == 'admin':
                login(request, user)
                return redirect("admin_dashboard")
            else:
                messages.error(request, 'You do not have admin access.')
                return redirect('admin_login')
        else:
            messages.error(request, 'Username or password incorrect.')
            return redirect('admin_login')

    return render(request, "login.html")

# views.py - Add this to your existing views.py file

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
import json

from index.models import ServiceCenter, CustomUser, PaymentTransaction, SubscriptionHistory
from interactions.models import Customer, VehicleOnService, ServiceEntry, Brand


@admin_only
@login_required
def admin_dashboard(request):
    """Admin dashboard with comprehensive analytics"""
    
    # Date ranges for filtering
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_12_months = today - timedelta(days=365)
    
    # ==== SERVICE CENTER ANALYTICS ====
    total_service_centers = ServiceCenter.objects.count()
    active_service_centers = ServiceCenter.objects.filter(is_active=True).count()
    trial_centers = ServiceCenter.objects.filter(
        trial_ends_at__gte=timezone.now(),
        subscription_valid_until__isnull=True
    ).count()
    subscribed_centers = ServiceCenter.objects.filter(
        subscription_valid_until__gte=today
    ).count()
    expired_centers = ServiceCenter.objects.filter(
        Q(trial_ends_at__lt=timezone.now()) & 
        (Q(subscription_valid_until__lt=today) | Q(subscription_valid_until__isnull=True))
    ).count()
    
    # ==== FINANCIAL ANALYTICS ====
    total_revenue = PaymentTransaction.objects.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_revenue = PaymentTransaction.objects.filter(
        status='completed',
        completed_at__gte=last_30_days
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    yearly_revenue = PaymentTransaction.objects.filter(
        status='completed',
        completed_at__gte=last_12_months
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # ==== CUSTOMER ANALYTICS ====
    total_customers = Customer.objects.count()
    new_customers_30_days = Customer.objects.filter(
        date_added__gte=last_30_days
    ).count()
    
    total_vehicles = VehicleOnService.objects.count()
    total_services = ServiceEntry.objects.count()
    
    # ==== USER ANALYTICS ====
    total_users = CustomUser.objects.count()
    admin_users = CustomUser.objects.filter(role='admin').count()
    center_admin_users = CustomUser.objects.filter(role='centeradmin').count()
    staff_users = CustomUser.objects.filter(role='staff').count()
    
    # ==== CHART DATA ====
    
    # Monthly Revenue Chart (Last 12 months)
    monthly_revenue_data = PaymentTransaction.objects.filter(
        status='completed',
        completed_at__gte=last_12_months
    ).annotate(
        month=TruncMonth('completed_at')
    ).values('month').annotate(
        revenue=Sum('amount')
    ).order_by('month')
    
    # Service Centers Growth Chart (Last 12 months)
    centers_growth_data = ServiceCenter.objects.filter(
        created_at__gte=last_12_months
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Customer Growth Chart (Last 12 months)
    customer_growth_data = Customer.objects.filter(
        date_added__gte=last_12_months
    ).annotate(
        month=TruncMonth('date_added')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Service Types Distribution
    service_types_data = ServiceEntry.objects.values('service_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Vehicle Types Distribution
    vehicle_types_data = VehicleOnService.objects.values(
        'transport_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Top Brands
    top_brands_data = VehicleOnService.objects.filter(
        vehicle_type__isnull=False
    ).values(
        'vehicle_type__brand__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Recent Activities
    recent_service_centers = ServiceCenter.objects.order_by('-created_at')[:5]
    recent_transactions = PaymentTransaction.objects.filter(
        status='completed'
    ).order_by('-completed_at')[:10]
    recent_services = ServiceEntry.objects.order_by('-created_at')[:10]
    
    # Subscription Status Distribution
    subscription_status_data = [
        {'status': 'Active Subscriptions', 'count': subscribed_centers},
        {'status': 'Trial Period', 'count': trial_centers},
        {'status': 'Expired', 'count': expired_centers},
    ]
    
    # Weekly activity (Last 4 weeks)
    weekly_activity = ServiceEntry.objects.filter(
        created_at__gte=timezone.now() - timedelta(weeks=4)
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        services=Count('id')
    ).order_by('week')
    
    context = {
        # Summary Cards Data
        'total_service_centers': total_service_centers,
        'active_service_centers': active_service_centers,
        'trial_centers': trial_centers,
        'subscribed_centers': subscribed_centers,
        'expired_centers': expired_centers,
        
        # Financial Data
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        
        # Customer Data
        'total_customers': total_customers,
        'new_customers_30_days': new_customers_30_days,
        'total_vehicles': total_vehicles,
        'total_services': total_services,
        
        # User Data
        'total_users': total_users,
        'admin_users': admin_users,
        'center_admin_users': center_admin_users,
        'staff_users': staff_users,
        
        # Chart Data (JSON serialized for JavaScript)
        'monthly_revenue_data': json.dumps(list(monthly_revenue_data), cls=DjangoJSONEncoder),
        'centers_growth_data': json.dumps(list(centers_growth_data), cls=DjangoJSONEncoder),
        'customer_growth_data': json.dumps(list(customer_growth_data), cls=DjangoJSONEncoder),
        'service_types_data': json.dumps(list(service_types_data), cls=DjangoJSONEncoder),
        'vehicle_types_data': json.dumps(list(vehicle_types_data), cls=DjangoJSONEncoder),
        'top_brands_data': json.dumps(list(top_brands_data), cls=DjangoJSONEncoder),
        'subscription_status_data': json.dumps(subscription_status_data, cls=DjangoJSONEncoder),
        'weekly_activity': json.dumps(list(weekly_activity), cls=DjangoJSONEncoder),
        
        # Recent Activities
        'recent_service_centers': recent_service_centers,
        'recent_transactions': recent_transactions,
        'recent_services': recent_services,
    }
    
    return render(request, "index.html", context)


@admin_only
@login_required
def dashboard_api_data(request):
    """API endpoint for dashboard data updates"""
    data_type = request.GET.get('type', 'summary')
    
    if data_type == 'summary':
        today = timezone.now().date()
        
        data = {
            'service_centers': ServiceCenter.objects.count(),
            'total_revenue': PaymentTransaction.objects.filter(
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'customers': Customer.objects.count(),
            'services_today': ServiceEntry.objects.filter(
                service_date=today
            ).count(),
        }
        
    elif data_type == 'revenue':
        last_12_months = timezone.now().date() - timedelta(days=365)
        revenue_data = PaymentTransaction.objects.filter(
            status='completed',
            completed_at__gte=last_12_months
        ).annotate(
            month=TruncMonth('completed_at')
        ).values('month').annotate(
            revenue=Sum('amount')
        ).order_by('month')
        
        data = list(revenue_data)
    
    else:
        data = {'error': 'Invalid data type'}
    
    return JsonResponse(data, safe=False, encoder=DjangoJSONEncoder)

@admin_only
@login_required
def admin_servicecenters(request):
    service_centers = ServiceCenter.objects.all().order_by('-id')

    context = {
        "service_centers":service_centers
    }
    return render(request,"service_centers/service_centers.html",context)



@admin_only
@login_required
def service_center_add(request):
    
    if request.method == 'POST':
        form = ServiceCenterRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service center added successfully.')
            return redirect('admin_servicecenters')
        else:
            print(form.errors )
            messages.error(request, f'Failed to add service center. Please check the form. {form.errors}')
    else:
        form = ServiceCenterRegistrationForm()

    return render(request, "service_centers/add_service_center.html", {'form': form})


@admin_only
@login_required
def service_center_delete(request, pk):
    try:
        service_center = ServiceCenter.objects.get(pk=pk)
        service_center.delete()
        messages.success(request, 'Service center deleted successfully.')
    except ServiceCenter.DoesNotExist:
        messages.error(request, 'Service center not found.')
    return redirect('admin_servicecenters')


@admin_only
@login_required
def service_center_detail(request, pk):
    try:
        center = ServiceCenter.objects.get(pk=pk)
        return render(request, "service_centers/service_center_detail.html", {'center': center})
    except ServiceCenter.DoesNotExist:
        return HttpResponseNotFound("Service center not found.")


@admin_only
@login_required
def service_center_edit(request, pk):
    try:
        service_center = ServiceCenter.objects.get(pk=pk)
        if request.method == 'POST':
            form = ServiceCenterForm(request.POST,instance = service_center )
            if form.is_valid():
                form.save()
                messages.success(request, 'Service center updated successfully.')
                return redirect('admin_servicecenters')
            else:
                messages.error(request, 'Failed to update service center. Please check the form.')
        else:
            form = ServiceCenterForm(instance=service_center)

        return render(request, "service_centers/edit_service_center.html", {'form': form, 'center': service_center})
    except ServiceCenter.DoesNotExist:
        return HttpResponseNotFound("Service center not found.")


# =================================================================================== 

## brand and variants add functionalities 
from interactions.models import Brand, VehicleVariant 
from .forms import BrandForm, VehicleVariantForm

def list_brand(request):
    brands = Brand.objects.all().order_by("-id")
    context = {"brands":brands}
    return render(request,'brand_and_variant/list_brand.html', context)


def add_brand(request):
    form = BrandForm()
    
    if request.method == "POST":
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            brand = form.save()
            brand.save()
            messages.success(request,"Brand Added success")
            return redirect("brand_view", pk = brand.id )
        else:
            messages.error(request,"Something is wrong....")
            return redirect("add_brand")

    else:
        context = {"form":form}
        return render(request,"brand_and_variant/brand_add.html",context)

def edit_brand(request, pk):
    brand = get_object_or_404(Brand, id = pk)
    form = BrandForm(instance=brand)
    
    if request.method == "POST":
        form = BrandForm(request.POST, request.FILES, instance = brand)
        if form.is_valid():
            brand = form.save()
            brand.save()
            messages.success(request,"Brand Added success")
            return redirect("brand_view", pk = brand.id )
        else:
            messages.error(request,"Something is wrong....")

    else:
        context = {"form":form}
        return render(request,"brand_and_variant/brand_edit.html",context)
    
def delete_brand(request, pk):
    get_object_or_404(Brand,id = pk).delete()
    messages.success(request,"Brand deleted successfully")
    return redirect("list_brand")


from django.http import JsonResponse


from .forms import VehicleVariantForm, BrandForm

def brand_view(request, pk):
    """Display brand details with all its variants"""
    brand = get_object_or_404(Brand, id=pk)
    form = VehicleVariantForm()
    variants = brand.brand_variants
    
    context = {
        "brand": brand,
        'form': form,
        "variants": variants
    }
    return render(request, "brand_and_variant/brand_view.html", context)

def add_variant(request, brand_id):
    """Add new variant to a specific brand"""
    brand = get_object_or_404(Brand, id=brand_id)
    
    if request.method == 'POST':
        variant_name = request.POST.get('variant_name')
        body_type = request.POST.get('body_type')
        
        # Check if variant name already exists for this brand
        if VehicleVariant.objects.filter(brand=brand, variant_name=variant_name).exists():
            messages.error(request, f'Variant "{variant_name}" already exists for {brand.name}.')
            return redirect('brand_view', pk=brand.id)
        
        # Create new variant
        variant = VehicleVariant.objects.create(
            brand=brand,
            variant_name=variant_name,
            body_type=body_type if body_type else None
        )
        
        messages.success(request, f'Variant "{variant_name}" added successfully to {brand.name}.')
        return redirect('brand_view', pk=brand.id)
    
    return redirect('brand_view', pk=brand.id)

def update_variant(request, variant_id):
    """Update existing variant"""
    variant = get_object_or_404(VehicleVariant, id=variant_id)
    brand = variant.brand
    
    if request.method == 'POST':
        variant_name = request.POST.get('variant_name')
        body_type = request.POST.get('body_type')
        
        # Check if variant name already exists for this brand (excluding current variant)
        if VehicleVariant.objects.filter(
            brand=brand, 
            variant_name=variant_name
        ).exclude(id=variant.id).exists():
            messages.error(request, f'Variant "{variant_name}" already exists for {brand.name}.')
            return redirect('brand_view', pk=brand.id)
        
        # Update variant
        variant.variant_name = variant_name
        variant.body_type = body_type if body_type else None
        variant.save()
        
        messages.success(request, f'Variant "{variant_name}" updated successfully.')
        return redirect('brand_view', pk=brand.id)
    
    return redirect('brand_view', pk=brand.id)

def delete_variant(request, variant_id):
    """Delete existing variant"""
    variant = get_object_or_404(VehicleVariant, id=variant_id)
    brand = variant.brand
    variant_name = variant.variant_name
    
    if request.method == 'POST':
        variant.delete()
        messages.success(request, f'Variant "{variant_name}" deleted successfully.')
        return redirect('brand_view', pk=brand.id)
    
    return redirect('brand_view', pk=brand.id)

# Optional: AJAX versions for better UX
def add_variant_ajax(request, brand_id):
    """AJAX version of add variant"""
    if request.method == 'POST':
        brand = get_object_or_404(Brand, id=brand_id)
        variant_name = request.POST.get('variant_name')
        body_type = request.POST.get('body_type')
        
        # Check if variant already exists
        if VehicleVariant.objects.filter(brand=brand, variant_name=variant_name).exists():
            return JsonResponse({
                'success': False, 
                'message': f'Variant "{variant_name}" already exists for {brand.name}.'
            })
        
        # Create new variant
        variant = VehicleVariant.objects.create(
            brand=brand,
            variant_name=variant_name,
            body_type=body_type if body_type else None
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Variant "{variant_name}" added successfully.',
            'variant': {
                'id': variant.id,
                'name': variant.variant_name,
                'body_type': variant.get_body_type_display() if variant.body_type else ''
            }
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def get_variant_details(request, variant_id):
    """Get variant details for editing (AJAX)"""
    variant = get_object_or_404(VehicleVariant, id=variant_id)
    return JsonResponse({
        'id': variant.id,
        'variant_name': variant.variant_name,
        'body_type': variant.body_type or '',
        'brand_id': variant.brand.id
    })