from django.urls import path, include
from . import views


urlpatterns = [
    path("",views.landing_page, name="landing_page"),
    path("admin_login/",views.admin_login, name="admin_login"),
    path("auth_sign_out/",views.auth_sign_out, name="auth_sign_out"),
    path("user_profile/",views.user_profile, name="user_profile"),
    path("dashboard/",views.admin_dashboard,name="admin_dashboard"),
    path('admin/dashboard-api/', views.dashboard_api_data, name='dashboard_api_data'),
    
    path("service-centers/",views.admin_servicecenters,name="admin_servicecenters"),
    path("service-centers/add",views.service_center_add,name="service_center_add"),
    
    path("service_center/delete/<int:pk>/",views.service_center_delete,name="service_center_delete"),
    path("service_center/details/<int:pk>/",views.service_center_detail,name="service_center_detail"),
    path("service_center/edit/<int:pk>/",views.service_center_edit,name="service_center_edit"),

    # brands 

    path("brands/", views.list_brand, name="list_brand"),
    path("brands/add/", views.add_brand, name="add_brand"),
    path("brands/edit/<int:pk>/", views.edit_brand, name="edit_brand"),
    path("brands/delete/<int:pk>/", views.delete_brand, name="delete_brand"),
     # Brand view
    path('brand/view/<int:pk>/', views.brand_view, name='brand_view'),
    
    # Variant operations
    path('brand/<int:brand_id>/variant/add/', views.add_variant, name='add_variant'),
    path('brand/variant/update/<int:variant_id>/', views.update_variant, name='update_variant'),
    path('brand/variant/delete/<int:variant_id>/', views.delete_variant, name='delete_variant'),
    
    # Optional AJAX endpoints
    path('brand/<int:brand_id>/variant/add/ajax/', views.add_variant_ajax, name='add_variant_ajax'),
    path('variant/<int:variant_id>/details/', views.get_variant_details, name='get_variant_details'),
   
]
    
    

