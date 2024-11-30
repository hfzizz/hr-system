from django.core.cache import cache
from employees.models import Employee
from .models import ContractRenewalStatus

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
                if employee.type_of_appointment == 'Contract':  # Only show for contract employees
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