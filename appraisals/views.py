from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Appraisal
from employees.models import Employee
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)

class AppraisalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Appraisal
    template_name = 'appraisals/appraisal_list.html'
    context_object_name = 'appraisals'
    permission_required = 'appraisals.view_appraisal'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user is HR
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
                status='pending'
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
            status='pending'
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