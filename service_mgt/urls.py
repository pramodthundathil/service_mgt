from django.contrib import admin
from django.urls import path,include 
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import index.views as views

# Setup Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title='API Documentation Wheel Alignment Info',
        default_version='v2',
        description="API for managing Wheel Alignment Info in the system",
    ),
    public=True,  # Set public to True for public access
    permission_classes=(permissions.AllowAny,),  # Allow public access
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("",include("dashboards.urls")),
    path("api/", include("index.urls")),
    path('interaction/',include('interactions.urls')),
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # Token authentication
    # path('api/token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
# Media file serving
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)