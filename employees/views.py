from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Employee, Department, Qualification, Document
from .forms import EmployeeForm, EmployeeProfileForm, QualificationForm, QualificationFormSet
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView
from django.contrib.messages.views import SuccessMessageMixin
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
    def test_func(self):
        return self.request.user.groups.filter(name='HR').exists()

class DepartmentListView(LoginRequiredMixin, HRRequiredMixin, ListView):
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
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def get_success_url(self):
        return self.success_url

    def form_valid(self, form):
        """Security check complete. Log the user in."""
        username = form.cleaned_data.get('login')  # Get the login field value
        password = form.cleaned_data.get('password')
        
        # Explicitly authenticate the user
        user = authenticate(
            self.request,
            username=username,  # Use username parameter as that's what your backend expects
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
    model = Employee
    template_name = 'employees/employee_list.html'
    context_object_name = 'employees'
    login_url = 'login'  # Redirect to login if user is not authenticated

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        # Get unique positions
        context['posts'] = Employee.objects.values_list('post', flat=True).distinct()
        return context

    def get_queryset(self):
        return Employee.objects.select_related('department', 'appointment__type_of_appointment').all()

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'employees/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get basic stats
        context['total_employees'] = Employee.objects.count()
        context['total_departments'] = Department.objects.count()
        
        # Get appraisal stats
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

                # Create user account
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=password,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
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

@transaction.atomic
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        appointment_form = AppointmentForm(request.POST)
        qualification_formset = QualificationFormSet(
            request.POST, 
            request.FILES,
            prefix='qualifications'
        )
        
        print("POST request received")
        print("Qualification formset is valid:", qualification_formset.is_valid())
        if not qualification_formset.is_valid():
            print("Qualification formset errors:", qualification_formset.errors)
        
        if form.is_valid() and appointment_form.is_valid() and qualification_formset.is_valid():
            try:
                # Generate a random password if none provided
                password = form.cleaned_data.get('password')
                if not password:
                    password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=12))

                # Create user account
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=password,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )

                # Save employee
                employee = form.save(commit=False)
                employee.user = user
                employee.save()
                form.save_m2m()  # Save many-to-many relationships
                
                # Save appointment
                if appointment_form.has_changed():
                    appointment = appointment_form.save(commit=False)
                    appointment.employee = employee
                    appointment.save()
                
                # Save qualifications
                instances = qualification_formset.save(commit=False)
                for instance in instances:
                    instance.save()
                employee.qualifications.add(*instances)
                
                messages.success(
                    request, 
                    f'Employee created successfully. Username: {user.username}. Please securely share the credentials with the employee.'
                )
                return redirect('employees:employee_list')
                
            except Exception as e:
                messages.error(request, f'Error creating employee: {str(e)}')
                # If there's an error, the transaction will be rolled back
                
    else:
        form = EmployeeForm()
        appointment_form = AppointmentForm()
        qualification_formset = QualificationFormSet(
            prefix='qualifications'
        )
        
        # Get the empty form HTML
        empty_form = qualification_formset.empty_form
        
    return render(request, 'employees/employee_create.html', {
        'form': form,
        'appointment_form': appointment_form,
        'qualification_formset': qualification_formset,
        'empty_form': empty_form,
    })

class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employees/employee_detail.html'
    context_object_name = 'employee'

    def get_queryset(self):
        # Prefetch the documents to optimize queries
        return super().get_queryset().prefetch_related('documents')

class SettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'employees/settings.html'
    
    def test_func(self):
        """Only allow HR users to access settings"""
        return self.request.user.groups.filter(name='HR').exists()
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access settings.")
        return redirect('dashboard')


