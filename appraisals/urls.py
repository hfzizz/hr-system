from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    path('', views.AppraisalListView.as_view(), name='appraisal_list'),
    path('<int:pk>/', views.AppraisalDetailView.as_view(), name='appraisal_detail'),
    path('create/', views.appraisal_edit, name='appraisal_create'),
    path('<int:pk>/edit/', views.appraisal_edit, name='appraisal_edit'),
    path('assign/', views.appraisal_assign, name='appraisal_assign'),
    path('periods/', views.AppraisalPeriodListView.as_view(), name='period_list'),
    path('periods/create/', views.create_period, name='period_create'),
    path('periods/<int:pk>/toggle/', views.toggle_period, name='period_toggle'),
] 