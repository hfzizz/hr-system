from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import ContractNotification, ContractRenewalStatus, Contract
from employees.models import Employee
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def check_contract_renewals(sender, user, request, **kwargs):
    # Check if user is in HR group
    if not user.groups.filter(name='HR').exists():
        return

    # Delete previous notifications of this type for HR users
    ContractNotification.objects.filter(
        employee__user__groups__name='HR',
        message__startswith='The following employees need contract renewal enabled:'
    ).delete()

    # Get eligible employees
    today = timezone.now().date()   
    eligible_employees = []

    contract_employees = Employee.objects.filter(
        appointment_type='Contract',
        contractrenewalstatus__is_enabled=False  # Contract renewal not enabled
    ).exclude(
        # Exclude employees with active contract submissions
        contracts__status__in=['pending', 'approved', 'rejected', 'smt_review']
    ).distinct()

    for employee in contract_employees:
        # Calculate next renewal date
        renewal_date = employee.hire_date + relativedelta(years=3)
        while renewal_date < today:
            renewal_date += relativedelta(years=3)
        
        # Calculate months remaining
        months_remaining = ((renewal_date.year - today.year) * 12 + 
                          renewal_date.month - today.month)
        
        # Check if less than 40 months remaining
        if months_remaining < 40:
            eligible_employees.append({
                'name': employee.get_full_name(),
                'department': employee.department.name if employee.department else 'No Department',
                'months': months_remaining,
                'id': employee.id
            })

    # If eligible employees found, create notification for HR
    if eligible_employees:
        # Sort by months remaining
        eligible_employees.sort(key=lambda x: x['months'])
        
        # Create message with proper line breaks
        message = "The following employees need contract renewal enabled:<br><br>"
        message += "<br>".join([
            f"{emp['name']} ({emp['department']}) - {emp['months']} months remaining"
            for emp in eligible_employees
        ])
        
        # Store employee IDs for enable action
        employee_ids = [emp['id'] for emp in eligible_employees]
        
        # Create notification for all HR users
        hr_users = user.groups.get(name='HR').user_set.all()
        logger.debug(f"Creating notifications for {hr_users.count()} HR users")
        
        for hr_user in hr_users:
            try:
                notification = ContractNotification.objects.create(
                    employee=hr_user.employee,
                    message=message,
                    metadata={'employee_ids': employee_ids, 'type': 'contract_renewal_enable'}
                )
                logger.debug(f"Created notification {notification.id} for HR user {hr_user.username}")
            except Exception as e:
                logger.error(f"Error creating notification for HR user {hr_user.username}: {str(e)}")

@receiver(user_logged_in)
def send_reminder_on_login(sender, user, request, **kwargs):
    now = timezone.now()
    three_days_ago = now - timedelta(days=3)

    # Get employee object if exists
    try:
        employee = user.employee
    except Employee.DoesNotExist:
        employee = None

    # Employee: contracts sent back for revision
    if user.groups.filter(name='Employee').exists() or (employee and not user.groups.exists()):
        sent_back_contracts = Contract.objects.filter(employee=employee, status='sent_back')
        if sent_back_contracts.exists():
            contract_links = [
                f'<a href="/contract/edit/{c.id}/" class="text-blue-600 hover:underline">Contract #{c.id}</a>'
                for c in sent_back_contracts
            ]
            message = (
                "You have contracts pending revision: " + ', '.join(contract_links) + ". Please edit and resubmit."
            )
            recent = ContractNotification.objects.filter(
                employee=employee,
                message__icontains='contracts pending revision',
                created_at__gte=three_days_ago
            ).exists()
            if not recent:
                ContractNotification.objects.create(
                    employee=employee,
                    message=message,
                    metadata={"type": "reminder", "contract_ids": [c.id for c in sent_back_contracts]}
                )
        # Contracts due for submission (no pending/draft/sent_back contract)
        pending = Contract.objects.filter(employee=employee, status__in=['pending', 'draft', 'sent_back']).exists()
        if not pending:
            recent = ContractNotification.objects.filter(
                employee=employee,
                message__icontains='contract renewal is due',
                created_at__gte=three_days_ago
            ).exists()
            if not recent:
                ContractNotification.objects.create(
                    employee=employee,
                    message="You have a contract renewal due. Please submit your contract renewal application.",
                    metadata={"type": "reminder"}
                )

    # HR: contracts in 'pending' status
    if user.groups.filter(name='HR').exists():
        pending_contracts = Contract.objects.filter(status='pending')
        if pending_contracts.exists():
            contract_links = [
                f'<a href="/contract/review/{c.id}/" class="text-blue-600 hover:underline">{c.employee.get_full_name()}</a>'
                for c in pending_contracts
            ]
            message = (
                "You have pending contracts to review for the following employees:<br>"
                + '<br>'.join(contract_links) + "<br>Please take action."
            )
            recent = ContractNotification.objects.filter(
                employee=user.employee,
                message__icontains='pending contracts to review for the following employees',
                created_at__gte=three_days_ago
            ).exists()
            if not recent:
                ContractNotification.objects.create(
                    employee=user.employee,
                    message=message,
                    metadata={"type": "reminder", "contract_ids": [c.id for c in pending_contracts]}
                )

    # Dean: contracts in 'dean_review' status for their department
    if user.groups.filter(name='Dean').exists():
        try:
            dean_employee = user.employee
            department = dean_employee.department
            contracts = Contract.objects.filter(status='dean_review', employee__department=department)
            if contracts.exists():
                contract_links = [
                    f'<a href="/contract/dean-review/{c.id}/" class="text-blue-600 hover:underline">{c.employee.get_full_name()}</a>'
                    for c in contracts
                ]
                message = (
                    "You have pending contracts to review for the following employees:<br>"
                    + '<br>'.join(contract_links) + "<br>Please take action."
                )
                recent = ContractNotification.objects.filter(
                    employee=dean_employee,
                    message__icontains='pending contracts to review for the following employees',
                    created_at__gte=three_days_ago
                ).exists()
                if not recent:
                    ContractNotification.objects.create(
                        employee=dean_employee,
                        message=message,
                        metadata={"type": "reminder", "contract_ids": [c.id for c in contracts]}
                    )
        except Employee.DoesNotExist:
            pass

    # SMT: contracts in 'smt_review' status
    if user.groups.filter(name='SMT').exists():
        smt_employee = user.employee
        contracts = Contract.objects.filter(status='smt_review')
        if contracts.exists():
            contract_links = [
                f'<a href="/contract/smt-review/{c.id}/" class="text-blue-600 hover:underline">{c.employee.get_full_name()}</a>'
                for c in contracts
            ]
            message = (
                "You have pending contracts to review for the following employees:<br>"
                + '<br>'.join(contract_links) + "<br>Please take action."
            )
            recent = ContractNotification.objects.filter(
                employee=smt_employee,
                message__icontains='pending contracts to review for the following employees',
                created_at__gte=three_days_ago
            ).exists()
            if not recent:
                ContractNotification.objects.create(
                    employee=smt_employee,
                    message=message,
                    metadata={"type": "reminder", "contract_ids": [c.id for c in contracts]}
                )