
from django.shortcuts import render, redirect, get_list_or_404
from django.contrib import messages

# Create your views here.
# webview form templates  ===========================================================
from django.contrib.auth import authenticate, login, logout
from dashboards.decorators import admin_only
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
def admin_dashboard(request):
    return render(request,"index.html")


def admin_servicecenters(request):
    service_centers = ServiceCenter.objects.all().order_by('-id')

    context = {
        "service_centers":service_centers
    }
    return render(request,"service_centers/service_centers.html",context)



@admin_only
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
def service_center_delete(request, pk):
    try:
        service_center = ServiceCenter.objects.get(pk=pk)
        service_center.delete()
        messages.success(request, 'Service center deleted successfully.')
    except ServiceCenter.DoesNotExist:
        messages.error(request, 'Service center not found.')
    return redirect('admin_servicecenters')


@admin_only
def service_center_detail(request, pk):
    try:
        center = ServiceCenter.objects.get(pk=pk)
        return render(request, "service_centers/service_center_detail.html", {'center': center})
    except ServiceCenter.DoesNotExist:
        return HttpResponseNotFound("Service center not found.")


@admin_only
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