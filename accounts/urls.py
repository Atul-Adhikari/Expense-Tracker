
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html'
        ),
        name='login'
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('my-accounts/', views.account_list, name='account_list'),

    path('my-accounts/add/', views.account_create, name='account_create'),

    path(
        'my-accounts/<int:pk>/edit/',
        views.account_update,
        name='account_update'
    ),

    path(
        'my-accounts/<int:pk>/toggle-status/',
        views.account_toggle_status,
        name='account_toggle_status'
    ),
]
