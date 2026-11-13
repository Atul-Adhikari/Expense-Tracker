
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path(
        'balances/visibility/',
        views.toggle_balance_visibility,
        name='toggle_balance_visibility'
    ),
]
