from django.urls import path, include
from . import views

app_name = 'appraisals'

urlpatterns = [

    # Appraisal Periods
    path('periods/create/', views.create_period, name='period_create'),
    path('periods/<int:period_id>/set-default/', views.set_default_period, name='set_default_period'),
    path('periods/<int:period_id>/edit/', views.edit_period, name='edit_period'),
    path('periods/<int:period_id>/update/', views.update_period, name='update_period'),
    path('periods/<int:period_id>/delete/', views.delete_period, name='delete_period'),


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
    # path('forms/<int:pk>/review/', views.AppraisalReviewView.as_view(), name='form_review'),

    path('api/appraisers/', views.get_appraisers, name='get_appraisers'),
    path('get-default-date/', views.get_default_date, name='get_default_date'),

    # HTMX endpoints for Section B
    path('save-rating/', views.save_rating, name='save_rating'),
    path('save-text-field/', views.save_text_field, name='save_text_field'),
    path('save-field/', views.save_field, name='save_field'),
    path('toggle-leadership-section/', views.toggle_leadership_section, name='toggle_leadership_section'),
    path('toggle-other-relationship/', views.toggle_other_relationship, name='toggle_other_relationship'),

        # Add these URL patterns for the wizard sections
    path('forms/<int:appraisal_id>/review/section-a/', views.appraisal_wizard_section_a, name='appraisal_wizard_section_a'),
    path('forms/<int:appraisal_id>/review/section-c/', views.appraisal_wizard_section_c, name='appraisal_wizard_section_c'),

]