from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy

class HRPermRequiredMixin(LoginRequiredMixin):
    """
    Mixin to verify that the user is both authenticated and has HR role.
    Inherits from LoginRequiredMixin to handle unauthenticated users.
    """
    login_url = reverse_lazy('login')  # Specify your login URL
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        try:
            # Check if userprofile exists and has HR role
            if not hasattr(request.user, 'userprofile') or \
               request.user.userprofile.role != 'HR':
                raise PermissionDenied("You must have HR permissions to access this page.")
        except AttributeError:
            raise PermissionDenied("User profile not configured properly.")
            
        return super().dispatch(request, *args, **kwargs)