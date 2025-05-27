from django.urls import path, include
from . import views

app_name = 'appraisals'

urlpatterns = [

    # Appraisal Periods
    path('periods/create/', views.create_period, name='period_create'),
    path('periods/<int:period_id>/', views.set_default_period, name='set_default_period'),
    path('periods/<int:period_id>/create/', views.create_period, name='period_create'),

    # Appraisers
    path('appraisers/', views.AppraiserListView.as_view(), name='appraiser_list'),
    path('appraisers/assign/<str:employee_id>/', views.AppraisalAssignView.as_view(), name='appraiser_assign'),
    path('appraisers/roles/', views.AppraiserRoleView.as_view(), name='appraiser_roles'),
    path('appraisers/role/<str:employee_id>/', views.role_update, name='role_update'),
    
    # Appraisal Forms
    path('forms/', views.AppraisalListView.as_view(), name='form_list'),
    path('forms/delete/', views.appraisal_delete, name='form_delete'),
    # path('forms/create/', views.AppraisalCreateForm.as_view(), name='form_create'),
    path('forms/<int:pk>/', views.AppraisalDetailView.as_view(), name='form_detail'),
    path('forms/<int:appraisal_id>/fill/', views.AppraiseeUpdateView.as_view(), name='appraisal_fill'),
    path('forms/<int:appraisal_id>/review/', views.AppraiserWizard.as_view(), name='appraisal_review'),
    path('forms/<int:appraisal_id>/appraisee-review/', views.AppraiseeWizard.as_view(), name='appraisee_review'),
    # path('forms/<int:pk>/review/', views.AppraisalReviewView.as_view(), name='form_review'),

    path('api/appraisers/', views.get_appraisers, name='get_appraisers'),
    path('set-default-deadline/', views.set_default_deadline, name='set_default_deadline'),
    path('get-default-deadline/', views.get_default_deadline, name='get_default_deadline'),
    path('get-default-period/', views.get_default_period, name='get_default_period'),

    # HTMX endpoints for Section B
    path('save-multiple-fields/', views.save_multiple_fields, name='save_multiple_fields'),
    # path('save-rating/', views.save_rating, name='save_rating'),
    # path('save-text-field/', views.save_text_field, name='save_text_field'),
    path('save-field/', views.save_field, name='save_field'),
    path('toggle-leadership-section/', views.toggle_leadership_section, name='toggle_leadership_section'),
    path('toggle-other-relationship/', views.toggle_other_relationship, name='toggle_other_relationship'),  
    # path('save-draft/', views.save_draft, name='save_draft'),
    path('save-section-data/', views.save_section_data, name='save_section_data'),
    path('get-section-data/', views.get_section_data, name='get_section_data'),

    # Add these URL patterns for the wizard sections
    path('forms/<int:appraisal_id>/review/section-a/', views.appraisal_wizard_section_a, name='appraisal_wizard_section_a'),
    path('forms/<int:appraisal_id>/review/section-c/', views.appraisal_wizard_section_c, name='appraisal_wizard_section_c'),
    path('update-appraisal-status/', views.update_appraisal_status, name='update_appraisal_status'),

]