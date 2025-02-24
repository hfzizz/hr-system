from django.urls import path
from .views import ContractSubmissionView, get_employee_data, ContractListView, ContractDeleteView, ContractReviewView, ThankYouView, ViewSubmissionsView, enable_contract, send_notification, NotificationsView, delete_notification, forward_to_smt, mark_notification_read, ViewAllSubmissionsView, EmployeeContractView, ContractRedirectView, ContractDetailView, delete_all_notifications, fetch_publications, download_document
from . import views

app_name = 'contract'

urlpatterns = [
    path('', ContractListView.as_view(), name='list'),
    path('form/', ContractSubmissionView.as_view(), name='submission'),
    path('employee-data/<int:employee_id>/', get_employee_data, name='employee_data'),
    path('delete/<int:pk>/', ContractDeleteView.as_view(), name='delete'),
    path('review/<int:pk>/', ContractReviewView.as_view(), name='review'),
    path('thank-you/', ThankYouView.as_view(), name='thank_you'),
    path('view-submissions/<int:employee_id>/', ViewSubmissionsView.as_view(), name='view_submissions'),
    path('enable-contract/', enable_contract, name='enable_contract'),
    path('send-notification/', send_notification, name='send_notification'),
    path('notifications/', NotificationsView.as_view(), name='notifications'),
    path('delete-notification/<int:notification_id>/', delete_notification, name='delete_notification'),
    path('forward-to-smt/<int:contract_id>/', forward_to_smt, name='forward_to_smt'),
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('all-submissions/', ViewAllSubmissionsView.as_view(), name='view_all_submissions'),
    path('employee-contracts/', EmployeeContractView.as_view(), name='employee_contracts'),
    path('redirect/', ContractRedirectView.as_view(), name='redirect'),
    path('contract/view/<int:pk>/', ContractDetailView.as_view(), name='contract_detail'),
    path('delete-all-notifications/', delete_all_notifications, name='delete_all_notifications'),
    path('fetch-publications/<str:scopus_id>/', fetch_publications, name='fetch_publications'),
    path('download-document/<int:contract_id>/<str:doc_type>/', download_document, name='download_document'),
]