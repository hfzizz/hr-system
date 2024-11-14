from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')  # or 'employee_list'

    def get_success_url(self):
        return self.success_url

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    login_url = 'login'  # Redirect to login if user is not authenticated

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/dashboard.html'
    login_url = 'login'

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/profile.html'
    login_url = 'login'
