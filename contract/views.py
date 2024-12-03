from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.core.cache import cache
from .models import Contract
from .forms import ContractRenewalForm
from appraisals.models import Appraisal
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import DeleteView
from django.shortcuts import get_object_or_404
from employees.models import Employee
from django.utils import timezone
from datetime import timedelta
import json
from datetime import datetime
from django.db.models import F
from dateutil.relativedelta import relativedelta
from django.views import View
from .models import Contract
from employees.models import Department
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import ContractRenewalStatus
from .models import ContractNotification
from django.contrib.auth.models import Group
from django.urls import reverse
from django.db.models import Q


class ContractSubmissionView(LoginRequiredMixin, CreateView):
    template_name = 'contract/submission.html'
    form_class = ContractRenewalForm
    success_url = reverse_lazy('contract:thank_you')
    model = Contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user is HR
        is_hr = self.request.user.groups.filter(name='HR').exists()
        
        if is_hr:
            context['contract_enabled'] = True
            context['is_hr_contract'] = True
        else:
            # For non-HR users, check their contract status
            try:
                employee = Employee.objects.get(user=self.request.user)
                if employee.type_of_appointment == 'Contract':
                    contract_status = ContractRenewalStatus.objects.filter(
                        employee=employee
                    ).first()
                    context['contract_enabled'] = contract_status.is_enabled if contract_status else False
            except Employee.DoesNotExist:
                context['contract_enabled'] = False
        
        # Get employee's previous contract if it exists
        if hasattr(self.request.user, 'employee'):
            previous_contract = Contract.objects.filter(
                employee=self.request.user.employee
            ).order_by('-submission_date').first()
            
            if previous_contract:
                context['previous_contract'] = previous_contract
                
        return context

    def form_valid(self, form):
        form.instance.employee = self.request.user.employee
        form.instance.status = 'pending'
        response = super().form_valid(form)
        
        # Create notification for HR users
        hr_users = Group.objects.get(name='HR').user_set.all()
        submission_date = form.instance.submission_date.strftime('%B %d, %Y')
        message = f"{self.request.user.employee.get_full_name()} has submitted a contract renewal form on {submission_date}"
        
        for hr_user in hr_users:
            ContractNotification.objects.create(
                employee=hr_user.employee,
                message=message,
                read=False,
                contract=form.instance
            )
        
        return response

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Handle the contract system toggle
            contract_status = request.POST.get('contract_status') == 'on'
            cache.set('contract_enabled', contract_status, timeout=86400)
            return JsonResponse({
                'success': True,
                'message': f"Contract system has been {'enabled' if contract_status else 'disabled'}"
            })
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Check if user has a pending submission
        existing_submission = Contract.objects.filter(
            employee=request.user.employee,
            status__in=['pending', 'smt_review']
        ).first()
        
        if existing_submission:
            return render(request, 'contract/submission_exists.html', {
                'submission': existing_submission
            })
            
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('contract:thank_you')

def get_employee_data(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
        appraisals = Appraisal.objects.filter(
            employee=employee
        ).order_by('-date_of_last_appraisal')

        if not appraisals.exists():
            return JsonResponse({
                'success': False,
                'message': 'No appraisal found for this employee'
            })

        latest_appraisal = appraisals.first()

        def process_status_fields(field_name):
            """
            Process fields that might contain status indicators
            Keep ONGOING items unless they have a FINISHED status
            """
            status_tracker = {}
            
            for appraisal in appraisals:
                content = getattr(appraisal, field_name, '') or ''
                if not content:
                    continue
                
                items = [item.strip() for item in content.split('\n') if item.strip()]
                
                for item in items:
                    base_item = item.replace('(ONGOING)', '').replace('(FINISHED)', '').strip()
                    is_finished = '(FINISHED)' in item
                    is_ongoing = '(ONGOING)' in item
                    
                    if base_item not in status_tracker:
                        status_tracker[base_item] = item
                    elif is_finished:
                        status_tracker[base_item] = item
                    elif is_ongoing and not '(FINISHED)' in status_tracker[base_item]:
                        status_tracker[base_item] = item

            finished_items = []
            ongoing_items = []
            regular_items = []
            
            for item in status_tracker.values():
                if '(FINISHED)' in item:
                    finished_items.append(item)
                elif '(ONGOING)' in item:
                    ongoing_items.append(item)
                else:
                    regular_items.append(item)
            
            all_items = finished_items + ongoing_items + regular_items
            return '\n'.join(all_items) if all_items else ''

        # Process appraiser comments
        appraiser_comments_history = []
        for appraisal in appraisals:
            if appraisal.appraiser_comments and appraisal.appraiser_comments.strip():
                comment_data = {
                    'comment': appraisal.appraiser_comments.strip(),
                    'date': appraisal.date_of_last_appraisal.strftime('%Y-%m-%d'),
                    'appraiser_name': appraisal.appraiser.get_full_name() if appraisal.appraiser else 'Unknown Appraiser'
                }
                appraiser_comments_history.append(comment_data)

        # Process academic qualifications
        unique_qualifications = set()
        all_qualifications = []
        
        for appraisal in appraisals:
            qualifications = appraisal.academic_qualifications.all().order_by('-to_date')
            for qual in qualifications:
                qual_identifier = (
                    qual.degree_diploma.lower(),
                    qual.university_college.lower(),
                    qual.from_date.isoformat(),
                    qual.to_date.isoformat()
                )
                if qual_identifier not in unique_qualifications:
                    unique_qualifications.add(qual_identifier)
                    all_qualifications.append({
                        'degree_diploma': qual.degree_diploma,
                        'university_college': qual.university_college,
                        'from_date': qual.from_date.strftime('%Y-%m-%d'),
                        'to_date': qual.to_date.strftime('%Y-%m-%d')
                    })

        # Process current enrollment
        current_enrollments = []
        seen_enrollments = set()
        
        for appraisal in appraisals:
            if appraisal.current_enrollment:
                enrollments = [e.strip() for e in appraisal.current_enrollment.split('\n') if e.strip()]
                for enrollment in enrollments:
                    if enrollment not in seen_enrollments:
                        seen_enrollments.add(enrollment)
                        current_enrollments.append(enrollment)
        
        contract_count = Contract.objects.filter(employee=employee).count() + 1

        combined_data = {
            # Basic information
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': employee.ic_colour,
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'department_id': employee.department.id if employee.department else '',
            'contract_count': contract_count, 
            
            # Academic qualifications
            'academic_qualifications_text': json.dumps(all_qualifications),
            
            # Appraiser comments
            'appraiser_comments_history': appraiser_comments_history,
            
            # Current enrollment
            'current_enrollment': '\n'.join(current_enrollments),
            
            # Status fields
            'last_research': process_status_fields('last_research'),
            'ongoing_research': process_status_fields('ongoing_research'),
            'publications': process_status_fields('publications'),
            'conference_papers': process_status_fields('conference_papers'),
            'consultancy_work': process_status_fields('consultancy_work'),
            'administrative_posts': process_status_fields('administrative_posts'),
            'higher_degree_students_supervised': process_status_fields('higher_degree_students_supervised'),
            'participation_within_university': process_status_fields('participation_within_university'),
            'participation_outside_university': process_status_fields('participation_outside_university'),
            'attendance': process_status_fields('attendance'),
            
            # Latest values
            'present_post': latest_appraisal.present_post,
            'salary_scale_division': latest_appraisal.salary_scale_division,
            'objectives_next_year': latest_appraisal.objectives_next_year,
            'incremental_date': latest_appraisal.incremental_date.strftime('%Y-%m-%d') if latest_appraisal.incremental_date else '',
            'date_of_last_appraisal': latest_appraisal.date_of_last_appraisal.strftime('%Y-%m-%d') if latest_appraisal.date_of_last_appraisal else '',
        }

        return JsonResponse({
            'success': True,
            'data': combined_data
        })

    except Exception as e:
        print(f"Error in get_employee_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

class ContractListView(LoginRequiredMixin, View):
    template_name = 'contract/contract_list.html'

    def get(self, request):
        if not request.user.groups.filter(name='HR').exists():
            return redirect('contract:submission')
            
        contract_employees = Employee.objects.filter(
            type_of_appointment='Contract'
        ).select_related('department')

        employees_data = []
        today = datetime.now().date()
        
        for employee in contract_employees:
            renewal_date = employee.hire_date + relativedelta(years=3)
            while renewal_date < today:
                renewal_date += relativedelta(years=3)
            
            r_date = datetime(renewal_date.year, renewal_date.month, 1)
            t_date = datetime(today.year, today.month, 1)
            
            months_remaining = ((r_date.year - t_date.year) * 12 + 
                              r_date.month - t_date.month)
            
            # Get contract renewal status
            status = ContractRenewalStatus.objects.filter(employee=employee).first()
            
            # Get number of contract submissions plus the default contract (1)
            contract_count = Contract.objects.filter(employee=employee).count() + 1
            
            employees_data.append({
                'employee': employee,
                'renewal_date': renewal_date,
                'months_remaining': months_remaining,
                'is_enabled': status.is_enabled if status else False,
                'contract_count': contract_count
            })

        context = {
            'employees_data': employees_data,
            'is_hr': True,
            'departments': Department.objects.all()
        }
        
        return render(request, self.template_name, context)

class ContractDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            contract = Contract.objects.get(pk=pk)
            employee_id = contract.employee.id  # Store employee_id before deletion
            contract.delete()
            messages.success(request, "Contract submission deleted successfully.")
            return redirect('contract:view_submissions', employee_id=employee_id)
        except Contract.DoesNotExist:
            messages.error(request, "Contract submission not found.")
            return redirect('contract:list')

class ContractReviewView(LoginRequiredMixin, UpdateView):
    model = Contract
    template_name = 'contract/review.html'
    form_class = ContractRenewalForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.get_object()
        employee = contract.employee
        
        # Get the contract count from the specific submission being reviewed
        submissions_before = Contract.objects.filter(
            employee=contract.employee,
            submission_date__lt=contract.submission_date
        ).count()
        contract_count = submissions_before + 1
        
        # Add personal details to context
        context.update({
            'contract': contract,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': employee.ic_colour,
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'contract_count': contract_count,
            'academic_qualifications': json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else [],
            'is_review': True
        })
        
        # Get all appraisals for this employee
        appraisals = Appraisal.objects.filter(
            employee=contract.employee
        ).order_by('-date_of_last_appraisal')
        
        # Format appraiser comments from all appraisals
        appraiser_comments = []
        for appraisal in appraisals:
            if appraisal.appraiser_comments and appraisal.appraiser_comments.strip():
                comment_data = {
                    'comment': appraisal.appraiser_comments.strip(),
                    'date': appraisal.date_of_last_appraisal.strftime('%Y-%m-%d'),
                    'appraiser_name': appraisal.appraiser.get_full_name() if appraisal.appraiser else 'Unknown Appraiser'
                }
                appraiser_comments.append(comment_data)
        
        context['appraiser_comments'] = appraiser_comments
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Make all fields read-only
        for field_name, field in form.fields.items():
            field.widget.attrs['readonly'] = True
            field.widget.attrs['disabled'] = True
        return form

class ThankYouView(LoginRequiredMixin, TemplateView):
    template_name = 'contract/thank_you.html'

class ViewSubmissionsView(LoginRequiredMixin, View):
    template_name = 'contract/view_submissions.html'

    def get(self, request, employee_id):
        try:
            employee = Employee.objects.get(id=employee_id)
            submissions = Contract.objects.filter(
                employee=employee
            ).order_by('-submission_date')

            context = {
                'employee': employee,
                'submissions': submissions
            }
            return render(request, self.template_name, context)
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
            return redirect('contract:contract_list')

@login_required
@require_POST
def enable_contract(request):
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        employee_ids = data.get('employee_ids', [])
        action = data.get('action')  # 'enable' or 'disable'
        
        for employee_id in employee_ids:
            status, created = ContractRenewalStatus.objects.get_or_create(
                employee_id=employee_id
            )
            status.is_enabled = (action == 'enable')
            status.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def send_notification(request):
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get all contract employees with enabled contract renewal status
        contract_employees = Employee.objects.filter(
            type_of_appointment='Contract',
            contractrenewalstatus__is_enabled=True
        ).select_related('department')
        
        today = timezone.now().date()
        notifications_sent = 0
        
        for employee in contract_employees:
            # Calculate next renewal date
            renewal_date = employee.hire_date + relativedelta(years=3)
            while renewal_date < today:
                renewal_date += relativedelta(years=3)
            
            # Calculate months remaining
            months_remaining = ((renewal_date.year - today.year) * 12 + 
                              renewal_date.month - today.month)
            
            # Get the correct URL using reverse()
            submission_url = '/contract/form/'
            
            # Create notification with link to contract renewal form
            message = (
                f"Your contract renewal is due on {renewal_date.strftime('%B %d, %Y')}. "
                f"You have {months_remaining} months remaining. "
                "Please submit your contract renewal application. Use the link below:<br/>"
                f'<a href="{submission_url}" class="text-blue-600 hover:underline">Click here to submit</a>'
            )
            
            # Create notification
            ContractNotification.objects.create(
                employee=employee,
                message=message
            )
            notifications_sent += 1
        
        if notifications_sent > 0:
            return JsonResponse({
                'status': 'success',
                'message': f'Notifications sent to {notifications_sent} employees'
            })
        else:
            return JsonResponse({
                'status': 'info',
                'message': 'No employees with enabled contract renewal found'
            })
        
    except Exception as e:
        print(f"Error sending notifications: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_notification(request, notification_id):
    try:
        notification = ContractNotification.objects.get(
            id=notification_id,
            employee__user=request.user
        )
        notification.delete()
        return JsonResponse({'status': 'success'})
    except ContractNotification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class NotificationsView(LoginRequiredMixin, ListView):
    template_name = 'contract/notifications.html'
    context_object_name = 'notifications'
    
    def get_queryset(self):
        return ContractNotification.objects.filter(
            employee__user=self.request.user
        ).order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        # Mark all notifications as read
        ContractNotification.objects.filter(
            employee__user=request.user,
            read=False
        ).update(read=True)
        return super().get(request, *args, **kwargs)

@login_required
@require_POST
def forward_to_smt(request, contract_id):
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        contract = Contract.objects.get(id=contract_id)
        contract.status = 'smt_review'
        contract.save()
        
        return JsonResponse({'status': 'success'})
    except Contract.DoesNotExist:
        return JsonResponse({'error': 'Contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    try:
        notification = ContractNotification.objects.get(
            id=notification_id,
            employee=request.user.employee
        )
        notification.read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except ContractNotification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)