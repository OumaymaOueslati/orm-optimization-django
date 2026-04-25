from django.urls import path
from . import views

urlpatterns = [
    path('orders-slow/', views.orders_slow, name='orders_slow'),
    path('orders-fast/', views.orders_fast, name='orders_fast'),
]