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

class AppraisalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Appraisal
    template_name = 'appraisals/appraisal_list.html'
    context_object_name = 'appraisals'
    permission_required = 'appraisals.view_appraisal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_periods'] = AppraisalPeriod.objects.filter(is_active=True).order_by('start_date')
        context['is_hr'] = self.request.user.groups.filter(name='HR').exists()
        
        # Get all employees for the main list
        context['employees'] = Employee.objects.all().order_by('department', 'last_name')
        
        # Add some debug printing
        try:
            appraiser_group = Group.objects.get(name='Appraiser')
            appraisers = Employee.objects.filter(user__groups=appraiser_group)
            print("Number of appraisers found:", appraisers.count())
            for appraiser in appraisers:
                print(f"Appraiser: {appraiser.first_name} {appraiser.last_name}, Dept: {appraiser.department}")
        except Group.DoesNotExist:
            print("Appraiser group not found")
            appraisers = Employee.objects.none()
        
        context['appraisers'] = appraisers
        return context

class AppraisalAssignView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Appraisal
    permission_required = 'appraisals.can_create_appraisal'
    http_method_names = ['post']

    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': form.errors
            }, status=400)
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        try:
            # Get the employee and appraiser
            employee = get_object_or_404(Employee, id=request.POST.get('employee_id'))
            appraiser = get_object_or_404(Employee, id=request.POST.get('appraiser'))
            
            # Create the appraisal
            appraisal = Appraisal.objects.create(
                employee=employee,
                appraiser=appraiser,
                review_period_start=request.POST.get('review_period_start'),
                review_period_end=request.POST.get('review_period_end'),
                status='pending',
                last_modified_by=request.user  # Add this line
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Appraisal assigned successfully'
                })
            return redirect('appraisals:appraisal_list')

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            messages.error(request, f'Error assigning appraisal: {str(e)}')
            return redirect('appraisals:appraisal_list')

@login_required
@require_http_methods(["POST"])
def appraisal_assign(request):
    try:
        # Get form data
        employee_id = request.POST.get('employee_id')
        appraiser_id = request.POST.get('appraiser')
        review_period_start = request.POST.get('review_period_start')
        review_period_end = request.POST.get('review_period_end')

        # Validate required fields
        if not all([employee_id, appraiser_id, review_period_start, review_period_end]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required'
            })

        # Get the employee and appraiser
        try:
            employee = Employee.objects.get(id=employee_id)
            appraiser = Employee.objects.get(id=appraiser_id)
        except Employee.DoesNotExist as e:
            logger.error(f"Employee/Appraiser not found: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Employee or appraiser not found'
            })

        # Create the appraisal
        appraisal = Appraisal.objects.create(
            employee=employee,
            appraiser=appraiser,
            review_period_start=review_period_start,
            review_period_end=review_period_end,
            status='pending',
            last_modified_by=request.user
        )

        return JsonResponse({
            'success': True,
            'message': 'Appraisal assigned successfully'
        })

    except Exception as e:
        logger.error(f"Error in appraisal_assign: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

class AppraisalDetailView(DetailView):
    model = Appraisal
    template_name = 'appraisals/appraisal_detail.html'
    context_object_name = 'appraisal'

class AppraisalUpdateView(UpdateView):
    model = Appraisal
    form_class = AppraisalForm
    template_name = 'appraisals/appraisal_form.html'
    success_url = reverse_lazy('appraisals:appraisal_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['academic_formset'] = AcademicQualificationFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['academic_formset'] = AcademicQualificationFormSet(
                instance=self.object
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        academic_formset = context['academic_formset']
        if form.is_valid() and academic_formset.is_valid():
            self.object = form.save()
            academic_formset.instance = self.object
            academic_formset.save()
            return super().form_valid(form)
        return self.render_to_response(self.get_context_data(form=form))

class AppraisalPeriodListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = AppraisalPeriod
    template_name = 'appraisals/period_list.html'
    context_object_name = 'periods'
    permission_required = ('appraisals.view_appraisalperiod',)
    
    def has_permission(self):
        user = self.request.user
        return user.groups.filter(name='HR').exists() or super().has_permission()

@login_required
@permission_required('appraisals.change_appraisalperiod')
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

@csrf_exempt  # Only for testing, remove in production
@require_http_methods(["POST"])
@login_required
@permission_required('appraisals.add_appraisalperiod', raise_exception=True)
def create_period(request):
    try:
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        print(f"Received dates - Start: {start_date}, End: {end_date}")  # Debug print
        
        if not start_date or not end_date:
            return JsonResponse({
                'success': False,
                'error': 'Both start date and end date are required'
            }, status=400)

        period = AppraisalPeriod(
            start_date=start_date,
            end_date=end_date,
            is_active=False
        )
        
        try:
            period.full_clean()
            period.save()
            return JsonResponse({
                'success': True,
                'message': 'Appraisal period created successfully'
            })
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
            
    except Exception as e:
        print(f"Error creating period: {str(e)}")  # Debug print
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@login_required
@permission_required('appraisals.change_appraisalperiod')
def toggle_period(request, pk):
    try:
        period = get_object_or_404(AppraisalPeriod, pk=pk)
        period.is_active = not period.is_active
        period.full_clean()
        period.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Period status updated successfully',
            'is_active': period.is_active
        })
    except ValidationError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while updating the period'
        }, status=500)

def appraisal_update_view(request, pk):
    appraisal = get_object_or_404(Appraisal, pk=pk)
    if request.method == 'POST':
        form = AppraisalForm(request.POST, instance=appraisal)
        formset = AcademicQualificationFormSet(request.POST, queryset=appraisal.academic_qualifications.all())
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            # Redirect or render success message
    else:
        form = AppraisalForm(instance=appraisal)
        formset = AcademicQualificationFormSet(queryset=appraisal.academic_qualifications.all())

    return render(request, 'appraisals/appraisal_form.html', {'form': form, 'formset': formset})

def appraisal_edit(request, pk=None):
    # Check permissions
    if not request.user.has_perm('appraisals.change_appraisal'):
        raise PermissionDenied
    
    # Define the formset outside try block since we'll need it in both cases
    AcademicQualificationFormSet = inlineformset_factory(
        Appraisal,
        AcademicQualification,
        fields=('degree_diploma', 'university_college', 'from_date', 'to_date'),
        extra=1,
        can_delete=True,
        min_num=1,  # Require at least one form
        validate_min=True
    )
    
    try:
        appraisal = get_object_or_404(Appraisal, pk=pk) if pk else None
        
        if request.method == 'POST':
            form = AppraisalForm(request.POST, instance=appraisal)
            academic_formset = AcademicQualificationFormSet(
                request.POST, 
                instance=appraisal,
                prefix='qualifications'
            )
            
            if form.is_valid() and academic_formset.is_valid():
                appraisal = form.save(commit=False)
                appraisal.last_modified_by = request.user
                appraisal.last_modified_date = timezone.now()
                appraisal.save()
                
                academic_formset.save()
                messages.success(request, 'Appraisal updated successfully.')
                return redirect('appraisals:appraisal_detail', pk=appraisal.pk)
            else:
                messages.error(request, 'Please correct the errors below.')
        else:
            form = AppraisalForm(instance=appraisal)
            academic_formset = AcademicQualificationFormSet(
                instance=appraisal,
                prefix='qualifications'
            )
        
        context = {
            'form': form,
            'academic_formset': academic_formset,
        }
        return render(request, 'appraisals/appraisal_form.html', context)
    except Exception as e:
        messages.error(request, f'An error occurred while editing the appraisal: {str(e)}')
        return redirect('appraisals:appraisal_list')

def appraisal_list(request):
    context = {
        'is_hr': request.user.has_perm('appraisals.can_manage_appraisals'),
        'employees': Employee.objects.all(),
        'appraisers': User.objects.filter(groups__name='Appraisers'),
        'active_period': AppraisalPeriod.objects.filter(is_active=True).first(),
        # ... other context data ...
    }
    return render(request, 'appraisals/appraisal_list.html', context)

def appraisal_context_processor(request):
    """
    Context processor to add appraisal-related data to all templates
    """
    active_period = AppraisalPeriod.objects.filter(is_active=True).exists()
    is_hr = request.user.groups.filter(name='HR').exists() if request.user.is_authenticated else False
    
    return {
        'active_period': active_period,
        'is_hr': is_hr,
    }