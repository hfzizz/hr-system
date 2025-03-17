from django.core.cache import cache
from employees.models import Employee
from .models import ContractRenewalStatus, ContractNotification

def contract_status(request):
    show_contract = False
    is_hr = False
    is_dean = False
    is_smt = False
    
    if request.user.is_authenticated:
        try:
            # Check if user is in HR group
            is_hr = request.user.groups.filter(name='HR').exists()
            
            # Check if user is a dean or HOD
            is_dean = request.user.groups.filter(name__in=['Dean', 'HOD']).exists()
            
            # Check if user is in SMT group
            is_smt = request.user.groups.filter(name='SMT').exists()
            
            if is_hr or is_dean or is_smt:
                show_contract = True
            else:
                # For non-HR/non-dean/non-SMT users, check their individual contract status
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
        'is_hr_contract': is_hr,
        'is_dean': is_dean,
        'is_smt': is_smt
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

def contract_context(request):
    context = {}
    
    # Add SMT pending reviews count
    if request.user.is_authenticated and request.user.groups.filter(name='SMT').exists():
        from contract.models import Contract
        # Count contracts waiting for SMT review
        smt_pending_reviews = Contract.objects.filter(status='smt_review').count()
        context['smt_pending_reviews'] = smt_pending_reviews
        
        # Count approved contracts
        smt_approved_contracts = Contract.objects.filter(status='approved').count()
        context['smt_approved_contracts'] = smt_approved_contracts
        
        # Count rejected contracts
        smt_rejected_contracts = Contract.objects.filter(status='rejected').count()
        context['smt_rejected_contracts'] = smt_rejected_contracts
    
    return context