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
        try:
            contract = form.save(commit=False)
            
            # Save all the form data exactly as submitted
            contract.employee = form.cleaned_data['employee']
            contract.first_name = contract.employee.first_name
            contract.last_name = contract.employee.last_name
            contract.ic_no = contract.employee.ic_no
            contract.ic_colour = contract.employee.ic_colour
            contract.phone_number = contract.employee.phone_number
            contract.department = contract.employee.department
            
            # Save all the editable fields from the form
            contract.present_post = form.cleaned_data['present_post']
            contract.salary_scale_division = form.cleaned_data['salary_scale_division']
            contract.incremental_date = form.cleaned_data['incremental_date']
            contract.date_of_last_appraisal = form.cleaned_data['date_of_last_appraisal']
            contract.current_enrollment = form.cleaned_data['current_enrollment']
            contract.higher_degree_students_supervised = form.cleaned_data['higher_degree_students_supervised']
            contract.last_research = form.cleaned_data['last_research']
            contract.ongoing_research = form.cleaned_data['ongoing_research']
            contract.publications = form.cleaned_data['publications']
            contract.attendance = form.cleaned_data['attendance']
            contract.conference_papers = form.cleaned_data['conference_papers']
            contract.consultancy_work = form.cleaned_data['consultancy_work']
            contract.administrative_posts = form.cleaned_data['administrative_posts']
            contract.participation_within_university = form.cleaned_data['participation_within_university']
            contract.participation_outside_university = form.cleaned_data['participation_outside_university']
            contract.objectives_next_year = form.cleaned_data['objectives_next_year']
            
            # Save academic qualifications exactly as submitted
            if 'academic_qualifications_text' in form.cleaned_data:
                contract.academic_qualifications_text = form.cleaned_data['academic_qualifications_text']
            
            contract.save()
            messages.success(self.request, "Contract renewal submitted successfully.")
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f"Error submitting contract renewal: {str(e)}")
            return super().form_invalid(form)

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

        combined_data = {
            # Basic information
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': employee.ic_colour,
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'department_id': employee.department.id if employee.department else '',
            
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
            
            employees_data.append({
                'employee': employee,
                'renewal_date': renewal_date,
                'months_remaining': months_remaining,
                'is_enabled': status.is_enabled if status else False
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

        # Add current contract comments if they exist
        if contract.appraiser_comments and contract.appraiser_comments.strip():
            contract_comment = {
                'comment': contract.appraiser_comments.strip(),
                'date': contract.submission_date.strftime('%Y-%m-%d'),
                'appraiser_name': 'Contract Reviewer'
            }
            appraiser_comments.append(contract_comment)

        context.update({
            'contract': contract,
            'academic_qualifications': json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else [],
            'appraiser_comments': appraiser_comments,
            'is_review': True
        })
        
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
def send_contract_notifications(request):
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get all employees with enabled contract renewal
        enabled_statuses = ContractRenewalStatus.objects.filter(is_enabled=True)
        
        notification_count = 0
        for status in enabled_statuses:
            # Create notification for each employee
            ContractNotification.objects.create(
                employee=status.employee,
                message="Your contract renewal is due. Please submit your renewal application."
            )
            notification_count += 1
        
        messages.success(request, f'Notifications sent to {notification_count} employees.')
        return JsonResponse({
            'status': 'success',
            'count': notification_count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)