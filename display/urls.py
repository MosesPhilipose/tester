from django.urls import path
from . import views

urlpatterns = [
    path('', views.market_analysis, name='market_analysis'),
    path('refresh-data/', views.refresh_data, name='refresh_data'),
    path('ticker-data/', views.get_ticker_data, name='ticker_data'),
]
