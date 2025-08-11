from django.shortcuts import redirect
from django.contrib import messages

def admin_only(view_fun):
    def wrapper_fun(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser and request.user.role == "admin":
                return view_fun(request, *args, **kwargs)
            else:
                messages.error(request,'Sorry You are not authorized ')
                return redirect('admin_login')
        else:
            messages.info(request,"Please Login to continue")
            return redirect('admin_login')
        
    return wrapper_fun

def unauthenticated_user(view_fun):
    def wrapper_fun(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_fun(request, *args, **kwargs)
        else:
            return redirect("admin_dashboard")
        
    return wrapper_fun

