from django.urls import path
from .views import ContractSubmissionView, get_employee_data, ContractListView, ContractDeleteView, ContractReviewView, ThankYouView, ViewSubmissionsView, enable_contract, send_notification, NotificationsView, delete_notification, forward_to_smt, mark_notification_read, ViewAllSubmissionsView, EmployeeContractView, ContractRedirectView, ContractDetailView, delete_all_notifications, fetch_publications, download_document, send_back_to_employee, get_hr_comments, EditSubmissionView, DeanContractView, SMTReviewView
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
    path('forward-to-smt/<int:contract_id>/', views.forward_to_smt, name='forward_to_smt'),
    path('notifications/<int:notification_id>/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('all-submissions/', ViewAllSubmissionsView.as_view(), name='view_all_submissions'),
    path('employee-contracts/', EmployeeContractView.as_view(), name='employee_contracts'),
    path('redirect/', ContractRedirectView.as_view(), name='redirect'),
    path('view/<int:pk>/', views.ContractDetailView.as_view(), name='contract_detail'),
    path('delete-all-notifications/', delete_all_notifications, name='delete_all_notifications'),
    path('fetch-publications/<str:scopus_id>/', fetch_publications, name='fetch_publications'),
    path('download-document/<int:contract_id>/<str:doc_type>/', download_document, name='download_document'),
    path('send-back/<int:contract_id>/', send_back_to_employee, name='send_back_to_employee'),
    path('get-hr-comments/<int:contract_id>/', get_hr_comments, name='get_hr_comments'),
    path('edit-submission/<int:pk>/', EditSubmissionView.as_view(), name='edit_submission'),
    path('dean-department-contracts/', DeanContractView.as_view(), name='dean_department_contracts'),
    path('dean-review/<int:contract_id>/', views.DeanReviewView.as_view(), name='dean_review'),
    path('submit-dean-review/<int:contract_id>/', views.submit_dean_review, name='submit_dean_review'),
    path('download-dean-document/<int:contract_id>/', views.download_dean_document, name='download_dean_document'),
    path('download-dean-document/<int:contract_id>/<int:review_id>/', views.download_dean_document, name='download_dean_document'),
    path('forward-to-dean/<int:contract_id>/', views.forward_to_dean, name='forward_to_dean'),
    path('smt-review/<int:contract_id>/', SMTReviewView.as_view(), name='smt_review'),
    path('smt-decision/<int:contract_id>/', views.smt_decision, name='smt_decision'),
    path('smt-contracts/', views.SMTContractsView.as_view(), name='smt_contracts'),
    path('download-smt-document/<int:contract_id>/', views.download_smt_document, name='download_smt_document'),
    path('download-smt-document/<int:contract_id>/<int:review_id>/', views.download_smt_document, name='download_smt_document_with_id'),
]