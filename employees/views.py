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
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee, Department, Qualification, Document, Publication
from .forms import EmployeeProfileForm, ProfileForm, QualificationForm, QualificationFormSet, PublicationFormSet, PublicationForm
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
from django.db import models
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.template import TemplateDoesNotExist
from unstructured.partition.pdf import partition_pdf
from transformers import pipeline
import tempfile
from PyPDF2 import PdfReader
from io import BytesIO
from unstructured.staging.base import convert_to_dict
import logging
import pdfplumber
import re
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import csv
from django.db import IntegrityError
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

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

class EmployeeListView(LoginRequiredMixin, HRRequiredMixin, ListView):
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
            },
            {
                'id': 'actions',
                'label': 'Actions',
                'value': 'actions',
                'sortable': False,
                'visible': True
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
        context['posts'] = Employee.POST_CHOICES
        context['appointment_types'] = Employee.objects.values_list('appointment_type', flat=True).distinct()
        context['ic_colours'] = dict(Employee.ICColour.choices)
        context['statuses'] = dict(Employee.Status.choices)

        return context

    def get_queryset(self):
        # Update this line too
        return Employee.objects.select_related('department').all()
    
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
    # resume
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
        
        # Get departments with employee counts
        department_data = Department.objects.annotate(
            employee_count=Count('employees')
        ).order_by('name')
        
        # Get positions (posts) with employee counts
        positions = Employee.objects.values('post').annotate(
            employee_count=Count('id'),
            name=models.F('post')  # Alias 'post' as 'name' to match template
        ).exclude(
            post__isnull=True
        ).exclude(
            post__exact=''
        ).order_by('post')

        # Get appointment types with employee counts
        appointments = Employee.objects.values('appointment_type') \
            .annotate(employee_count=Count('id')) \
            .order_by('appointment_type')
        
        context.update({
            'department_data': department_data,
            'department_count': Department.objects.count(),
            'positions': positions,
            'position_count': positions.count(),
            'appointments': appointments,
            'appointment_count': Employee.objects.values('appointment_type').distinct().count(),
        })

        # Appraisal analytics (removed actual queries, just set to 0 or empty for display)
        context['ongoing_appraisals'] = 0
        context['pending_reviews'] = 0
        context['recent_appraisals'] = []

        # Get recent employees (last 5)
        context['recent_employees'] = Employee.objects.select_related('department').order_by('-hire_date')[:5]

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

class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/profile.html'
    context_object_name = 'employee'

    def get_object(self):
        return self.request.user.employee
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fields'] = [
            ("Username", self.object.user.username),
            ("Full name", f"{self.object.first_name} {self.object.last_name}"),
            ("Email address", self.object.email),
            ("Phone number", self.object.phone_number),
            ("IC Number", self.object.ic_no),
            ("IC Colour", self.object.get_ic_colour_display()),
            ("Type of Appointment", self.object.appointment_type),
            ("Department", self.object.department),
            ("Position", self.object.post),
            ("Roles", "roles"),  # Special handling in template
            ("Address", self.object.address),
            ("Hire date", self.object.hire_date),
        ]
        return context
    

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    form_class = ProfileForm
    template_name = 'employees/profile_edit.html'

    def get_success_url(self):
        return reverse_lazy('employees:profile', kwargs={'pk': self.request.user.pk}) 
    
    def get_object(self):
        try:
            return self.request.user.employee
        except Employee.DoesNotExist:
            raise Http404("Employee profile not found.")

    def get_context_data(self, **kwargs):
        """Ensure 'employee' is included in the context."""
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()  # Pass employee object to the template
        return context

    def form_valid(self, form):
        """Handle form submission when valid."""
        if form.is_valid():
            response = super().form_valid(form)
            messages.success(self.request, 'Profile updated successfully!')
            return response
        else:
            return self.render_to_response(self.get_context_data(form=form))

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'employees/change_password.html'
    success_url = reverse_lazy('employees:profile')

    def form_valid(self, form):
        messages.success(self.request, 'Your password was successfully updated!')
        return super().form_valid(form)

class EmployeeCreateView(LoginRequiredMixin, HRRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeProfileForm
    template_name = 'employees/employee_create.html'
    success_url = reverse_lazy('employees:employee_list')

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
                request.session['created_credentials'] = [{'email': email, 'password': password}]
                return super().form_valid(form)
            except Exception as e:
                logger.error(f"Error creating employee: {str(e)}")
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

class EmployeeDetailView(LoginRequiredMixin, HRRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'

    def get_queryset(self):
        # Prefetch the documents to optimize queries
        return super().get_queryset().prefetch_related('documents')

class EmployeeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Employee
    form_class = EmployeeProfileForm
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
            context['publication_formset'] = PublicationFormSet(
                self.request.POST,
                instance=self.object,
                prefix='publication_set'
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
            context['publication_formset'] = PublicationFormSet(
                instance=self.object,
                prefix='publication_set'
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        qualification_formset = context['qualification_formset']
        document_formset = context['document_formset']
        publication_formset = context['publication_formset']
        
        if qualification_formset.is_valid() and document_formset.is_valid() and publication_formset.is_valid():
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

            # Save publications
            publication_formset.instance = self.object
            publication_instances = publication_formset.save(commit=False)

             # Delete marked qualifications
            for obj in publication_formset.deleted_objects:
                obj.delete()
            
            # Save new/updated qualifications
            for publication in publication_instances:
                publication.employee = self.object
                publication.save()
            
            
            return super().form_valid(form)
        else:
            if not qualification_formset.is_valid():
                messages.error(self.request, "Please correct the errors in the qualifications section.")
            if not document_formset.is_valid():
                messages.error(self.request, "Please correct the errors in the documents section.")
            if not publication_formset.is_valid():
                    messages.error(self.request, "Please correct the errors in the publications section.")
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error updating the employee.")
        return super().form_invalid(form)
    
@login_required
@require_http_methods(["GET"])
def load_publication_form(request):
    source_type = request.GET.get('source_type')
    context = {
        'source_type': source_type,
        'form': PublicationForm()
    }
    return TemplateResponse(
        request,
        'employees/partials/_publication_fields.html',  # Updated path
        context
    )
@login_required
@require_http_methods(["GET"])
def add_publication_form(request):
    """Add a new publication form dynamically"""
    total_forms = request.GET.get('total_forms', '0')
    index = int(total_forms)
    
    form = PublicationForm(prefix=f'publication_set-{index}')
    
    context = {
        'form': form,
        'index': index
    }
    
    return TemplateResponse(
        request,
        'employees/partials/_publication_form.html',
        context
    )

@login_required
@require_http_methods(["GET"])
def load_type_fields_publication(request):
    # Get publication_type from request - check multiple possible parameter names
    publication_type = None
    
    # First check direct parameter
    if request.GET.get('publication_type'):
        publication_type = request.GET.get('publication_type')
    
    # If not found, check for formset style parameters
    if not publication_type or publication_type == 'undefined':
        for key in request.GET:
            if key.endswith('-pub_type'):
                publication_type = request.GET.get(key)
                break
    
    index = request.GET.get('index', '0')
    
    print(f"load_type_fields_publication - publication_type={publication_type}, index={index}")
    print(f"All request params: {dict(request.GET.items())}")
    
    context = {
        'pub_type': publication_type,
        'form': PublicationForm(),
        'index': index
    }
    
    # Add debug information
    context['debug'] = {
        'request_params': dict(request.GET.items()),
        'publication_type_param': publication_type
    }
    
    return TemplateResponse(
        request,
        'employees/partials/_type_specific_fields.html',
        context
    )

@login_required
@require_http_methods(["DELETE"])
def delete_publication(request, pk):
    """
    Delete a publication entry.
    Called via HTMX when delete button is clicked.
    """
    try:
        publication = Publication.objects.get(pk=pk)
        publication.delete()
        return HttpResponse(status=204)
    except Publication.DoesNotExist:
        return HttpResponse(status=404)

@login_required
@require_http_methods(["GET"])
def fetch_publication_metadata(request):
    """
    Fetch publication metadata from external sources.
    Called via HTMX when source ID field loses focus.
    """
    source_type = request.GET.get('source_type')
    source_id = request.GET.get('source_id')
    
    # Add your logic to fetch metadata based on source type
    # This is just a placeholder example
    metadata = {
        'title': 'Sample Publication',
        'authors': 'Author 1, Author 2',
        'year': '2023',
        'journal': 'Sample Journal'
    }
    
    context = {
        'metadata': metadata,
        'source_type': source_type
    }
    return TemplateResponse(
        request,
        'employee/partials/_publication_preview.html',
        context
    )



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
        print("\n=== Resume Parser View Debug ===")
        print("Received POST request")
        if 'resume' not in request.FILES:
            print("No file in request")
            return JsonResponse({
                'status': 'error',
                'message': 'No resume file provided'
            }, status=400)
        full_path = None
        try:
            resume_file = request.FILES['resume']
            print(f"Processing file: {resume_file.name}")
            print(f"File size: {resume_file.size} bytes")
            print(f"Content type: {resume_file.content_type}")
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
            print(f"Saved file to: {full_path}")
            try:
                # Parse the resume
                print("\n=== Resume Parsing ===")
                parsed_data = parse_resume(full_path)
                print(f"Raw parsed data type: {type(parsed_data)}")
                print(f"Raw parsed data keys: {parsed_data.keys() if isinstance(parsed_data, dict) else 'Not a dictionary'}")
                print("Raw parsed data content:")
                print(json.dumps(parsed_data, indent=2))
                # Transform the parsed data into form-compatible format
                print("\n=== Data Transformation ===")
                ic_colour_map = {
                    'yellow': 'Y',
                    'purple': 'P',
                    'green': 'G',
                    'red': 'R'
                }
                parsed_colour = (parsed_data.get('personal_info', {}).get('ic_colour', '').strip().lower())
                employee_data = {
                    'first_name': parsed_data.get('personal_info', {}).get('first_name', ''),
                    'last_name': parsed_data.get('personal_info', {}).get('last_name', ''),
                    'email': parsed_data.get('personal_info', {}).get('email', ''),
                    'phone_number': parsed_data.get('personal_info', {}).get('phone_number', ''),
                    'address': parsed_data.get('personal_info', {}).get('address', ''),
                    'ic_no': parsed_data.get('personal_info', {}).get('ic_no', ''),
                    'date_of_birth': parsed_data.get('personal_info', {}).get('date_of_birth', ''),
                    'gender': parsed_data.get('personal_info', {}).get('gender', ''),
                    'department': parsed_data.get('employment', {}).get('department', ''),
                    'post': parsed_data.get('employment', {}).get('post', ''),
                    'appointment_type': parsed_data.get('employment', {}).get('appointment_type', ''),
                    'employee_status': parsed_data.get('employment', {}).get('employee_status', ''),
                    'hire_date': parsed_data.get('employment', {}).get('hire_date', ''),
                    'salary': parsed_data.get('employment', {}).get('salary', ''),
                    'ic_colour': ic_colour_map.get(parsed_colour, None)
                }
                # Generate a username from email or name
                if employee_data['email']:
                    employee_data['username'] = employee_data['email'].split('@')[0]
                elif employee_data['first_name'] and employee_data['last_name']:
                    employee_data['username'] = f"{employee_data['first_name']}{employee_data['last_name']}".lower()
                print("\nTransformed form data:")
                print(json.dumps(employee_data, indent=2))
                print(f"Form data type: {type(employee_data)}")
                # Check which fields have values
                populated_fields = {k: v for k, v in employee_data.items() if v}
                print(f"\nFields with values ({len(populated_fields)}):")
                for key, value in populated_fields.items():
                    print(f"- {key}: {value}")
                # Prepare the response
                response_data = {
                    'status': 'success',
                    'data': employee_data,
                    'jsonb_data': parsed_data
                }
                print("\n=== Response Data ===")
                print(f"Response structure: {list(response_data.keys())}")
                print(f"Response data type: {type(response_data)}")
                print(f"Form data in response type: {type(response_data['data'])}")
                print(f"JSONB data in response type: {type(response_data['jsonb_data'])}")
                return JsonResponse(response_data)
            except Exception as e:
                print(f"\nError parsing resume: {str(e)}")
                print(f"Error type: {type(e)}")
        except Exception as e:
            print(f"\nError handling file: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print("Traceback:")
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

@login_required
def employee_search(request):
    """
    Search for employees based on query parameters.
    """
    query = request.GET.get('q', '')
    if query:
        employees = Employee.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(employee_id__icontains=query) |
            Q(email__icontains=query)
        )
    else:
        employees = Employee.objects.none()
    
    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'search_query': query
    })

@login_required
@require_http_methods(["POST"])
def employee_delete(request, employee_id):
    """
    Delete an employee record.
    """
    try:
        employee = Employee.objects.get(id=employee_id)
        employee.delete()
        messages.success(request, f'Employee {employee.get_full_name()} has been deleted successfully.')
    except Employee.DoesNotExist:
        messages.error(request, 'Employee not found.')
    
    return redirect('employees:employee_list')

@csrf_exempt
@require_POST
def parse_pdf(request):
    if 'pdf' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No PDF file provided'}, status=400)
    pdf_file = request.FILES['pdf']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        for chunk in pdf_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        # Extract all text from the PDF
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # Helper function to extract section by keyword
        def extract_section(keyword, text):
            # Adjust the pattern as needed for your PDF's formatting
            pattern = rf"{re.escape(keyword)}\n(.*?)(?=\n\d+\.\s|$)"
            match = re.search(pattern, text, re.DOTALL)
            return match.group(1).strip() if match else ""

        # Map your form fields to keywords in the PDF (adjust these to match your actual PDF)
        parsed_data = {
            'teaching_philosophy_full': extract_section("1. Teaching Philosophy", text),
            'learning_outcome_full': extract_section("2. Strategies, Objective, Methodology", text),
            'instructional_methodology_full': extract_section("b) Instructional methodology (including the use of e-learning or experiential learning projects).", text),
            'other_means_to_enhance_learning_full': extract_section("c) Other means to enhance learning.", text),
            'other_teaching_full': extract_section("c) Other teaching (e.g. Lifelong Learning, in-service, EDPMMO, EDPSGO, etc). Please provide details.", text),
            'academic_leadership_full': extract_section("4. Teaching Achievement and Academic Leadership", text),
            'contribution_teaching_materials_full': extract_section("b) Contribution to development of teaching materials (including published cases, textbooks, production of teaching materials, software, pedagogical articles, teaching methodologies, etc)", text),
            'future_teaching_goals_full': extract_section("a) Teaching goals for the next 3 years", text),
            'future_steps_improve_teaching_full': extract_section("b) Steps taken to improve teaching", text),
        }

        return JsonResponse({'status': 'success', 'data': parsed_data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        os.remove(tmp_path)

def bulk_add(request):
    employees = request.session.get('bulk_employees', [])
    already_exists = request.session.get('bulk_already_exists', [])
    return render(request, 'employees/bulk_add.html', {'employees': employees, 'already_exists': already_exists})

@csrf_exempt
def bulk_upload_parse(request):
    if request.method == 'POST':
        files = request.FILES.getlist('resume_folder')
        parsed_employees = []
        for f in files:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                for chunk in f.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            # Parse PDF (use your parse_pdf logic)
            employee_data = parse_employee_from_pdf(tmp_path)
            print("Parsed employee data:", employee_data)
            if employee_data and any(employee_data.values()):
                parsed_employees.append(employee_data)
            os.remove(tmp_path)
        # Store in session for validation
        request.session['bulk_employees'] = parsed_employees
        return render(request, 'employees/bulk_add.html', {'employees': parsed_employees})
    else:
        return render(request, 'employees/bulk_add.html')

@require_POST
def bulk_confirm_create(request):
    # Get original parsed data from session
    session_employees = request.session.get('bulk_employees', [])
    total = int(request.POST.get('total_employees', 0))
    merged_employees = []
    created_credentials = []
    already_exists = []

    for i in range(total):
        # Get editable fields from POST
        post_data = {
            'first_name': request.POST.get(f'employees-{i}-first_name'),
            'last_name': request.POST.get(f'employees-{i}-last_name'),
            'email': request.POST.get(f'employees-{i}-email'),
            'ic_no': request.POST.get(f'employees-{i}-ic_no'),
            'post': request.POST.get(f'employees-{i}-post'),
        }
        # Get original data for this employee (by index)
        original = session_employees[i] if i < len(session_employees) else {}
        # Merge: use POST value if present, else original
        merged = {**original, **{k: v for k, v in post_data.items() if v is not None}}
        merged_employees.append(merged)

    # Create users and employees
    for idx, data in enumerate(merged_employees):
        # Generate a username (from email or name)
        username = (data.get('first_name', '') or '') + (data.get('last_name', '') or '')
        username = username.lower() or data.get('ic_no') or None
        password = User.objects.make_random_password()
        try:
            user = User.objects.create_user(
                username=username,
                email=data.get('email', ''),
                password=password,
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', '')
            )
            # Send credentials email
            if data.get('email'):
                try:
                    send_mail(
                        subject='Your Employee Account Credentials',
                        message=(
                            f"Dear {data.get('first_name', '')},\n\n"
                            f"Your employee account has been created.\n"
                            f"Username: {username}\n"
                            f"Password: {password}\n\n"
                            "Please log in and change your password as soon as possible.\n\n"
                            "Best regards,\nHR Department"
                        ),
                        from_email=None,  # Uses DEFAULT_FROM_EMAIL
                        recipient_list=[data.get('email')],
                        fail_silently=False,
                    )
                except Exception as e:
                    print(f"Failed to send email to {data.get('email')}: {e}")
        except IntegrityError:
            already_exists.append({
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'email': data.get('email', ''),
                'ic_no': data.get('ic_no', ''),
                'index': idx,
            })
            continue
        # Get or create department if present
        department = data.get('department')
        if isinstance(department, str) and department:
            department_obj, _ = Department.objects.get_or_create(name=department)
        else:
            department_obj = department if department else None

        # Create Employee
        Employee.objects.create(
            user=user,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            ic_no=data.get('ic_no', ''),
            ic_colour=data.get('ic_colour'),
            date_of_birth=data.get('date_of_birth'),
            department=department_obj,
            post=data.get('post'),
            appointment_type=data.get('appointment_type'),
            salary=data.get('salary') or 0,
            hire_date=data.get('hire_date'),
            employee_status=data.get('employee_status', 'active'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
        )
        created_credentials.append({'email': data.get('email', ''), 'password': password})

    # Clean up session
    if 'bulk_employees' in request.session:
        del request.session['bulk_employees']
    request.session['created_credentials'] = created_credentials
    # Store already_exists persistently in session
    if already_exists:
        request.session['bulk_already_exists'] = already_exists
    elif 'bulk_already_exists' in request.session:
        del request.session['bulk_already_exists']
    # Show credentials and already_exists on the same page
    return render(request, 'employees/bulk_add.html', {
        'created_credentials': created_credentials,
        'already_exists': already_exists,
        'employees': []
    })

def bulk_cancel(request):
    if 'bulk_employees' in request.session:
        del request.session['bulk_employees']
    return redirect('employees:employee_list')

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    # Try several common formats
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue
    return None

def parse_employee_from_pdf(pdf_path):
    import pdfplumber
    import re
    from employees.models import Department

    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Name
    name = None
    for line in lines:
        if line.startswith("A1. Name"):
            name = line.split(":", 1)[-1].strip()
            break
    name_parts = name.split() if name else []
    first_name = name_parts[0] if name_parts else None
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else None

    # IC No & Colour (robust extraction)
    ic_no, ic_colour = None, None
    ic_pattern = re.compile(r"([0-9\-]+)[,\s]+(Yellow|Purple|Green|Red)", re.IGNORECASE)
    for line in lines:
        if "IC. No & colour: " in line:
            # Try to extract using regex
            match = ic_pattern.search(line)
            if match:
                ic_no = match.group(1).strip()
                ic_colour = match.group(2).capitalize()
                break
            # Fallback: split by ':' and ','
            val = line.split(":", 1)[-1].strip() if ":" in line else line
            if "," in val:
                parts = [x.strip() for x in val.split(",", 1)]
                if len(parts) == 2:
                    ic_no, ic_colour = parts[0], parts[1].capitalize()
                    break
            elif val:
                ic_no = val
                ic_colour = None
                break

    # Date of Birth
    date_of_birth = None
    for line in lines:
        if "Date of Birth" in line:
            date_of_birth = line.split(":", 1)[-1].strip()
            break
    date_of_birth = parse_date(date_of_birth) if date_of_birth else None

    # Table row for appointment
    department, hire_date = None, None
    for line in lines:
        if "First appointment in Universiti Brunei Darussalam" in line:
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 4:
                department = parts[2] if parts[2] else None
                hire_date = parts[3] if parts[3] else None
            break
    hire_date = parse_date(hire_date) if hire_date else None

    # Present Post
    post = None
    for line in lines:
        if "Present Post" in line:
            # Extract only the job title (e.g., "Professor", "Assistant Professor", etc.)
            match = re.search(r"Present Post\\s*(.*?)(?:\\s*A5\\.i|$)", line)
            if match:
                post = match.group(1).strip()
            else:
                # Fallback: just take the first word after "Present Post"
                post = line.split("Present Post")[-1].strip().split()[0] if line.split("Present Post")[-1].strip() else None
            break

    # Appointment Type (Type of Service)
    appointment_type = None
    for line in lines:
        if "Type of Service" in line:
            if "Contract" in line and "√" in line:
                appointment_type = "Contract"
            elif "Permanent" in line and "√" in line:
                appointment_type = "Permanent"
            elif "Month-to-Month" in line and "√" in line:
                appointment_type = "Month-to-Month"
            elif "Daily Rated" in line and "√" in line:
                appointment_type = "Daily-Rated"

    # Salary
    salary = None
    for line in lines:
        if "Salary scale/ Division" in line:
            salary = line.split("Salary scale/ Division")[-1].strip()
            break
    try:
        salary = float(salary)
    except:
        salary = None

    # Department object
    department_obj = None
    if department:
        department_obj, _ = Department.objects.get_or_create(name=department)

    # Generate username/email/phone/address
    username = ((first_name or "") + (last_name or "")).lower() or ic_no or None
    email = f"{username}@example.com" if username else None
    phone_number = None
    address = None

    employee_data = {
        "employee_id": None,
        "ic_no": ic_no if ic_no else None,
        "first_name": first_name if first_name else None,
        "last_name": last_name if last_name else None,
        "date_of_birth": date_of_birth if date_of_birth else None,
        "department": department_obj if department_obj else None,
        "post": post if post else None,
        "appointment_type": appointment_type if appointment_type else None,
        "salary": salary if salary is not None else None,
        "ic_colour": ic_colour if ic_colour else None,
        "hire_date": hire_date if hire_date else None,
        "employee_status": "active",
        "address": address,
        "email": email,
        "phone_number": phone_number,
    }
    return employee_data

def create_user_for_employee(employee_data):
    username = employee_data['employee_id'] or (employee_data['first_name'] + employee_data['last_name']).lower()
    password = User.objects.make_random_password()
    user = User.objects.create_user(
        username=username,
        email=employee_data['email'],
        password=password,
        first_name=employee_data['first_name'],
        last_name=employee_data['last_name']
    )
    return user

def download_credentials_csv(request):
    credentials = request.session.get('created_credentials')
    if not credentials:
        messages.error(request, "No credentials to download.")
        return redirect('employees:bulk_add')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=\"bulk_employee_credentials.csv\"'
    writer = csv.writer(response)
    writer.writerow(['Email', 'Password'])
    for cred in credentials:
        writer.writerow([cred['email'], cred['password']])
    return response

def bulk_employee_edit(request, index):
    from employees.models import Employee, Department
    employees = request.session.get('bulk_employees', [])
    if index < 0 or index >= len(employees):
        return redirect('employees:bulk_add')
    employee = employees[index]

    # Choices for dropdowns
    ic_colour_choices = Employee.ICColour.choices
    gender_choices = Employee.Gender.choices
    appointment_type_choices = Employee.AppointmentType.choices
    status_choices = Employee.Status.choices
    department_list = Department.objects.all()

    if request.method == 'POST':
        # Update all relevant fields from form
        for field in [
            'first_name', 'last_name', 'email', 'phone_number', 'ic_no', 'ic_colour',
            'date_of_birth', 'gender', 'address', 'hire_date', 'salary',
            'appointment_type', 'employee_status', 'post', 'department'
        ]:
            value = request.POST.get(field, employee.get(field))
            if field in ['salary']:
                try:
                    value = float(value) if value else None
                except Exception:
                    value = None
            elif field in ['hire_date', 'date_of_birth']:
                value = value if value else None
            elif field == 'department':
                value = int(value) if value else None
            employee[field] = value
        employees[index] = employee
        request.session['bulk_employees'] = employees
        # Remove from bulk_already_exists if no longer duplicate
        already_exists = request.session.get('bulk_already_exists', [])
        # Check if this employee is in already_exists
        for emp in already_exists:
            if emp.get('index') == index:
                # Check if the new data would still cause a duplicate
                from django.contrib.auth.models import User
                username = (employee.get('first_name', '') or '') + (employee.get('last_name', '') or '')
                username = username.lower() or employee.get('ic_no') or None
                email = employee.get('email', '')
                duplicate = User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists()
                if not duplicate:
                    already_exists = [e for e in already_exists if e.get('index') != index]
                    break
        if already_exists:
            request.session['bulk_already_exists'] = already_exists
        elif 'bulk_already_exists' in request.session:
            del request.session['bulk_already_exists']
        # Redirect logic
        if 'next' in request.POST:
            return redirect('employees:bulk_employee_edit', index=index+1)
        elif 'prev' in request.POST:
            return redirect('employees:bulk_employee_edit', index=index-1)
        else:
            return redirect('employees:bulk_add')

    return render(request, 'employees/bulk_employee_edit.html', {
        'employee': employee,
        'index': index,
        'has_prev': index > 0,
        'has_next': index < len(employees) - 1,
        'ic_colour_choices': ic_colour_choices,
        'gender_choices': gender_choices,
        'appointment_type_choices': appointment_type_choices,
        'status_choices': status_choices,
        'department_list': department_list,
    })

@csrf_exempt
def bulk_employee_autosave(request, index):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    employees = request.session.get('bulk_employees', [])
    if index < 0 or index >= len(employees):
        return JsonResponse({'success': False, 'error': 'Invalid index'}, status=400)
    employee = employees[index]
    field = request.POST.get('field')
    value = request.POST.get('value')
    if not field:
        return JsonResponse({'success': False, 'error': 'No field provided'}, status=400)
    # Type conversion for certain fields
    if field in ['salary']:
        try:
            value = float(value) if value else None
        except Exception:
            value = None
    elif field in ['hire_date', 'date_of_birth']:
        value = value if value else None
    elif field == 'department':
        value = int(value) if value else None
    employee[field] = value
    employees[index] = employee
    request.session['bulk_employees'] = employees
    return JsonResponse({'success': True})

@require_POST
def bulk_employee_delete(request, index):
    employees = request.session.get('bulk_employees', [])
    from_edit = request.POST.get('from_edit')
    if 0 <= index < len(employees):
        del employees[index]
        request.session['bulk_employees'] = employees
    # Also remove from bulk_already_exists if present
    already_exists = request.session.get('bulk_already_exists', [])
    already_exists = [emp for emp in already_exists if emp.get('index') != index]
    if already_exists:
        request.session['bulk_already_exists'] = already_exists
    elif 'bulk_already_exists' in request.session:
        del request.session['bulk_already_exists']
    if from_edit:
        if index < len(employees):
            return redirect('employees:bulk_employee_edit', index=index)
        elif index-1 >= 0 and len(employees) > 0:
            return redirect('employees:bulk_employee_edit', index=index-1)
        else:
            return redirect('employees:bulk_add')
    return redirect('employees:bulk_add')