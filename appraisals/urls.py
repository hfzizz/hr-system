from django.urls import path, include
from . import views

app_name = 'appraisals'

urlpatterns = [
    # Dashboard
    path('', views.AppraisalDashboardView.as_view(), name='dashboard'),
    
    # Appraisal Periods
    path('periods/', views.AppraisalPeriodListView.as_view(), name='period_list'),
    path('periods/create/', views.create_period, name='period_create'),
    path('periods/<int:pk>/toggle/', views.toggle_period, name='period_toggle'),
    
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
    path('forms/<int:pk>/fill/', views.AppraiseeUpdateView.as_view(), name='appraisal_fill'),
    path('forms/<int:pk>/review/', views.AppraiserWizard.as_view(), name='appraisal_review'),
    # path('forms/<int:pk>/review/', views.AppraisalReviewView.as_view(), name='form_review'),

    path('api/appraisers/', views.get_appraisers_api, name='api_get_appraisers'),
]