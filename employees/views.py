"""
Employee Management System Views.

This module contains all the view classes for handling employee management,
authentication, and administrative functions.

Classes:
    - Authentication Views (Login/Logout)
    - Department Management Views
    - Employee Management Views
    - Dashboard and Analytics Views
    - Profile Management Views
    - System Configuration Views
"""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee, Department, Qualification, Document, AppointmentType
from .forms import EmployeeForm, EmployeeProfileForm, QualificationForm, QualificationFormSet
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User
from django.db import transaction
import string
import random
from django.contrib.auth import login, authenticate
from django.shortcuts import render
from django.forms import modelformset_factory
from django.forms import inlineformset_factory
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q
from appraisals.models import Appraisal, AppraisalPeriod
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from employees.resume_parser import parse_resume
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.core.files.uploadedfile import UploadedFile
import os
from django.conf import settings
import json
from django.core.serializers.json import DjangoJSONEncoder

# Formset Configurations
QualificationFormSet = inlineformset_factory(
    Employee,
    Qualification,
    form=QualificationForm,
    extra=1,
    can_delete=True,
    fields=['degree_diploma', 'university_college', 'from_date', 'to_date'],
    validate_min=False,
    validate_max=False
)

DocumentFormSet = inlineformset_factory(
    Employee,
    Document,
    fields=['title', 'file'],
    extra=1,
    can_delete=True,
    validate_min=False,
    validate_max=False
)

class HRRequiredMixin(UserPassesTestMixin):
    """
    Mixin to enforce HR role-based access control.
    
    This mixin ensures that only users belonging to the HR group can access
    the protected views. It should be used in conjunction with LoginRequiredMixin.
    """
    def test_func(self):
        return self.request.user.groups.filter(name='HR').exists()

class DepartmentListView(LoginRequiredMixin, HRRequiredMixin, ListView):
    """
    Display a paginated list of all departments.
    
    Requires:
        - User authentication
        - HR group membership
    
    Template: employees/department_list.html
    Context: departments (queryset of Department objects)
    """
    model = Department
    template_name = 'employees/department_list.html'
    context_object_name = 'departments'

class DepartmentCreateView(LoginRequiredMixin, HRRequiredMixin, CreateView):
    model = Department
    template_name = 'employees/department_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('employees:department_list')

class DepartmentUpdateView(LoginRequiredMixin, HRRequiredMixin, UpdateView):
    model = Department
    template_name = 'employees/department_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('employees:department_list')

class DepartmentDeleteView(LoginRequiredMixin, HRRequiredMixin, DeleteView):
    model = Department
    template_name = 'employees/department_confirm_delete.html'
    success_url = reverse_lazy('employees:department_list')

class CustomLoginView(LoginView):
    """
    Custom authentication view with enhanced functionality.
    
    Features:
        - Combined username/email authentication
        - Custom form styling
        - Success/error message handling
        - Authenticated user redirection
    
    Template: auth/login.html
    """
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def get_success_url(self):
        return self.success_url

    def form_valid(self, form):
        """
        Process valid form submission and authenticate user.
        
        Args:
            form: The submitted authentication form
            
        Returns:
            HttpResponse: Redirects to success URL or renders form with errors
        """
        username = form.cleaned_data.get('login')
        password = form.cleaned_data.get('password')
        
        user = authenticate(
            self.request,
            username=username,
            password=password
        )
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Welcome back, {user.username}!')
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, f'Failed to authenticate user with username/email: {username}')
            return self.form_invalid(form)

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form with error messages."""
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Update the login field (instead of username) to match your form
        form.fields['login'] = form.fields.pop('username')  # Rename the field
        form.fields['login'].label = 'Username or Email'
        form.fields['login'].widget.attrs.update({
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
    """
    Display a comprehensive list of employees with advanced filtering and sorting.
    
    Features:
        - Configurable column display
        - Dynamic sorting
        - Multi-criteria filtering
        - Role-based access control
        - Optimized database queries
    
    Template: employees/employee_list.html
    Context:
        - employees: QuerySet of Employee objects
        - employee_columns: List of column configurations
        - table_config: Dictionary of table settings
        - filter options: Departments, posts, appointment types, etc.
    """
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'

    def get_context_data(self, **kwargs):
        """
        Prepare and return the context data for the employee list view.
        
        Returns:
            dict: Context containing:
                - Column configurations
                - Table settings
                - Filter options
                - Employee data
        """
        context = super().get_context_data(**kwargs)
        context['employee_columns'] = [
            {
                'id': 'employee_id',
                'label': 'Employee ID',
                'value': 'employee_id',
                'clickable': True,
                'url_name': 'employees:employee_detail'
            },
            {
                'id': 'name',
                'label': 'Name',
                'value': 'get_full_name',
                'clickable': True,
                'url_name': 'employees:employee_detail'
            },
            {
                'id': 'email',
                'label': 'Email',
                'value': 'email'
            },
            {
                'id': 'department',
                'label': 'Department',
                'value': 'department'
            },
            {
                'id': 'post',
                'label': 'Position',
                'value': 'post'
            },
            {
                'id': 'appointment_type',
                'label': 'Appointment',
                'value': 'appointment_type'
            },
            {
                'id': 'status',
                'label': 'Status',
                'value': 'get_employee_status_display'
            },
            {
                'id': 'hire_date',
                'label': 'Hire Date',
                'value': 'hire_date',
                'type': 'date',
                'date_format': '%d %b %Y'
            },
            {
                'id': 'ic_no',
                'label': 'IC Number',
                'value': 'ic_no'
            },
            {
                'id': 'ic_colour',
                'label': 'IC Colour',
                'value': 'get_ic_colour_display'
            },
            {
                'id': 'phone_number',
                'label': 'Phone',
                'value': 'phone_number'
            }
        ]

        # Table configuration
        context['table_config'] = {
            'update_url_name': 'employees:employee_update',
            'status_column': 'status',
            'status_field': 'employee_status',
            'enable_sorting': True,
            'default_sort': '-hire_date',
            'enable_reorder': True,  # Enable/disable column reordering
        }

        # Filter options - only include if they exist in your database
        context['departments'] = Department.objects.all()
        context['posts'] = Employee.objects.values_list('post', flat=True).distinct()
        if hasattr(Employee, 'appointment_type'):
            context['appointment_types'] = AppointmentType.objects.all()
        context['ic_colours'] = dict(Employee.ICColour.choices)
        context['statuses'] = dict(Employee.Status.choices)

        return context

    def get_queryset(self):
        return Employee.objects.select_related('department', 'appointment__type_of_appointment').all()
    
    def employee_list(request):
        employee_columns = [
            {'id': 'employee_id', 'label': 'Employee ID', 'value': 'employee_id'},
            {'id': 'name', 'label': 'Name', 'value': 'get_full_name'},
            {'id': 'email', 'label': 'Email', 'value': 'email'},
            # ... add all your columns here
        ]
    
        context = {
            'employees': Employee.objects.all(),
            'departments': Department.objects.all(),
            'posts': Employee.POST_CHOICES,
            'employee_columns': employee_columns,
    }
        return render(request, 'employees/employee_list.html', context)

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard displaying system analytics and recent activities.
    
    Provides:
        - Employee statistics
        - Department analytics
        - Appraisal status overview
        - Recent employee additions
        - Latest appraisal activities
    
    Access: All authenticated users
    Template: employees/dashboard.html
    """
    template_name = 'employees/dashboard.html'

    def get_context_data(self, **kwargs):
        """
        Gather and prepare dashboard analytics data.
        
        Returns:
            dict: Context containing:
                - Statistical counters
                - Recent activity lists
                - Role-specific information
        """
        context = super().get_context_data(**kwargs)
        
        # Core statistics
        context['total_employees'] = Employee.objects.count()
        context['total_departments'] = Department.objects.count()
        
        # Get departments with employee counts, ordered by count
        context['department_data'] = Department.objects.annotate(
            employee_count=Count('employees')
        ).order_by('-employee_count')
        
        # Appraisal analytics
        active_period = AppraisalPeriod.objects.filter(is_active=True).first()
        if active_period:
            context['ongoing_appraisals'] = Appraisal.objects.filter(
                status='in_progress'
            ).count()
            context['pending_reviews'] = Appraisal.objects.filter(
                status='pending'
            ).count()
        else:
            context['ongoing_appraisals'] = 0
            context['pending_reviews'] = 0

        # Get recent employees (last 5)
        context['recent_employees'] = Employee.objects.select_related('department').order_by('-hire_date')[:5]

        # Get recent appraisals - Removed period from select_related
        if self.request.user.groups.filter(name='HR').exists():
            # HR sees all recent appraisals
            context['recent_appraisals'] = Appraisal.objects.select_related(
                'employee', 'appraiser'
            ).order_by('-date_created')[:5]
        else:
            # Regular users see only their appraisals and ones they need to review
            context['recent_appraisals'] = Appraisal.objects.filter(
                Q(employee=self.request.user.employee) |
                Q(appraiser=self.request.user.employee)  # Changed from reviewer to appraiser
            ).select_related(
                'employee', 'appraiser'
            ).order_by('-date_created')[:5]

        # Get status counts
        status_counts = Employee.objects.values('employee_status').annotate(
            count=Count('id')
        )

        # Format status data as list of dictionaries
        status_data = [
            {'status': 'active', 'count': 0},
            {'status': 'on_leave', 'count': 0},
            {'status': 'inactive', 'count': 0}
        ]

        # Update with actual counts
        for item in status_counts:
            for status in status_data:
                if status['status'] == item['employee_status']:
                    status['count'] = item['count']

        # Add to context
        context['status_data'] = status_data

        return context

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

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
        
        if self.request.POST:
            context['document_formset'] = DocumentFormSet(
                self.request.POST,
                self.request.FILES,
                prefix='document_set'
            )
        else:
            context['document_formset'] = DocumentFormSet(
                prefix='document_set'
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        document_formset = context['document_formset']
        
        if document_formset.is_valid():
            try:
                # Generate a random password if none provided
                password = form.cleaned_data.get('password')
                if not password:
                    password = self.generate_random_password()

                # Create the User instance first
                username = form.cleaned_data['username']
                email = form.cleaned_data['email']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )

                # Save employee
                employee = form.save(commit=False)
                employee.user = user
                employee.save()
                form.save_m2m()

                # Save documents
                document_formset.instance = employee
                document_instances = document_formset.save(commit=False)
                for document in document_instances:
                    document.employee = employee
                    document.save()

                messages.success(
                    self.request, 
                    f'Employee created successfully. Username: {user.username}. Please securely share the credentials with the employee.'
                )
                
                return super().form_valid(form)
            except Exception as e:
                print(f"Error creating employee: {str(e)}")
                messages.error(self.request, f"Error creating employee: {str(e)}")
                return super().form_invalid(form)
        else:
            messages.error(self.request, "Please correct the errors in the documents section.")
            return self.form_invalid(form)

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
    permission_required = 'employees.change_employee'
    success_message = "Employee updated successfully"

    def get_success_url(self):
        return reverse_lazy('employees:employee_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if form.fields.get('password'):
            del form.fields['password']
        if form.fields.get('confirm_password'):
            del form.fields['confirm_password']
        if form.fields.get('username'):
            del form.fields['username']
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['qualification_formset'] = QualificationFormSet(
                self.request.POST,
                instance=self.object,
                prefix='qualification_set'
            )
            context['document_formset'] = DocumentFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                prefix='document_set'
            )
        else:
            context['qualification_formset'] = QualificationFormSet(
                instance=self.object,
                prefix='qualification_set'
            )
            context['document_formset'] = DocumentFormSet(
                instance=self.object,
                prefix='document_set'
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        qualification_formset = context['qualification_formset']
        document_formset = context['document_formset']
        
        if qualification_formset.is_valid() and document_formset.is_valid():
            self.object = form.save()
            
            # Save qualifications
            qualification_formset.instance = self.object
            qualification_instances = qualification_formset.save(commit=False)
            
            # Delete marked qualifications
            for obj in qualification_formset.deleted_objects:
                obj.delete()
            
            # Save new/updated qualifications
            for qualification in qualification_instances:
                qualification.employee = self.object
                qualification.save()
            
            # Save documents
            document_formset.instance = self.object
            document_instances = document_formset.save(commit=False)
            
            # Delete marked documents
            for obj in document_formset.deleted_objects:
                obj.delete()
            
            # Save new/updated documents
            for document in document_instances:
                document.employee = self.object
                document.save()
            
            return super().form_valid(form)
        else:
            if not qualification_formset.is_valid():
                messages.error(self.request, "Please correct the errors in the qualifications section.")
            if not document_formset.is_valid():
                messages.error(self.request, "Please correct the errors in the documents section.")
            return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data()
        qualification_formset = context['qualification_formset']
        if not qualification_formset.is_valid():
            messages.error(self.request, "Please correct the errors in the qualifications section.")
        return super().form_invalid(form)

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

class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'

    def get_queryset(self):
        # Prefetch the documents to optimize queries
        return super().get_queryset().prefetch_related('documents')

class SettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    System configuration interface for HR administrators.
    
    Provides access to:
        - System settings
        - Configuration options
        - Administrative controls
    
    Access: HR personnel only
    Template: employees/settings.html
    """
    template_name = 'employees/settings.html'
    
    def test_func(self):
        """
        Verify user has HR privileges.
        
        Returns:
            bool: True if user belongs to HR group, False otherwise
        """
        return self.request.user.groups.filter(name='HR').exists()
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access settings.")
        return redirect('dashboard')

class ResumeParserView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        print("Received POST request")  # Debug print
        
        if 'resume' not in request.FILES:
            print("No file in request")  # Debug print
            return JsonResponse({
                'status': 'error',
                'message': 'No resume file provided'
            }, status=400)
            
        try:
            resume_file = request.FILES['resume']
            print(f"Processing file: {resume_file.name}")  # Debug print
            
            # Verify file type
            if not resume_file.name.lower().endswith('.pdf'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only PDF files are allowed'
                }, status=400)

            # Create a unique filename
            fs = FileSystemStorage(location=settings.TEMP_UPLOAD_DIR)
            filename = fs.get_valid_name(resume_file.name)
            
            # Save the file temporarily
            file_path = fs.save(filename, resume_file)
            full_path = fs.path(file_path)
            
            try:
                # Parse the resume
                parsed_data = parse_resume(full_path)
                print(f"Parsed data: {parsed_data}")  # Debug print
                
                # Ensure all values are strings and JSON serializable
                cleaned_data = {}
                for key, value in parsed_data.items():
                    if value is not None:
                        try:
                            # Test JSON serialization
                            json.dumps(str(value))
                            cleaned_data[key] = str(value)
                        except (TypeError, ValueError):
                            cleaned_data[key] = ''
                    else:
                        cleaned_data[key] = ''
                
                response_data = {
                    'status': 'success',
                    'data': cleaned_data
                }
                
                # Test full response serialization
                json.dumps(response_data)
                
                return JsonResponse(response_data)
                    
            except Exception as e:
                print(f"Error parsing resume: {str(e)}")  # Debug print
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
            finally:
                # Clean up: remove the temporary file
                if os.path.exists(full_path):
                    os.remove(full_path)
                
        except Exception as e:
            print(f"Error handling file: {str(e)}")  # Debug print
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

def dashboard(request):
    # Get department counts
    department_data = Employee.objects.values(
        'department__name'
    ).annotate(
        employee_count=Count('id')
    ).order_by('-employee_count')
    
    # Format department data
    formatted_department_data = []
    for dept in department_data:
        formatted_department_data.append({
            'name': dept['department__name'],
            'employee_count': dept['employee_count']
        })

    # Get status counts
    all_statuses = dict(Employee.Status.choices)
    
    # Get current counts
    status_counts = Employee.objects.values('employee_status').annotate(
        count=Count('id')
    )
    
    # Create a dictionary of counts
    count_dict = {item['employee_status']: item['count'] for item in status_counts}
    
    # Format status data
    formatted_status_data = []
    for status_code, status_name in all_statuses.items():
        formatted_status_data.append({
            'status': status_code,
            'name': status_name,
            'count': count_dict.get(status_code, 0)
        })
    
    # Get position counts with debug prints
    position_counts = Employee.objects.values('position').annotate(
        employee_count=Count('id')
    ).order_by('-employee_count')
    
    print("DEBUG - Raw Position Counts:", position_counts)
    print("DEBUG - Position Counts Query:", position_counts.query)
    
    # Format position data
    formatted_position_data = []
    for pos in position_counts:
        formatted_position_data.append({
            'name': dict(Employee._meta.get_field('position').choices).get(pos['position'], pos['position']),
            'employee_count': pos['employee_count']
        })
    
    context = {
        'department_data': formatted_department_data,
        'status_data': formatted_status_data,
        'position_data': formatted_position_data,
        'total_employees': Employee.objects.count()
    }
    return render(request, 'employees/dashboard.html', context)


