from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path('', views.market_analysis, name='market_analysis'),
    path('refresh-data/', views.refresh_data, name='refresh_data'),  # New endpoint
    path('static/indexstats/data.json', views.serve_data_json, name='serve_data_json'),
]
# if settings.DEBUG:
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])