from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Appraisal, AppraisalPeriod
from employees.models import Employee, Department
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .forms import ModuleFormSet, SectionAForm, SectionBForm
from employees.forms import QualificationFormSet
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied
from django.template.context_processors import request
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

logger = logging.getLogger(__name__)

# Constants
HR_GROUP_NAME = 'HR'
APPRAISER_GROUP_NAME = 'Appraiser'

# ============================================================================
# Appraisal Period Management Views
# =============================================================================


class AppraisalPeriodListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Displays a list of all appraisal periods.
    Only HR and users with specific permissions can access this view.
    """
    model = AppraisalPeriod
    template_name = 'appraisals/period_list.html'
    context_object_name = 'periods'
    permission_required = ('appraisals.view_appraisalperiod',)
    
    def has_permission(self):
        return self.request.user.groups.filter(name=HR_GROUP_NAME).exists() or super().has_permission()

@login_required
@permission_required('appraisals.add_appraisalperiod', raise_exception=True)
def create_period(request):
    """
    Creates a new appraisal period.
    Requires POST request with start_date and end_date.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not all([start_date, end_date]):
            return JsonResponse({
                'success': False,
                'error': 'Both start date and end date are required'
            }, status=400)

        period = AppraisalPeriod(
            start_date=start_date,
            end_date=end_date,
            is_active=False
        )
        
        period.full_clean()
        period.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Appraisal period created successfully'
        })
            
    except Exception as e:
        logger.error(f"Error creating appraisal period: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def appraisal_delete(request):
    if request.method == 'POST':
        appraisal_id = request.POST.get('appraisal_id')
        user = request.user
        
        # Only allow HR users or staff to delete appraisals
        if user.is_staff or user.groups.filter(name=HR_GROUP_NAME).exists():
            try:
                appraisal = Appraisal.objects.get(appraisal_id=appraisal_id)
                appraisal.delete()
                messages.success(request, "Appraisal successfully deleted.")
            except Appraisal.DoesNotExist:
                messages.error(request, "Appraisal not found.")
        else:
            messages.error(request, "You don't have permission to delete appraisals.")
            
    return redirect('appraisals:form_list')

# ============================================================================
# Appraisal Management Views
# ============================================================================

class AppraisalListView(LoginRequiredMixin, ListView):
    """
    Display all appraisals with filtering capabilities.
    Provides tabs for different statuses (pending, review, completed)
    """
    model = Appraisal
    template_name = 'appraisals/appraisal_list.html'
    context_object_name = 'appraisals'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name='HR').exists():
            # HR users can see all appraisals
            return Appraisal.objects.all().select_related(
                'employee__user',
                'appraiser__user',
                'employee__department'
            ).order_by('-date_created')
        else:
            # Regular users see only their appraisals
            return Appraisal.objects.filter(
                Q(employee__user=user) |  # User's own appraisals
                Q(appraiser__user=user)   # Appraisals where user is appraiser
            ).order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Common data
        context['departments'] = Department.objects.all()
        
        # My Appraisals tab - show only appraisals where user is the employee
        context['my_appraisals'] = Appraisal.objects.filter(
            employee__user=user,
            status='pending' or 'pending_response',
        ).select_related('employee__user', 'appraiser__user', 'appraiser_secondary')  # Add select_related
        
        # Review tab - show appraisals where user is the primary or secondary appraiser
        context['review_appraisals'] = Appraisal.objects.filter(
            Q(appraiser__user=user) | Q(appraiser_secondary__user=user),
            status__in=['primary_review', 'secondary_review']
        )
        
        # Completed tab - show completed appraisals for the user
        context['completed_appraisals'] = Appraisal.objects.filter(
            Q(employee__user=user) | Q(appraiser__user=user) | Q(appraiser_secondary__user=user),
            status='completed'
        )

        # Only add all_appraisals to the context if the user is HR or staff
        if user.groups.filter(name=HR_GROUP_NAME).exists():
            context['all_appraisals'] = Appraisal.objects.all().select_related(
                'employee__user', 'appraiser__user', 'appraiser_secondary'
            ).order_by('-date_created')

        return context
class AppraisalDetailView(LoginRequiredMixin, DetailView):
    """
    Display details of a single appraisal.
    """
    model = Appraisal
    template_name = 'appraisals/appraisal_detail.html'
    context_object_name = 'appraisal'

class BaseAppraisalWizard(SessionWizardView):
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp'))
    
    def get_template_names(self):
        return [self.templates[self.steps.current]]
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context.update({
            'can_save_draft': True,
            'appraisal_id': self.kwargs.get('appraisal_id'),
            'is_edit': self.kwargs.get('is_edit', False)
        })
        return context

    def process_step(self, form):
        if self.request.POST.get('save_draft'):
            self.save_draft(form)
            return self.render_goto_step(self.steps.current)
        return self.get_form_step_data(form)

    def save_draft(self, form):
        appraisal = form.save(commit=False)
        appraisal.status = 'draft'
        appraisal.save()

class AppraiseeWizard(BaseAppraisalWizard, UpdateView):

    form_list = [
        ('section_a', SectionAForm),
        # ... other sections ...
    ]

    templates = {
        'section_a': 'appraisals/wizard/section_a.html',
        # ... other sections ...
    }
    
    def get_form_instance(self, step):
        """Initialize form instance with existing appraisal data"""
        if self.kwargs.get('appraisal_id'):
            try:
                return Appraisal.objects.get(
                   appraisal_id=self.kwargs.get('appraisal_id')
                )
            except Appraisal.DoesNotExist:
                pass
        return None

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        
        if self.steps.current == 'section_a':
            instance = self.get_form_instance(self.steps.current)
            
            if instance and instance.employee:
                # Add qualification formset with proper prefix
                if self.request.POST:
                    context['qualification_formset'] = QualificationFormSet(
                        self.request.POST,
                        instance=instance.employee,
                        prefix='qualification_set'
                    )
                else:
                    context['qualification_formset'] = QualificationFormSet(
                        instance=instance.employee,
                        prefix='qualification_set'
                    )
        
        return context
            
            
        #     # For appointments formset
        #     if self.request.POST:
        #         context['appointment_formset'] = AppointmentFormSet(
        #             self.request.POST, 
        #             instance=instance
        #         )
        #     else:
        #         context['appointment_formset'] = AppointmentFormSet(
        #             instance=instance
        #         )
        
        # return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        qualification_formset = context.get('qualification_formset')
        
        qualification_formset.instance = self.get_form_instance('section_a').employee
        qualification_instances = qualification_formset.save(commit=False)

        for obj in qualification_formset.deleted_objects:
            obj.delete()
        
        for qualification in qualification_instances:
            qualification.employee = self.get_form_instance('section_a').employee
            qualification.save()
        
        return super().form_valid(form)
    

    def get_template_names(self):
        """Override to ensure we're using the correct template"""
        return [self.templates[self.steps.current]]

    def process_step(self, form):
        """Handle step processing"""
        # Remove the save_draft check since we'll handle all saves the same way
        return super().process_step(form)
    
    def post(self, *args, **kwargs):
        form = self.get_form(data=self.request.POST, files=self.request.FILES)
        
        if form.is_valid():
            instance = self.get_form_instance(self.steps.current)
            if instance:
                form.save()
                
                if self.steps.current == 'section_a':
                    qualification_formset = QualificationFormSet(
                        data=self.request.POST,
                        instance=instance.employee,
                        prefix='qualification_set'
                    )
                    
                    if qualification_formset.is_valid():
                        qualification_formset.save()
                    else:
                        context = self.get_context_data(form=form)
                        context['qualification_formset'] = qualification_formset
                        return self.render(form)
                
                # Handle draft save explicitly
                if self.request.POST.get('save_draft') == 'true':
                    messages.success(self.request, 'Form saved as draft successfully.')
                    return HttpResponseRedirect(
                        reverse('appraisals:form_detail', 
                        kwargs={'pk': instance.appraisal_id})
                    )
                
                # Handle normal submission
                instance.status = 'pending'
                instance.save()
                messages.success(self.request, 'Form submitted successfully.')
                return HttpResponseRedirect(
                    reverse('appraisals:form_detail', 
                    kwargs={'pk': instance.appraisal_id})
                )
        
        # If form is invalid
        return self.render(form)
    
class AppraiserWizard(BaseAppraisalWizard):
    form_list = [
        ('section_b', SectionBForm),  # General Traits
        # ('section_c', SectionCForm),  # Local Staff Appraisal
        # ('section_d', SectionDForm),  # Adverse Appraisal
    ]
    
    templates = {
        'section_b': 'appraisals/wizard/section_b.html',
        # 'section_c': 'appraisals/wizard/section_c.html',
        # 'section_d': 'appraisals/wizard/section_d.html',
    }

    def dispatch(self, request, *args, **kwargs):
        appraisal = get_object_or_404(Appraisal, id=kwargs['appraisal_id'])
        if appraisal.appraiser.user != request.user:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)



class AppraisalAssignView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Handles assigning appraisals to employees with designated appraisers.
    """
    permission_required = 'appraisals.add_appraisal'
    
    def get_context_data(self):
        context = {}
        context['appraisers'] = Employee.objects.filter(
            roles__name='Appraiser'
        ).select_related('position')
        
        context['periods'] = AppraisalPeriod.objects.filter(
            is_active=True
        ).order_by('-start_date')
        
        return context
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            # Get the basic required fields from the POST data
            employee_id = request.POST.get('employee_id')
            appraiser_id = request.POST.get('appraiser')
            appraiser_secondary_id = request.POST.get('appraiser_secondary')  
            period_id = request.POST.get('period')

            # Get the period dates
            appraisal_period_start = request.POST.get('appraisal_period_start')
            appraisal_period_end = request.POST.get('appraisal_period_end')
            review_period_start = request.POST.get('review_period_start')
            review_period_end = request.POST.get('review_period_end')

            # Validate required fields
            if not all([employee_id, appraiser_id, period_id, appraisal_period_start, appraisal_period_end, review_period_start, review_period_end]):
                return JsonResponse({
                    'success': False,
                    'error': 'Please fill in all required fields'
                }, status=400)

            try:
                # Get the required objects
                employee = Employee.objects.get(employee_id=employee_id)
                appraiser = Employee.objects.get(employee_id=appraiser_id)
                period = AppraisalPeriod.objects.get(id=period_id)

                # Handle optional secondary appraiser
                appraiser_secondary = None
                if appraiser_secondary_id:
                    try:
                        appraiser_secondary = Employee.objects.get(employee_id=appraiser_secondary_id)
                    except Employee.DoesNotExist:
                        # Optional field, so we can just log this
                        logger.warning(f"Secondary appraiser not found: {appraiser_secondary_id}")
        
                # Create appraisal with period dates
                appraisal = Appraisal.objects.create(
                    employee=employee,
                    appraiser=appraiser,
                    appraiser_secondary=appraiser_secondary,
                    appraisal_period_start=period.start_date,
                    appraisal_period_end=period.end_date,
                    review_period_start=review_period_start,
                    review_period_end=review_period_end,
                    status='pending',
                    last_modified_by=request.user
                )

                return JsonResponse({
                    'success': True,
                    'message': 'Appraisal assigned successfully',
                    'appraisal_id': appraisal.appraisal_id
                })

            except (Employee.DoesNotExist, AppraisalPeriod.DoesNotExist) as e:
                logger.error(f"Error finding objects: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid employee, appraiser, or period selected'
                }, status=404)

        except Exception as e:
            logger.error(f"Error in appraisal_assign: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while assigning the appraisal'
            }, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_appraisal_period(request, pk):
    period = get_object_or_404(AppraisalPeriod, pk=pk)
    period.is_active = not period.is_active
    try:
        period.full_clean()
        period.save()
        message = 'Appraisal period activated' if period.is_active else 'Appraisal period deactivated'
        status = 'success'
    except ValidationError as e:
        message = str(e)
        status = 'error'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': status, 'message': message})
    messages.add_message(request, messages.INFO if status == 'success' else messages.ERROR, message)
    return redirect('appraisals:period_list')

@login_required
@permission_required('appraisals.change_appraisalperiod')
def toggle_period(request, pk):
    """
    Toggles the active status of an appraisal period.
    
    Args:
        request: HTTP request
        pk: Primary key of the AppraisalPeriod
        
    Returns:
        JsonResponse with updated status
    """
    try:
        period = get_object_or_404(AppraisalPeriod, pk=pk)
        period.is_active = not period.is_active
        period.full_clean()
        period.save()
        
        message = 'Period activated' if period.is_active else 'Period deactivated'
        return JsonResponse({
            'status': 'success',
            'message': f'Appraisal {message} successfully',
            'is_active': period.is_active
        })
    except ValidationError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Error toggling period status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while updating the period'
        }, status=500)

def get_appraisal_context(request):
    """
    Common context processor for appraisal-related views.
    Provides consistent context data across multiple views.
    """
    return {
        'active_periods': AppraisalPeriod.objects.filter(is_active=True),
        'is_hr': request.user.groups.filter(name=HR_GROUP_NAME).exists(),
        'is_appraiser': request.user.groups.filter(name=APPRAISER_GROUP_NAME).exists(),
        'can_manage_appraisals': request.user.has_perm('appraisals.can_manage_appraisals'),
    }

class AppraisalDashboardView(LoginRequiredMixin, TemplateView):
    """
    Overview dashboard showing key metrics and summaries
    """
    template_name = 'appraisals/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'active_periods': AppraisalPeriod.objects.filter(is_active=True).count(),
            'pending_appraisals': Appraisal.objects.filter(status='pending').count(),
            'completed_appraisals': Appraisal.objects.filter(status='completed').count(),
            'recent_activities': Appraisal.objects.order_by('-last_modified_date')[:5],
        })
        return context

class AppraiserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Display and manage list of appraisers with traditional HTML table
    """
    model = Employee
    template_name = 'appraisals/appraiser_list.html'
    permission_required = 'appraisals.view_appraisal'
    context_object_name = 'appraisers'  # Changed to match the template context variable

    def get_queryset(self):
        """
        Return employees who have the Appraiser role assigned
        """
        # Get employees who are appraisers
        return Employee.objects.filter(
            roles__name='Appraiser'
        ).select_related('user', 'department')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get employees who have ongoing appraisals (not completed)
        ongoing_appraisal_employee_ids = Appraisal.objects.exclude(
            status='completed'
        ).values_list('employee_id', flat=True).distinct()
        
        # Add non-appraisers for the Assign Appraisers tab (excluding those with ongoing appraisals)
        context['assign_employees'] = Employee.objects.exclude(
            # Exclude employees who have ongoing appraisals
            id__in=ongoing_appraisal_employee_ids
        ).select_related(
            'user',
            'department'
        )
        
        # Common data
        context['departments'] = Department.objects.all()
        context['periods'] = AppraisalPeriod.objects.all().order_by('-start_date')
        
        # Current assignments data - employees with their assigned appraisers
        employee_appraiser_assignments = {}
        appraisals = Appraisal.objects.all().select_related(
            'employee', 'appraiser', 'appraiser_secondary'
        )
        
        for appraisal in appraisals:
            if appraisal.employee_id not in employee_appraiser_assignments:
                employee_appraiser_assignments[appraisal.employee_id] = {
                    'primary': appraisal.appraiser,
                    'secondary': appraisal.appraiser_secondary,
                    'status': appraisal.status  # Add status to track whether it's completed
                }
        
        context['employee_appraisers'] = employee_appraiser_assignments
        
        return context
    
@require_http_methods(["GET"])
def get_appraisers(request):
    exclude_employee_id = request.GET.get('exclude_employee_id')
    
    # Get all employees that can be appraisers
    appraisers_queryset = Employee.objects.all()
    
    # Exclude the current employee if ID is provided
    if exclude_employee_id:
        appraisers_queryset = appraisers_queryset.exclude(employee_id=exclude_employee_id)
    
    # Format for template
    appraisers_data = [
        {
            'id': appraiser.employee_id,
            'name': appraiser.get_full_name(),
            'post': appraiser.post,
            'department': appraiser.department.name if appraiser.department else 'Other'
        }
        for appraiser in appraisers_queryset
    ]
    
    # Render the template
    content = render_to_string('appraisals/includes/appraiser_options.html', 
                              {'appraisers': appraisers_data})
    
    return HttpResponse(content, content_type='application/json')

class AppraiserRoleView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Manage appraiser roles and permissions
    """
    template_name = 'appraisals/appraiser_roles.html'
    permission_required = 'auth.change_group'

class PendingAppraisalsView(LoginRequiredMixin, ListView):
    """
    Display pending appraisals
    """
    model = Appraisal
    template_name = 'appraisals/pending_list.html'
    context_object_name = 'appraisals'
    
    def get_queryset(self):
        return Appraisal.objects.filter(status='pending')

class ReviewAppraisalsView(LoginRequiredMixin, ListView):
    """
    Display appraisals under review
    """
    model = Appraisal
    template_name = 'appraisals/review_list.html'
    context_object_name = 'appraisals'
    
    def get_queryset(self):
        return Appraisal.objects.filter(status='in_review')

class CompletedAppraisalsView(LoginRequiredMixin, ListView):
    """
    Display completed appraisals
    """
    model = Appraisal
    template_name = 'appraisals/completed_list.html'
    context_object_name = 'appraisals'
    
    def get_queryset(self):
        return Appraisal.objects.filter(status='completed')

@require_http_methods(["POST"])
def role_update(request, employee_id):
    try:
        employee = Employee.objects.get(employee_id=employee_id)
        action = request.POST.get('action')
        appraiser_group = Group.objects.get(name='Appraiser')
        
        if action == 'add':
            # Add employee to Appraiser group
            employee.roles.add(appraiser_group)
            message = f'{employee.get_full_name()} is now an Appraiser'
        elif action == 'remove':
            # Remove employee from Appraiser group
            employee.roles.remove(appraiser_group)
            message = f'{employee.get_full_name()} is no longer an Appraiser'
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid action'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'is_appraiser': employee.roles.filter(name='Appraiser').exists()
        })
    except Employee.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Employee with ID {employee_id} not found'
        }, status=404)
    except Group.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Appraiser group not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

class AppraisalReviewView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Appraisal
    template_name = 'appraisals/appraisal_form.html'
    permission_required = 'appraisals.change_appraisal'
    fields = [
        # Core Information
        'employee',
        'appraiser',
        'review_period_start',
        'review_period_end',
        'status',
        
        # Employment Details
        'present_post',
        'salary_scale_division',
        'incremental_date',
        'date_of_last_appraisal',
        
        # Academic Information
        'current_enrollment',
        'higher_degree_students_supervised',
        
        # Research and Publications
        'last_research',
        'ongoing_research',
        'publications',
        'conference_papers',
        
        # Professional Activities
        'attendance',
        'consultancy_work',
        'administrative_posts',
        
        # Participation
        'participation_within_university',
        'participation_outside_university',
        
        # Objectives and Comments
        'objectives_next_year',
        'appraiser_comments',
    ]

    def get_success_url(self):
        return reverse_lazy('appraisals:form_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Review Appraisal'
        context['submit_text'] = 'Save Review'
        return context

    def form_valid(self, form):
        # Add any additional processing before saving
        form.instance.last_modified_by = self.request.user
        return super().form_valid(form)

class AppraiseeUpdateView(LoginRequiredMixin, UpdateView):
    model = Appraisal
    form_class = SectionAForm
    template_name = 'appraisals/wizard/section_a.html'
    
    def get_object(self):
        return get_object_or_404(
            Appraisal, 
            appraisal_id=self.kwargs.get('appraisal_id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_save_draft'] = True
        
        if self.request.POST:
            context['qualification_formset'] = QualificationFormSet(
                self.request.POST, 
                instance=self.object.employee,
                prefix='qualification_set'
            )
            context['module_formset'] = ModuleFormSet(
                self.request.POST, 
                instance=self.object.employee,
                prefix='module_set'
            )
        else:
            context['qualification_formset'] = QualificationFormSet(
                instance=self.object.employee,
                prefix='qualification_set'
            )
            context['module_formset'] = ModuleFormSet(
                instance=self.object.employee,
                prefix='module_set'
            )
        
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        qualification_formset = context.get('qualification_formset')
        module_formset = context.get('module_formset')
        
        if (qualification_formset.is_valid() and 
            module_formset.is_valid()):
            
            # Save the main form
            self.object = form.save(commit=False)
            
            # Handle draft save
            if self.request.POST.get('save_draft') == 'true':
                self.object.status = 'draft'
            else:
                self.object.status = 'pending'
            
            self.object.save()
            
            # Save formsets
            qualification_formset.instance = self.object.employee
            qualification_formset.save()
            
            module_formset.instance = self.object.employee
            module_formset.save()
            
            # Add success message
            msg = 'Form saved as draft successfully.' if self.request.POST.get('save_draft') == 'true' else 'Form submitted successfully.'
            messages.success(self.request, msg)
            
            # Redirect to detail view
            return HttpResponseRedirect(
                reverse('appraisals:form_detail', 
                kwargs={'pk': self.object.appraisal_id})
            )
        
        return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)