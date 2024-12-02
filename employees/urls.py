from django.urls import path
from .views import EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeProfileView, EmployeeProfileEditView, EmployeeDetailView

app_name = 'employees'

urlpatterns = [
    path('', EmployeeListView.as_view(), name='employee_list'),
    path('create/', EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/edit/', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('profile/', EmployeeProfileView.as_view(), name='profile'),
    path('profile/edit/', EmployeeProfileEditView.as_view(), name='profile_edit'),
    path('<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
]