
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

@admin_only
@login_required
def admin_dashboard(request):
    return render(request,"index.html")

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