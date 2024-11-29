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

class ContractSubmissionView(LoginRequiredMixin, CreateView):
    template_name = 'contract/submission.html'
    form_class = ContractRenewalForm
    success_url = reverse_lazy('contract:list')
    model = Contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contract_enabled'] = cache.get('contract_enabled', False)
        return context

    def form_valid(self, form):
        try:
            contract = form.save(commit=False)
            employee = form.cleaned_data['employee']
            
            # Save personal details from employee
            contract.first_name = employee.first_name
            contract.last_name = employee.last_name
            contract.ic_no = employee.ic_no
            contract.ic_colour = employee.ic_colour
            contract.phone_number = employee.phone_number
            contract.department = employee.department
            
            # Get latest appraisal data
            latest_appraisal = Appraisal.objects.filter(
                employee=employee
            ).order_by('-date_of_last_appraisal').first()

            if latest_appraisal:
                # Populate contract with appraisal data
                contract.present_post = latest_appraisal.present_post
                contract.salary_scale_division = latest_appraisal.salary_scale_division
                contract.incremental_date = latest_appraisal.incremental_date
                contract.date_of_last_appraisal = latest_appraisal.date_of_last_appraisal
                contract.academic_qualifications_text = latest_appraisal.academic_qualifications_text
                contract.current_enrollment = latest_appraisal.current_enrollment
                contract.last_research = latest_appraisal.last_research
                contract.ongoing_research = latest_appraisal.ongoing_research
                contract.publications = latest_appraisal.publications
                contract.conference_papers = latest_appraisal.conference_papers
                contract.consultancy_work = latest_appraisal.consultancy_work
                contract.administrative_posts = latest_appraisal.administrative_posts
                contract.participation_within_university = latest_appraisal.participation_within_university
                contract.participation_outside_university = latest_appraisal.participation_outside_university
                contract.objectives_next_year = latest_appraisal.objectives_next_year
                contract.appraiser_comments = latest_appraisal.appraiser_comments
            
            contract.save()
            messages.success(self.request, 'Contract renewal submitted successfully')
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error submitting contract: {str(e)}')
            return self.form_invalid(form)

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
    """API endpoint to get combined appraisal data for an employee"""
    try:
        # Get employee details
        employee = Employee.objects.get(id=employee_id)
        
        # Get all appraisals ordered by date, latest first
        appraisals = Appraisal.objects.filter(
            employee=employee
        ).order_by('-date_of_last_appraisal')

        if not appraisals.exists():
            return JsonResponse({
                'success': False,
                'message': 'No appraisal found for this employee'
            })

        # Get the latest appraisal
        latest_appraisal = appraisals.first()
        
        # Initialize lists for cumulative fields
        research_history = []
        publications = []
        conferences = []
        consultancy = []
        admin_posts = []
        participation_internal = []
        participation_external = []
        appraiser_comments = []

        # Combine data from all appraisals without duplicates
        for appraisal in appraisals:
            # Appraiser Comments
            if appraisal.appraiser_comments:
                appraiser_comments.append({
                    'comment': appraisal.appraiser_comments,
                    'appraiser_name': appraisal.appraiser.get_full_name() if appraisal.appraiser else 'Unknown Appraiser',
                    'date': appraisal.date_of_last_appraisal.strftime('%d %B %Y') if appraisal.date_of_last_appraisal else 'Unknown Date'
                })
            
            # Research History
            if appraisal.last_research and appraisal.last_research not in research_history:
                research_history.append(appraisal.last_research)
            
            # Publications
            if appraisal.publications:
                pub_list = [p.strip() for p in appraisal.publications.split('\n') if p.strip()]
                for pub in pub_list:
                    if pub not in publications:
                        publications.append(pub)

            # Conference Papers
            if appraisal.conference_papers:
                conf_list = [c.strip() for c in appraisal.conference_papers.split('\n') if c.strip()]
                for conf in conf_list:
                    if conf not in conferences:
                        conferences.append(conf)

            # Consultancy Work
            if appraisal.consultancy_work and appraisal.consultancy_work not in consultancy:
                consultancy.append(appraisal.consultancy_work)

            # Administrative Posts
            if appraisal.administrative_posts and appraisal.administrative_posts not in admin_posts:
                admin_posts.append(appraisal.administrative_posts)

            # University Participation
            if appraisal.participation_within_university and appraisal.participation_within_university not in participation_internal:
                participation_internal.append(appraisal.participation_within_university)

            # External Participation
            if appraisal.participation_outside_university and appraisal.participation_outside_university not in participation_external:
                participation_external.append(appraisal.participation_outside_university)

        # Initialize data with employee's personal details
        combined_data = {
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': employee.ic_colour,
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'department_id': employee.department.id if employee.department else '',
            'present_post': latest_appraisal.present_post,
            'salary_scale_division': latest_appraisal.salary_scale_division,
            'academic_qualifications_text': latest_appraisal.academic_qualifications_text,
            'current_enrollment': latest_appraisal.current_enrollment,
            'last_research': '\n\n'.join(research_history),
            'ongoing_research': latest_appraisal.ongoing_research,
            'publications': '\n'.join(publications),
            'conference_papers': '\n'.join(conferences),
            'consultancy_work': '\n\n'.join(consultancy),
            'administrative_posts': '\n\n'.join(admin_posts),
            'participation_within_university': '\n\n'.join(participation_internal),
            'participation_outside_university': '\n\n'.join(participation_external),
            'objectives_next_year': latest_appraisal.objectives_next_year,
            'appraiser_comments_history': appraiser_comments
        }

        return JsonResponse({
            'success': True,
            'data': combined_data
        })

    except Exception as e:
        print(f"Error in get_employee_data: {str(e)}")  # Debug print
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

class ContractListView(LoginRequiredMixin, ListView):
    model = Contract
    template_name = 'contract/contract_list.html'
    context_object_name = 'contracts'

    def dispatch(self, request, *args, **kwargs):
        # Check if user is HR
        if not request.user.groups.filter(name='HR').exists():
            return redirect('contract:submission')  # Redirects to contract/form/
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.user.groups.filter(name='HR').exists():
            contract_status = request.POST.get('contract_status') == 'on'
            cache.set('contract_enabled', contract_status, timeout=86400)  # 24 hours
            messages.success(request, f"Contract system has been {'enabled' if contract_status else 'disabled'}")
            return redirect('contract:list')
        return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contract_enabled'] = cache.get('contract_enabled', False)
        context['is_hr'] = self.request.user.groups.filter(name='HR').exists()
        return context

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='HR').exists():
            return Contract.objects.all().order_by('-submission_date')
        return Contract.objects.filter(employee__user=user).order_by('-submission_date')

class ContractDeleteView(LoginRequiredMixin, DeleteView):
    model = Contract
    success_url = reverse_lazy('contract:list')
    
    def dispatch(self, request, *args, **kwargs):
        # Only HR can delete contracts
        if not request.user.groups.filter(name='HR').exists():
            messages.error(request, "You don't have permission to delete contracts.")
            return redirect('contract:list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Contract deleted successfully.")
        return super().delete(request, *args, **kwargs)

class ContractReviewView(LoginRequiredMixin, UpdateView):
    model = Contract
    template_name = 'contract/review.html'
    form_class = ContractRenewalForm
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='HR').exists():
            messages.error(request, "You don't have permission to review contracts.")
            return redirect('contract:list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        messages.success(self.request, "Contract review completed successfully.")
        return reverse_lazy('contract:list')