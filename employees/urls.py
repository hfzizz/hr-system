from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.EmployeeListView.as_view(), name='employee_list'),
    path('create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('department/', views.DepartmentListView.as_view(), name='department_list'),
    path('department/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('department/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_edit'),
    path('department/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]