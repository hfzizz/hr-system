from django.urls import path
from .views import ContractSubmissionView, get_employee_data, ContractListView, ContractDeleteView, ContractReviewView

app_name = 'contract'

urlpatterns = [
    path('', ContractListView.as_view(), name='list'),
    path('form/', ContractSubmissionView.as_view(), name='submission'),
    path('employee-data/<int:employee_id>/', get_employee_data, name='employee_data'),
    path('delete/<int:pk>/', ContractDeleteView.as_view(), name='delete'),
    path('review/<int:pk>/', ContractReviewView.as_view(), name='review'),
]