from django.core.cache import cache
from employees.models import Employee
from .models import ContractRenewalStatus, ContractNotification

def contract_status(request):
    show_contract = False
    is_hr = False
    
    if request.user.is_authenticated:
        try:
            # Check if user is in HR group
            is_hr = request.user.groups.filter(name='HR').exists()
            
            if is_hr:
                show_contract = True
            else:
                # For non-HR users, check their individual contract status
                employee = Employee.objects.get(user=request.user)
                # Check if employee has contract appointment type
                if hasattr(employee, 'appointment_type') and employee.appointment_type and employee.appointment_type.name == 'Contract':
                    contract_status = ContractRenewalStatus.objects.filter(
                        employee=employee
                    ).first()
                    show_contract = contract_status.is_enabled if contract_status else False
                
        except Employee.DoesNotExist:
            show_contract = False
    
    return {
        'contract_enabled': show_contract,
        'is_hr_contract': is_hr
    }

def notifications(request):
    unread_count = 0
    if request.user.is_authenticated and hasattr(request.user, 'employee'):
        unread_count = ContractNotification.objects.filter(
            employee=request.user.employee,
            read=False
        ).count()
    
    return {
        'unread_notifications_count': unread_count
    }