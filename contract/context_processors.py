from django.core.cache import cache
from employees.models import Employee
from datetime import datetime

def contract_status(request):
    show_contract = False
    contract_enabled = cache.get('contract_enabled', False)
    
    if request.user.is_authenticated:
        try:
            # Check if user is in HR group
            if 'HR' in request.user.groups.all().values_list('name', flat=True):
                show_contract = True
            else:
                employee = Employee.objects.get(user=request.user)
                current_year = datetime.now().year
                hire_year = employee.hire_date.year
                years_since_hire = current_year - hire_year
                
                # Check if current year is a 3-year interval from hire date
                is_renewal_year = years_since_hire > 0 and years_since_hire % 3 == 0
                
                # Show contract if enabled AND it's a renewal year
                show_contract = contract_enabled and is_renewal_year
                
        except Employee.DoesNotExist:
            show_contract = False
    
    return {
        'contract_enabled': show_contract
    }