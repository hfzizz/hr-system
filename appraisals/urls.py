from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    path('', views.AppraisalListView.as_view(), name='appraisal_list'),
    path('<int:pk>/', views.AppraisalDetailView.as_view(), name='appraisal_detail'),
    path('create/', views.AppraisalCreateView.as_view(), name='appraisal_create'),
    path('<int:pk>/edit/', views.AppraisalUpdateView.as_view(), name='appraisal_edit'),
] 