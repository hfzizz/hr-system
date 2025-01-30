from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import ContractNotification, ContractRenewalStatus, Contract
from employees.models import Employee
import logging

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
        type_of_appointment='Contract',
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