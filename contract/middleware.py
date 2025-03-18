from django.shortcuts import redirect
from django.urls import resolve
from django.contrib import messages

class ContractAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_url = resolve(request.path_info)
            
            # Only check contract-related URLs
            if current_url.app_name == 'contract':
                # Skip check for HR users
                if not request.user.groups.filter(name='HR').exists():
                    from .context_processors import get_employee_contract_status
                    
                    if not get_employee_contract_status(request.user.id):
                        messages.warning(request, 'Contract renewal access is currently disabled.')
                        return redirect('dashboard:index')

        response = self.get_response(request)
        return response 