from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee, Department
from .forms import EmployeeForm, EmployeeProfileForm
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import User
from django.db import transaction
import string
import random

class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def get_success_url(self):
        return self.success_url

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        # Call parent's form_valid to complete the login process first
        response = super().form_valid(form)
        
        # Get the authenticated user and welcome them by username
        user = form.get_user()
        messages.success(self.request, f'Welcome back, {user.username}!')
            
        return response

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form with a generic error message."""
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Update the username field label and placeholder
        form.fields['username'].label = 'Username or Email'
        form.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username',
            'class': 'block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
        })
        # Update password field styling
        form.fields['password'].widget.attrs.update({
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'class': 'block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
        })
        return form

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        # Get unique positions
        context['positions'] = Employee.objects.values_list('position', flat=True).distinct()
        return context

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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Employee'
        context['button_label'] = 'Create'
        return context

    def form_valid(self, form):
        try:
            # Generate a random password if none provided
            password = form.cleaned_data.get('password')
            if not password:
                password = self.generate_random_password()

            # Create user account
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']

            # Create the user first
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Set the user for the employee
            employee = form.save(commit=False)
            employee.user = user
            employee.save()
            
            # Save many-to-many relationships
            form.save_m2m()

            # Add success message
            messages.success(
                self.request, 
                f'Employee created successfully. Username: {username}. Please securely share the credentials with the employee.'
            )
            
            return super().form_valid(form)
        except Exception as e:
            # Add error message and print for debugging
            print(f"Error creating employee: {str(e)}")
            messages.error(self.request, f"Error creating employee: {str(e)}")
            return super().form_invalid(form)

    def generate_random_password(self, length=12):
        """Generate a random password with letters, digits, and special characters"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choice(characters) for _ in range(length))

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to add employees.")
        return redirect('employees:employee_list')

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            # Add current roles to context
            context['current_roles'] = self.object.roles.all()
        return context

class EmployeeProfileView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/profile.html'
    context_object_name = 'employee'

    def get_object(self, queryset=None):
        return self.request.user.employee

class EmployeeProfileEditView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employees/profile_edit.html'
    success_url = reverse_lazy('employees:profile')

    def get_object(self):
        return self.request.user.employee

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update the username
        if 'username' in form.cleaned_data:
            new_username = form.cleaned_data['username']
            user = self.object.user
            if user.username != new_username:
                user.username = new_username
                user.save()
                messages.success(self.request, 'Profile updated successfully. Your username has been changed.')
            else:
                messages.success(self.request, 'Profile updated successfully.')
                
        return response
