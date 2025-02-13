from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Appraisal, AppraisalPeriod, AcademicQualification
from employees.models import Employee
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .forms import AppraisalForm, AcademicQualificationFormSet
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied
from django.template.context_processors import request

logger = logging.getLogger(__name__)

# Constants
HR_GROUP_NAME = 'HR'
APPRAISER_GROUP_NAME = 'Appraiser'

# ============================================================================
# Appraisal Period Management Views
# ============================================================================

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

# ============================================================================
# Appraisal Management Views
# ============================================================================

class AppraisalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Displays a list of all appraisals.
    Provides context for filtering and managing appraisals.
    """
    model = Appraisal
    template_name = 'appraisals/appraisal_list.html'
    context_object_name = 'appraisals'
    permission_required = 'appraisals.view_appraisal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'active_periods': AppraisalPeriod.objects.filter(is_active=True).order_by('start_date'),
            'is_hr': self.request.user.groups.filter(name=HR_GROUP_NAME).exists(),
            'employees': Employee.objects.all().order_by('department', 'last_name'),
            'appraisers': self._get_appraisers()
        })
        return context

    def _get_appraisers(self):
        """Helper method to get all appraisers"""
        try:
            appraiser_group = Group.objects.get(name=APPRAISER_GROUP_NAME)
            return Employee.objects.filter(user__groups=appraiser_group)
        except Group.DoesNotExist:
            logger.warning("Appraiser group not found")
            return Employee.objects.none()

class AppraisalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Displays detailed information about a specific appraisal.
    """
    model = Appraisal
    template_name = 'appraisals/appraisal_detail.html'
    context_object_name = 'appraisal'
    permission_required = 'appraisals.view_appraisal'

class AppraisalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Handles updating existing appraisals including academic qualifications.
    """
    model = Appraisal
    form_class = AppraisalForm
    template_name = 'appraisals/appraisal_form.html'
    success_url = reverse_lazy('appraisals:appraisal_list')
    permission_required = 'appraisals.change_appraisal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_formset'] = AcademicQualificationFormSet(
            self.request.POST if self.request.POST else None,
            instance=self.object
        )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        academic_formset = context['academic_formset']
        
        if form.is_valid() and academic_formset.is_valid():
            self.object = form.save(commit=False)
            self.object.last_modified_by = self.request.user
            self.object.last_modified_date = timezone.now()
            self.object.save()
            
            academic_formset.instance = self.object
            academic_formset.save()
            
            messages.success(self.request, 'Appraisal updated successfully.')
            return super().form_valid(form)
            
        return self.render_to_response(self.get_context_data(form=form))

@login_required
@require_http_methods(["POST"])
def appraisal_assign(request):
    """
    Assigns an appraisal to an employee with a designated appraiser.
    
    Args:
        request: HTTP request containing employee_id, appraiser_id, and review period dates
        
    Returns:
        JsonResponse with success/failure status and appropriate message
    """
    try:
        data = {
            'employee_id': request.POST.get('employee_id'),
            'appraiser_id': request.POST.get('appraiser'),
            'review_period_start': request.POST.get('review_period_start'),
            'review_period_end': request.POST.get('review_period_end')
        }

        # Validate required fields
        if not all(data.values()):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required'
            }, status=400)

        # Get the employee and appraiser
        try:
            employee = Employee.objects.get(id=data['employee_id'])
            appraiser = Employee.objects.get(id=data['appraiser_id'])
        except Employee.DoesNotExist as e:
            logger.error(f"Employee/Appraiser not found: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Employee or appraiser not found'
            }, status=404)

        appraisal = Appraisal.objects.create(
            employee=employee,
            appraiser=appraiser,
            review_period_start=data['review_period_start'],
            review_period_end=data['review_period_end'],
            status='pending',
            last_modified_by=request.user
        )

        # Send notification (implement your notification system)
        # notify_appraisal_assignment(appraisal)

        return JsonResponse({
            'success': True,
            'message': 'Appraisal assigned successfully',
            'appraisal_id': appraisal.id
        })

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

class AppraisalEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Handles the editing of appraisals and their associated academic qualifications.
    Provides form handling for both the main appraisal form and academic qualification formset.
    """
    model = Appraisal
    form_class = AppraisalForm
    template_name = 'appraisals/appraisal_form.html'
    permission_required = 'appraisals.change_appraisal'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['academic_formset'] = AcademicQualificationFormSet(
                self.request.POST,
                instance=self.object,
                prefix='qualifications'
            )
        else:
            context['academic_formset'] = AcademicQualificationFormSet(
                instance=self.object,
                prefix='qualifications'
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        academic_formset = context['academic_formset']
        
        if academic_formset.is_valid():
            self.object = form.save(commit=False)
            self.object.last_modified_by = self.request.user
            self.object.last_modified_date = timezone.now()
            self.object.save()
            
            academic_formset.instance = self.object
            academic_formset.save()
            
            messages.success(self.request, 'Appraisal updated successfully.')
            return redirect('appraisals:appraisal_detail', pk=self.object.pk)
        
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

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