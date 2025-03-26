from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('display/', include('display.urls')),
    path('', include('display.urls')),  # Added for root URL
]