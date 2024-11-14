from django.urls import path
from .views import EmployeeCreateView, EmployeeListView

app_name = 'employees'  # Add namespace

urlpatterns = [
    path('', EmployeeListView.as_view(), name='employee_list'),
    path('create/', EmployeeCreateView.as_view(), name='employee_create')
]