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
    
    # Appraisal Forms (Single view with filters)
    path('forms/', views.AppraisalListView.as_view(), name='appraisal_list'),
    path('<int:pk>/', views.AppraisalDetailView.as_view(), name='appraisal_detail'),
    path('<int:pk>/edit/', views.AppraisalEditView.as_view(), name='appraisal_edit'),
] 