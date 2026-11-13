
from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('add/', views.transaction_create, name='transaction_create'),
    path('<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    # Transfers
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/add/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/edit/', views.transfer_update, name='transfer_update'),
    path('transfers/<int:pk>/delete/', views.transfer_delete, name='transfer_delete'),
        # Recurring Transactions
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/add/', views.recurring_create, name='recurring_create'),
    path(
        'recurring/<int:pk>/edit/',
        views.recurring_update,
        name='recurring_update'
    ),
    path(
        'recurring/<int:pk>/toggle/',
        views.recurring_toggle_status,
        name='recurring_toggle_status'
    ),
    path(
        'recurring/<int:pk>/delete/',
        views.recurring_delete,
        name='recurring_delete'
    ),
    path(
        'export/csv/',
        views.transaction_export_csv,
        name='transaction_export_csv'
    ),
    path(
        'export/excel/',
        views.transaction_export_excel,
        name='transaction_export_excel'
    ),
]
