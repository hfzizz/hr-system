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
    path('appraisers/assign/<int:employee_id>/', views.appraisal_assign, name='appraiser_assign'),
    path('appraisers/roles/', views.AppraiserRoleView.as_view(), name='appraiser_roles'),
    path('appraisers/role/<int:employee_id>/', views.role_update, name='role_update'),
    
    # Appraisal Forms
    path('forms/', views.AppraisalListView.as_view(), name='form_list'),
    path('forms/create/', views.AppraisalCreateView.as_view(), name='form_create'),
    path('forms/<int:pk>/', views.AppraisalDetailView.as_view(), name='form_detail'),
    path('forms/<int:pk>/review/', views.AppraisalReviewView.as_view(), name='form_review'),
] 