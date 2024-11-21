from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    path('', views.AppraisalListView.as_view(), name='appraisal_list'),
    path('assign/', views.AppraisalAssignView.as_view(), name='appraisal_assign'),
] 