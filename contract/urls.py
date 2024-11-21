from django.urls import path
from . import views

app_name = 'contract'

urlpatterns = [
    path('templates/', views.FormTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.FormTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:template_id>/fields/', views.manage_fields, name='manage_fields'),
    path('templates/<int:template_id>/fill/', views.fill_form, name='fill_form'),
    path('submissions/', views.SubmissionListView.as_view(), name='submission_list'),
    path('template/<int:pk>/delete/', views.FormTemplateDeleteView.as_view(), name='template_delete'),
    path('template/<int:pk>/edit/', views.FormTemplateUpdateView.as_view(), name='template_edit'),
    path('field/<int:field_id>/delete/', views.delete_field, name='delete_field'),
    path('field/<int:field_id>/edit/', views.edit_field, name='edit_field'),
    path('template/<int:template_id>/update/', views.update_template_settings, name='update_template'),
    path('api/employees/<int:employee_id>/', views.get_employee_data, name='get_employee_data'),
    path('submission/<int:pk>/delete/', views.delete_submission, name='submission_delete'),]