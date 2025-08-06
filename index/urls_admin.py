from django.urls import path, include
from . import views


urlpatterns = [
    path("login/",views.admin_login, name="admin_login"),
    path("dashboard/",views.admin_dashboard,name="admin_dashboard"),
    path("service-centers/",views.admin_servicecenters,name="admin_servicecenters"),
    path("service-centers/add",views.service_center_add,name="service_center_add"),
    
    path("service_center/delete/<int:pk>/",views.service_center_delete,name="service_center_delete"),
    path("service_center/details/<int:pk>/",views.service_center_detail,name="service_center_detail"),
    path("service_center/edit/<int:pk>/",views.service_center_edit,name="service_center_edit"),

   
]
    
    

