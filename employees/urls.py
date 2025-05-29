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
    path('profile/', views.ProfileView.as_view(), name='profile'), # can delete this and use the new one below
    path('parse-resume/', views.ResumeParserView.as_view(), name='parse_resume'),
    path('profile/<int:pk>/', views.ProfileDetailView.as_view(), name='profile'),
    path('profile/<int:pk>/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('change-password/', views.CustomPasswordChangeView.as_view(), name='change_password'),
    path('publications/load-form/', views.load_publication_form, name='load_publication_form'),
    path('publications/add-form/', views.add_publication_form, name='add_publication_form'),
    path('publications/<int:pk>/delete/', views.delete_publication, name='delete_publication'),
    path('publications/fetch-metadata/', views.fetch_publication_metadata, name='fetch_publication_metadata'),
    path('publications/load-type-fields/', views.load_type_fields_publication, name='load_type_fields_publication'),
    path('bulk_add/', views.bulk_add, name='bulk_add'),
    path('bulk_upload_parse/', views.bulk_upload_parse, name='bulk_upload_parse'),
    path('bulk_confirm_create/', views.bulk_confirm_create, name='bulk_confirm_create'),
    path('bulk_cancel/', views.bulk_cancel, name='bulk_cancel'),
    path('download_credentials_csv/', views.download_credentials_csv, name='download_credentials_csv'),
    path('bulk_employee_edit/<int:index>/', views.bulk_employee_edit, name='bulk_employee_edit'),
    path('bulk_employee_edit/<int:index>/autosave/', views.bulk_employee_autosave, name='bulk_employee_autosave'),
    path('bulk_employee_delete/<int:index>/', views.bulk_employee_delete, name='bulk_employee_delete'),
]