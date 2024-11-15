from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee
from .forms import EmployeeForm
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin

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

class EmployeeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_create.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = 'employees.add_employee'
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to add employees.")
        return redirect('employees:employee_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Employee created successfully with ID: {self.object.employee_id}')
        return response

    def form_invalid(self, form):
        # Handle invalid form
        return super().form_invalid(form)

class EmployeeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/employee_edit.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = 'employees.change_employee'
    success_message = "Employee updated successfully"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Remove password fields for edit form
        if form.fields.get('password'):
            del form.fields['password']
        if form.fields.get('confirm_password'):
            del form.fields['confirm_password']
        if form.fields.get('username'):
            del form.fields['username']
        return form
