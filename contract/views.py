from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, FileResponse, HttpResponseNotFound, HttpResponseRedirect
from django.core.cache import cache
from .models import Contract, AdministrativePosition, DeanReview, SMTReview
from .forms import ContractRenewalForm, ContractForm
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
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import spacy
from django.conf import settings
import en_core_web_sm
from .scopus import ScopusPublicationsFetcher
import os
from django.db import models


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
                if employee.appointment_type and employee.appointment_type.name == 'Contract':
                    contract_status = ContractRenewalStatus.objects.filter(
                        employee=employee
                    ).first()
                    context['contract_enabled'] = contract_status.is_enabled if contract_status else False
            except Employee.DoesNotExist:
                context['contract_enabled'] = False
        
        # Get employee's previous contracts count
        if hasattr(self.request.user, 'employee'):
            previous_contracts_count = Contract.objects.filter(
                employee=self.request.user.employee
            ).count()
            # Always show at least 1 contract
            context['contract_count'] = max(1, previous_contracts_count)
            
            # Get employee's previous contract if it exists
            previous_contract = Contract.objects.filter(
                employee=self.request.user.employee
            ).order_by('-submission_date').first()
            
            if previous_contract:
                context['previous_contract'] = previous_contract
                
        # Add contract type choices
        context['contract_type_choices'] = Contract.CONTRACT_TYPE_CHOICES
        
        return context


    def form_valid(self, form):
        form.instance.employee = self.request.user.employee
        form.instance.status = 'pending'

        # Handle consultancy work
        consultancy_data = self.request.POST.get('consultancy_work')
        if consultancy_data:
            try:
                json.loads(consultancy_data)
                form.instance.consultancy_work = consultancy_data
            except json.JSONDecodeError:
                form.instance.consultancy_work = '[]'
        else:
            form.instance.consultancy_work = '[]'

        # Handle research history
        research_history = self.request.POST.get('last_research')
        if research_history:
            try:
                json.loads(research_history)
                form.instance.last_research = research_history
            except json.JSONDecodeError:
                form.instance.last_research = '[]'
        else:
            form.instance.last_research = '[]'

        # Handle ongoing research
        ongoing_research = self.request.POST.get('ongoing_research')
        if ongoing_research:
            try:
                json.loads(ongoing_research)
                form.instance.ongoing_research = ongoing_research
            except json.JSONDecodeError:
                form.instance.ongoing_research = '[]'
        else:
            form.instance.ongoing_research = '[]'

        # Handle conference papers
        conference_papers = self.request.POST.get('conference_papers')
        if conference_papers:
            try:
                json.loads(conference_papers)
                form.instance.conference_papers = conference_papers
            except json.JSONDecodeError:
                form.instance.conference_papers = '[]'
        else:
            form.instance.conference_papers = '[]'

        # Handle teaching documents data
        teaching_documents = self.request.FILES.get('teaching_documents')
        if teaching_documents:
            form.instance.teaching_documents = teaching_documents.read()
            form.instance.teaching_documents_name = teaching_documents.name

        # Handle teaching modules data
        teaching_modules_data = self.request.POST.get('teaching_modules_text')
        if teaching_modules_data:
            try:
                modules = json.loads(teaching_modules_data)
                valid_modules = [
                    module for module in modules 
                    if any(str(value).strip() for value in module.values())
                ]
                form.instance.teaching_modules_text = json.dumps(valid_modules)
            except json.JSONDecodeError:
                form.instance.teaching_modules_text = '[]'
        else:
            form.instance.teaching_modules_text = '[]'
        
        # Handle attendance data
        attendance_data = self.request.POST.get('attendance_data')
        if attendance_data:
            try:
                json.loads(attendance_data)
                form.instance.attendance = attendance_data
            except json.JSONDecodeError:
                form.instance.attendance = '[]'
        else:
            form.instance.attendance = '[]'
            
        # Handle administrative positions data
        response = super().form_valid(form)
        administrative_positions_data = self.request.POST.get('administrative_positions_text')
        form.instance.administrative_positions_text = '[]'  # Default to empty list
        if administrative_positions_data:
            try:
                positions = json.loads(administrative_positions_data)
                for position in positions:
                    # Create and save each administrative position
                    AdministrativePosition.objects.create(
                        contract=form.instance,
                        title=position.get('position', ''),
                        from_date=position.get('fromDate', None),
                        to_date=position.get('toDate', None),
                        details=position.get('details', '')
                    )
            except json.JSONDecodeError:
                pass
        
        # Handle university committees data
        university_committees_data = self.request.POST.get('university_committees_text')
        if university_committees_data:
            try:
                committees = json.loads(university_committees_data)
                # Modified validation: only filter out completely empty committees
                valid_committees = [
                    committee for committee in committees 
                    if any(value.strip() for value in committee.values() if value)  # Check if any field has content
                ]
                form.instance.university_committees_text = json.dumps(valid_committees)
            except json.JSONDecodeError:
                form.instance.university_committees_text = '[]'
        else:
            form.instance.university_committees_text = '[]'

        # Handle external committees data
        external_committees_data = self.request.POST.get('external_committees_text')
        if external_committees_data:
            try:
                committees = json.loads(external_committees_data)
                # Modified validation: only filter out completely empty committees
                valid_committees = [
                    committee for committee in committees 
                    if any(value.strip() for value in committee.values() if value)  # Check if any field has content
                ]
                form.instance.external_committees_text = json.dumps(valid_committees)
            except json.JSONDecodeError:
                form.instance.external_committees_text = '[]'
        else:
            form.instance.external_committees_text = '[]'
        
            # Create notification for HR users
        try:
            hr_group = Group.objects.get(name='HR')
            hr_users = hr_group.user_set.all()
            submission_date = form.instance.submission_date.strftime('%B %d, %Y')
            message = f"{self.request.user.employee.get_full_name()} has submitted a contract renewal form on {submission_date}"
            
            for hr_user in hr_users:
                try:
                    hr_employee = Employee.objects.get(user=hr_user)
                    ContractNotification.objects.create(
                        employee=hr_employee,
                        message=message,
                        read=False,
                        contract=form.instance
                    )
                except Employee.DoesNotExist:
                    continue
        except Group.DoesNotExist:
            print("HR group not found")
        except Exception as e:
            print(f"Error creating HR notification: {str(e)}")
        
        contract = form.save()
        return response

    def get(self, request, *args, **kwargs):
        # Check if user has a pending submission
        existing_submission = Contract.objects.filter(
            employee=request.user.employee,
            status__in=['pending', 'smt_review', 'sent_back']
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

        def process_research_fields():
            """
            Process research fields using NLP to identify similar research topics
            and categorize them based on the most recent appraisal
            """
            try:
                nlp = en_core_web_sm.load()
            except OSError:
                # Fallback if spaCy model isn't installed
                return latest_appraisal.last_research or '', latest_appraisal.ongoing_research or ''

            def normalize_text(text):
                """Normalize text for NLP processing"""
                # Convert to lowercase and remove extra whitespace
                text = ' '.join(text.lower().split())
                # Process with spaCy
                doc = nlp(text)
                # Return processed tokens, excluding stopwords and punctuation
                return ' '.join(token.text for token in doc if not token.is_stop and not token.is_punct)

            def are_similar(text1, text2, threshold=0.85):
                """Compare two texts for similarity using spaCy"""
                if not text1 or not text2:
                    return False
                doc1 = nlp(normalize_text(text1))
                doc2 = nlp(normalize_text(text2))
                return doc1.similarity(doc2) > threshold

            # Get research entries from latest appraisal
            latest_research = set(
                item.strip() 
                for item in (latest_appraisal.last_research or '').split('\n') 
                if item.strip()
            )
            latest_ongoing = set(
                item.strip() 
                for item in (latest_appraisal.ongoing_research or '').split('\n') 
                if item.strip()
            )

            # Track all unique research entries
            all_research = {}  # {normalized_text: {original_text, status, appraisal_date}}

            # Process all appraisals from newest to oldest
            for appraisal in appraisals:
                appraisal_date = appraisal.date_of_last_appraisal

                # Process completed research
                if appraisal.last_research:
                    for research in appraisal.last_research.split('\n'):
                        research = research.strip()
                        if not research:
                            continue

                        # Check if this research is similar to any we've seen
                        is_new = True
                        normalized = normalize_text(research)
                        
                        for existing in all_research:
                            if are_similar(normalized, existing):
                                is_new = False
                                # Update only if this is from a newer appraisal
                                if appraisal_date > all_research[existing]['date']:
                                    all_research[existing] = {
                                        'text': research,
                                        'status': 'completed',
                                        'date': appraisal_date
                                    }
                                break
                        
                        if is_new:
                            all_research[normalized] = {
                                'text': research,
                                'status': 'completed',
                                'date': appraisal_date
                            }

                # Process ongoing research
                if appraisal.ongoing_research:
                    for research in appraisal.ongoing_research.split('\n'):
                        research = research.strip()
                        if not research:
                            continue

                        normalized = normalize_text(research)
                        is_new = True

                        for existing in all_research:
                            if are_similar(normalized, existing):
                                is_new = False
                                # Update only if this is from a newer appraisal
                                if appraisal_date > all_research[existing]['date']:
                                    all_research[existing] = {
                                        'text': research,
                                        'status': 'ongoing',
                                        'date': appraisal_date
                                    }
                                break
                        
                        if is_new:
                            all_research[normalized] = {
                                'text': research,
                                'status': 'ongoing',
                                'date': appraisal_date
                            }

            # Separate research based on latest status
            completed_research = []
            ongoing_research = []

            for entry in all_research.values():
                if entry['status'] == 'completed':
                    completed_research.append(entry['text'])
                else:
                    ongoing_research.append(entry['text'])

            return '\n'.join(completed_research), '\n'.join(ongoing_research)

        # Get processed research data
        last_research, ongoing_research = process_research_fields()

        def process_status_fields(field_name):
            """
            Process fields that might contain status indicators
            Keep ONGOING items unless they have a FINISHED status
            Remove duplicates (case-insensitive and punctuation-insensitive)
            """
            status_tracker = {}
            seen_items = set()
            
            def normalize_text(text):
                """Normalize text for comparison by removing punctuation and extra spaces"""
                import re
                # Remove status indicators before normalization
                text = text.replace('(ONGOING)', '').replace('(FINISHED)', '')
                # Remove all punctuation and convert to lowercase
                text = re.sub(r'[^\w\s]', '', text.lower())
                # Normalize whitespace
                text = ' '.join(text.split())
                return text
            
            for appraisal in appraisals:
                content = getattr(appraisal, field_name, '') or ''
                if not content:
                    continue
                
                items = [item.strip() for item in content.split('\n') if item.strip()]
                
                for item in items:
                    base_item = item.replace('(ONGOING)', '').replace('(FINISHED)', '').strip()
                    is_finished = '(FINISHED)' in item
                    is_ongoing = '(ONGOING)' in item
                    
                    normalized = normalize_text(base_item)
                    
                    if normalized not in seen_items:
                        seen_items.add(normalized)
                        status_tracker[normalized] = {
                            'text': base_item,
                            'status': 'FINISHED' if is_finished else ('ONGOING' if is_ongoing else None),
                            'original': item
                        }
                    elif is_finished:
                        # Update status to FINISHED if it wasn't already
                        status_tracker[normalized]['status'] = 'FINISHED'
                        status_tracker[normalized]['original'] = item
                    elif is_ongoing and status_tracker[normalized]['status'] != 'FINISHED':
                        # Update to ONGOING only if not FINISHED
                        status_tracker[normalized]['status'] = 'ONGOING'
                        status_tracker[normalized]['original'] = item

            # Sort items by status and original text
            finished_items = []
            ongoing_items = []
            regular_items = []
            
            for item_data in status_tracker.values():
                if item_data['status'] == 'FINISHED':
                    finished_items.append(item_data['original'])
                elif item_data['status'] == 'ONGOING':
                    ongoing_items.append(item_data['original'])
                else:
                    regular_items.append(item_data['original'])
            
            all_items = finished_items + ongoing_items + regular_items
            return '\n'.join(all_items) if all_items else ''

        def process_objectives():
            """
            Combine all 'Teaching and Research Objectives for Next Year' entries
            Remove duplicates (case-insensitive and punctuation-insensitive)
            """
            seen_objectives = set()
            unique_objectives = []
            
            def normalize_text(text):
                """Normalize text for comparison by removing punctuation and extra spaces"""
                import re
                # Remove all punctuation and convert to lowercase
                text = re.sub(r'[^\w\s]', '', text.lower())
                # Normalize whitespace
                text = ' '.join(text.split())
                return text
            
            for appraisal in appraisals:
                if appraisal.objectives_next_year and appraisal.objectives_next_year.strip():
                    objectives = [obj.strip() for obj in appraisal.objectives_next_year.split('\n') if obj.strip()]
                    
                    for objective in objectives:
                        # Normalize for comparison
                        normalized = normalize_text(objective)
                        if normalized not in seen_objectives:
                            seen_objectives.add(normalized)
                            unique_objectives.append(objective)
            
            return '\n'.join(unique_objectives) if unique_objectives else ''

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
            'objectives_next_year': process_objectives(),
            'incremental_date': latest_appraisal.incremental_date.strftime('%Y-%m-%d') if latest_appraisal.incremental_date else '',
            'date_of_last_appraisal': latest_appraisal.date_of_last_appraisal.strftime('%Y-%m-%d') if latest_appraisal.date_of_last_appraisal else '',
            'last_research': last_research,
            'ongoing_research': ongoing_research,
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
            appointment_type__name='Contract'
        ).select_related('department')

        employees_data = []
        today = datetime.now().date()
        
        # Check if user is a dean
        is_dean = request.user.groups.filter(name='Dean').exists()
        
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
            'is_dean': True,
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
        
        # Fetch administrative positions
        administrative_positions = contract.administrative_positions.all()
        context['administrative_positions'] = administrative_positions
        
        try:
            # Parse academic qualifications
            academic_quals = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
        except json.JSONDecodeError:
            academic_quals = []
            print("Error parsing academic qualifications")
        
        # Parse teaching modules
        try:
            teaching_modules = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
        except json.JSONDecodeError:
            teaching_modules = []
            print("Error parsing teaching modules")

        # Parse participation data
        try:
            participation_within = json.loads(contract.participation_within_text) if contract.participation_within_text else []
            participation_outside = json.loads(contract.participation_outside_text) if contract.participation_outside_text else []
        except json.JSONDecodeError:
            participation_within = []
            participation_outside = []
        
        # Parse university committees
        try:
            university_committees = json.loads(contract.university_committees_text) if contract.university_committees_text else []
        except json.JSONDecodeError:
            university_committees = []
        
        # Parse external committees
        try:
            external_committees = json.loads(contract.external_committees_text) if contract.external_committees_text else []
        except json.JSONDecodeError:
            external_committees = []
        
        # Add committee data to context
        context['university_committees'] = university_committees
        context['external_committees'] = external_committees
        
        # IC Color mapping
        IC_COLOURS = {
            'Y': 'Yellow',
            'P': 'Purple',
            'G': 'Green',
            'R': 'Red'
        }
        
        context.update({
            'contract': contract,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': IC_COLOURS.get(employee.ic_colour, employee.ic_colour),
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'contract_count': Contract.objects.filter(
                employee=contract.employee,
                submission_date__lt=contract.submission_date
            ).count() + 1,
            'academic_qualifications': academic_quals,
            'teaching_modules': teaching_modules,
            'participation_within': participation_within,
            'participation_outside': participation_outside,
            'teaching_future_plan': contract.teaching_future_plan,
            'is_review': True,
            'university_committees': university_committees,
            'external_committees': external_committees,
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
        
        # Add attendance data to context
        try:
            context['attendance_events'] = json.loads(contract.attendance) if contract.attendance else []
        except json.JSONDecodeError:
            context['attendance_events'] = []

        # Parse JSON data for research sections
        try:
            context['consultancy_work'] = json.loads(contract.consultancy_work) if contract.consultancy_work else []
        except json.JSONDecodeError:
            context['consultancy_work'] = []

        try:
            context['research_history'] = json.loads(contract.last_research) if contract.last_research else []
        except json.JSONDecodeError:
            context['research_history'] = []

        try:
            context['ongoing_research'] = json.loads(contract.ongoing_research) if contract.ongoing_research else []
        except json.JSONDecodeError:
            context['ongoing_research'] = []

        try:
            context['conference_papers'] = json.loads(contract.conference_papers) if contract.conference_papers else []
        except json.JSONDecodeError:
            context['conference_papers'] = []

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
            appointment_type__name='Contract',
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
        
        # Create notification for SMT users
        try:
            smt_group = Group.objects.get(name='SMT')
            smt_users = smt_group.user_set.all()
            
            for smt_user in smt_users:
                try:
                    smt_employee = Employee.objects.get(user=smt_user)
                    # Create notification with link to SMT review page
                    review_url = reverse('contract:smt_review', args=[contract.id])
                    message = f"HR has forwarded contract {contract.contract_id} for {contract.employee.get_full_name()} for SMT review. "
                    message += f'<a href="{review_url}" class="text-blue-600 hover:underline">Review Contract</a>'
                    
                    ContractNotification.objects.create(
                        employee=smt_employee,
                        message=message,
                        read=False,
                        contract=contract
                    )
                except Employee.DoesNotExist:
                    continue
        except Group.DoesNotExist:
            pass
        
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class ViewAllSubmissionsView(LoginRequiredMixin, View):
    template_name = 'contract/all_submissions.html'

    def get(self, request):
        if not (request.user.groups.filter(name='HR').exists() or request.user.groups.filter(name='SMT').exists()):
            return redirect('contract:submission')
        
        today = datetime.now().date()
        filter_param = request.GET.get('filter')
        
        # For SMT users with specific filters
        if request.user.groups.filter(name='SMT').exists():
            if filter_param == 'approved':
                in_process_contracts = Contract.objects.filter(
                    status='approved'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
            elif filter_param == 'rejected':
                in_process_contracts = Contract.objects.filter(
                    status='rejected'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
            else:
                # Default view for SMT - show contracts waiting for review
                in_process_contracts = Contract.objects.filter(
                    status='smt_review'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
        elif request.user.groups.filter(name='HR').exists():
            # For HR users, show all contracts
            in_process_contracts = Contract.objects.filter(
                status__in=['smt_review', 'approved', 'rejected', 'sent_back', 'dean_review']
            ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]

            pending_contracts = Contract.objects.filter(
            status='pending'
            ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
        else:
            # For other users
            in_process_contracts = Contract.objects.none()
            pending_contracts = Contract.objects.none()
        
        

        # Pre-calculate months_remaining to avoid doing it in the template
        for contracts in [in_process_contracts, pending_contracts]:
            for contract in contracts:
                renewal_date = contract.employee.hire_date + relativedelta(years=3)
                while renewal_date < today:
                    renewal_date += relativedelta(years=3)
                
                r_date = datetime(renewal_date.year, renewal_date.month, 1)
                t_date = datetime(today.year, today.month, 1)
                
                contract.months_remaining = ((r_date.year - t_date.year) * 12 + 
                                          r_date.month - t_date.month)

        context = {
            'in_process_contracts': in_process_contracts,
            'pending_contracts': pending_contracts,
            'departments': Department.objects.all(),
            'is_smt': request.user.groups.filter(name='SMT').exists(),
            'filter': filter_param,
        }
        
        return render(request, self.template_name, context)

class EmployeeContractView(LoginRequiredMixin, View):
    template_name = 'contract/employee_contracts.html'

    def get(self, request):
        if request.user.groups.filter(name='HR').exists():
            return redirect('contract:list')
        
        # Fetch contracts for the current user
        previous_contracts = Contract.objects.filter(
            employee=request.user.employee,
            status__in=['approved', 'rejected']
        ).select_related('employee', 'employee__department')

        current_contracts = Contract.objects.filter(
            employee=request.user.employee,
            status__in=['pending', 'smt_review', 'sent_back', 'dean_review']
        ).select_related('employee', 'employee__department')

        context = {
            'previous_contracts': previous_contracts,
            'current_contracts': current_contracts,
            'departments': Department.objects.all()
        }

        return render(request, self.template_name, context)

def some_view(request):
    if not request.user.groups.filter(name='HR').exists():
        return redirect('contract:employee_contracts')
    # HR logic here

class ContractRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        if request.user.groups.filter(name='HR').exists():
            return redirect('contract:all_submissions')
        elif request.user.groups.filter(name='SMT').exists():
            # For SMT users, show all contracts in SMT review
            return redirect('contract:all_submissions')  # They can use the same view as HR
        elif request.user.groups.filter(name__in=['Dean', 'HOD']).exists():
            return redirect('contract:dean_department_contracts')
        else:
            return redirect('contract:employee_contracts')

class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = 'contract/contract_detail.html'
    context_object_name = 'contract'

    def get_queryset(self):
        # For HR users, allow access to all contracts
        if self.request.user.groups.filter(name='HR').exists():
            return Contract.objects.all().select_related('employee', 'employee__department')
        
        # For deans, allow access to contracts in their department
        if self.request.user.groups.filter(name__in=['Dean', 'HOD']).exists():
            try:
                dean_employee = Employee.objects.get(user=self.request.user)
                return Contract.objects.filter(
                    employee__department=dean_employee.department
                ).select_related('employee', 'employee__department')
            except Employee.DoesNotExist:
                return Contract.objects.none()
        
        # For regular employees, only show their own contracts
        return Contract.objects.filter(
            employee__user=self.request.user
        ).select_related('employee', 'employee__department')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Define IC_COLOURS dictionary
        IC_COLOURS = {
            'Y': 'Yellow',
            'P': 'Purple',
            'G': 'Green',
            'R': 'Red'
        }
        
        # Fetch employee details
        employee = self.object.employee
        context.update({
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': IC_COLOURS.get(employee.ic_colour, employee.ic_colour),
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else 'None',
        })
        
        # Parse JSON fields
        try:
            context['academic_qualifications'] = json.loads(self.object.academic_qualifications_text or '[]')
        except json.JSONDecodeError:
            context['academic_qualifications'] = []
        
        try:
            context['teaching_modules'] = json.loads(self.object.teaching_modules_text or '[]')
        except json.JSONDecodeError:
            context['teaching_modules'] = []
        
        try:
            context['participation_within'] = json.loads(self.object.participation_within_text or '[]')
            context['participation_outside'] = json.loads(self.object.participation_outside_text or '[]')
        except json.JSONDecodeError:
            context['participation_within'] = []
            context['participation_outside'] = []
        
        # Get dean reviews
        context['dean_reviews'] = DeanReview.objects.filter(contract=self.object).order_by('-created_at')
        
        # Get SMT reviews
        context['smt_reviews'] = SMTReview.objects.filter(contract=self.object).order_by('-created_at')
        
        return context

@login_required
@require_POST
@csrf_exempt  # Optionally exempt CSRF for AJAX calls if needed
def delete_all_notifications(request):
    try:
        notifications = ContractNotification.objects.filter(employee__user=request.user)
        count = notifications.count()
        notifications.delete()
        return JsonResponse({'status': 'success', 'deleted_count': count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def fetch_publications(request, scopus_id):
    try:
        # Initialize the fetcher with your API key
        api_key = settings.SCOPUS_API_KEY
        fetcher = ScopusPublicationsFetcher(api_key)
        
        # Add some debug logging
        print(f"Fetching publications for Scopus ID: {scopus_id}")
        
        # Fetch publications
        publications = fetcher.fetch_publications(scopus_id)
        
        # Debug print
        print(f"Found {len(publications)} publications")
        
        return JsonResponse({
            'success': True,
            'publications': publications,
            'count': len(publications)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'error_details': str(e)
        })

def review_contract(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    # Parse teaching modules data
    teaching_modules = []
    if contract.teaching_modules_text:
        try:
            teaching_modules = json.loads(contract.teaching_modules_text)
        except json.JSONDecodeError:
            teaching_modules = []
    
    # Parse university committees data
    university_committees = []
    if contract.university_committees_text:
        try:
            university_committees = json.loads(contract.university_committees_text)
        except json.JSONDecodeError:
            university_committees = []
    
    # Parse external committees data
    external_committees = []
    if contract.external_committees_text:
        try:
            external_committees = json.loads(contract.external_committees_text)
        except json.JSONDecodeError:
            external_committees = []
            
            
    consultancy_work = []
    if contract.consultancy_work:
        try:
            consultancy_work = json.loads(contract.consultancy_work)
        except json.JSONDecodeError:
            consultancy_work = []
    
    
    # Parse research history data
    research_history = []
    if contract.last_research:
        try:
            research_history = json.loads(contract.last_research)
        except json.JSONDecodeError:
            research_history = []
    
    # Parse ongoing research data
    ongoing_research = []
    if contract.ongoing_research:
        try:
            ongoing_research = json.loads(contract.ongoing_research)
        except json.JSONDecodeError:
            ongoing_research = []
    
    # Parse conference papers data
    conference_papers = []
    if contract.conference_papers:
        try:
            conference_papers = json.loads(contract.conference_papers)
        except json.JSONDecodeError:
            conference_papers = []
    
    context = {
        'contract': contract,
        'teaching_modules': teaching_modules,
        'university_committees': university_committees,
        'external_committees': external_committees,
        'consultancy_work': consultancy_work,
        'research_history': research_history,
        'ongoing_research': ongoing_research,
        'conference_papers': conference_papers,
        # ... rest of your context data ...
    }
    
    return render(request, 'contract/review.html', context)

@login_required
def download_document(request, contract_id, doc_type):
    contract = get_object_or_404(Contract, id=contract_id)
    
    if doc_type == 'teaching' and contract.teaching_documents:
        response = HttpResponse(contract.teaching_documents, content_type='application/pdf')  # Adjust content type as needed
        response['Content-Disposition'] = f'attachment; filename="{contract.teaching_documents_name}"'
        return response
    
    return HttpResponseNotFound('Document not found')

@login_required
@require_POST
def submit_contract(request):
    form = ContractForm(request.POST)
    if form.is_valid():
        contract = form.save(commit=False)
        
        # Save university committees data
        university_committees_data = request.POST.get('university_committees_text')
        contract.university_committees_text = university_committees_data
        
        # Save external committees data
        external_committees_data = request.POST.get('external_committees_text')
        contract.external_committees_text = external_committees_data
        
        contract.save()
        messages.success(request, "Contract submitted successfully.")
        return redirect('contract:review', contract_id=contract.id)
    else:
        messages.error(request, "There was an error submitting the contract.")
        return render(request, 'contract/submission.html', {'form': form})

@login_required
@require_POST
def send_back_to_employee(request, contract_id):
    try:
        contract = Contract.objects.get(pk=contract_id)
        data = json.loads(request.body)
        comments = data.get('comments')
        
        if not comments:
            return JsonResponse({'error': 'Comments are required'}, status=400)
            
        # Update contract status
        contract.status = 'sent_back'
        contract.save()
        
        # Create notification for employee
        ContractNotification.objects.create(
            employee=contract.employee,
            contract=contract,
            message=f"Your contract renewal form has been returned for revision. HR Comments: {comments}",
            metadata={'hr_comments': comments}
        )
        
        return JsonResponse({'status': 'success'})
    except Contract.DoesNotExist:
        return JsonResponse({'error': 'Contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_hr_comments(request, contract_id):
    try:
        contract = Contract.objects.get(pk=contract_id)
        notification = ContractNotification.objects.filter(
            contract=contract,
            employee=request.user.employee
        ).latest('created_at')
        
        return JsonResponse({
            'comments': notification.metadata.get('hr_comments', 'No comments available')
        })
    except (Contract.DoesNotExist, ContractNotification.DoesNotExist):
        return JsonResponse({'error': 'Comments not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class EditSubmissionView(LoginRequiredMixin, UpdateView):
    model = Contract
    template_name = 'contract/submission.html'
    form_class = ContractRenewalForm
    success_url = reverse_lazy('contract:thank_you')
    
    def get_queryset(self):
        return Contract.objects.filter(
            employee=self.request.user.employee,
            status='sent_back'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit_mode'] = True
        
        # Add contract type choices
        context['contract_type_choices'] = Contract.CONTRACT_TYPE_CHOICES
        
        # Get employee's previous contracts count
        previous_contracts_count = Contract.objects.filter(
            employee=self.request.user.employee
        ).count()
        # Always show at least 1 contract
        context['contract_count'] = max(1, previous_contracts_count)
        
        return context
    
    def form_valid(self, form):
        # Set status back to pending
        form.instance.status = 'pending'
        
        # Handle consultancy work
        consultancy_data = self.request.POST.get('consultancy_work')
        if consultancy_data:
            try:
                json.loads(consultancy_data)
                form.instance.consultancy_work = consultancy_data
            except json.JSONDecodeError:
                form.instance.consultancy_work = '[]'
        else:
            form.instance.consultancy_work = '[]'

        # Handle research history
        research_history = self.request.POST.get('last_research')
        if research_history:
            try:
                json.loads(research_history)
                form.instance.last_research = research_history
            except json.JSONDecodeError:
                form.instance.last_research = '[]'
        else:
            form.instance.last_research = '[]'

        # Handle ongoing research
        ongoing_research = self.request.POST.get('ongoing_research')
        if ongoing_research:
            try:
                json.loads(ongoing_research)
                form.instance.ongoing_research = ongoing_research
            except json.JSONDecodeError:
                form.instance.ongoing_research = '[]'
        else:
            form.instance.ongoing_research = '[]'

        # Handle conference papers
        conference_papers = self.request.POST.get('conference_papers')
        if conference_papers:
            try:
                json.loads(conference_papers)
                form.instance.conference_papers = conference_papers
            except json.JSONDecodeError:
                form.instance.conference_papers = '[]'
        else:
            form.instance.conference_papers = '[]'

        # Handle teaching documents data
        teaching_documents = self.request.FILES.get('teaching_documents')
        if teaching_documents:
            form.instance.teaching_documents = teaching_documents.read()
            form.instance.teaching_documents_name = teaching_documents.name

        # Handle teaching modules data
        teaching_modules_data = self.request.POST.get('teaching_modules_text')
        if teaching_modules_data:
            try:
                modules = json.loads(teaching_modules_data)
                valid_modules = [
                    module for module in modules 
                    if any(str(value).strip() for value in module.values())
                ]
                form.instance.teaching_modules_text = json.dumps(valid_modules)
            except json.JSONDecodeError:
                form.instance.teaching_modules_text = '[]'
        else:
            form.instance.teaching_modules_text = '[]'
        
        # Handle attendance data
        attendance_data = self.request.POST.get('attendance_data')
        if attendance_data:
            try:
                json.loads(attendance_data)
                form.instance.attendance = attendance_data
            except json.JSONDecodeError:
                form.instance.attendance = '[]'
        else:
            form.instance.attendance = '[]'
        
        # First save the form to ensure we have a valid instance
        self.object = form.save()
            
        # Handle administrative positions data
        administrative_positions_data = self.request.POST.get('administrative_positions_text')
        
        # Clear existing administrative positions
        self.object.administrative_positions.all().delete()
        
        if administrative_positions_data:
            try:
                positions = json.loads(administrative_positions_data)
                for position in positions:
                    # Create and save each administrative position
                    AdministrativePosition.objects.create(
                        contract=self.object,
                        title=position.get('position', ''),
                        from_date=position.get('fromDate', None),
                        to_date=position.get('toDate', None),
                        details=position.get('details', '')
                    )
            except json.JSONDecodeError:
                pass
        
        # Handle university committees data
        university_committees_data = self.request.POST.get('university_committees_text')
        if university_committees_data:
            try:
                committees = json.loads(university_committees_data)
                # Modified validation: only filter out completely empty committees
                valid_committees = [
                    committee for committee in committees 
                    if any(value.strip() for value in committee.values() if value)  # Check if any field has content
                ]
                self.object.university_committees_text = json.dumps(valid_committees)
            except json.JSONDecodeError:
                self.object.university_committees_text = '[]'
        else:
            self.object.university_committees_text = '[]'

        # Handle external committees data
        external_committees_data = self.request.POST.get('external_committees_text')
        if external_committees_data:
            try:
                committees = json.loads(external_committees_data)
                # Modified validation: only filter out completely empty committees
                valid_committees = [
                    committee for committee in committees 
                    if any(value.strip() for value in committee.values() if value)  # Check if any field has content
                ]
                self.object.external_committees_text = json.dumps(valid_committees)
            except json.JSONDecodeError:
                self.object.external_committees_text = '[]'
        else:
            self.object.external_committees_text = '[]'
        
        # Save the object again with all the updated fields
        self.object.save()
        
        # Create notification for HR users
        try:
            hr_group = Group.objects.get(name='HR')
            hr_users = hr_group.user_set.all()
            submission_date = timezone.now().strftime('%B %d, %Y')
            message = f"{self.request.user.employee.get_full_name()} has resubmitted a contract renewal form on {submission_date}"
            
            for hr_user in hr_users:
                try:
                    hr_employee = Employee.objects.get(user=hr_user)
                    ContractNotification.objects.create(
                        employee=hr_employee,
                        message=message,
                        read=False,
                        contract=self.object
                    )
                except Employee.DoesNotExist:
                    continue
        except Group.DoesNotExist:
            print("HR group not found")
        except Exception as e:
            print(f"Error creating HR notification: {str(e)}")
        
        # Return the success URL response
        return HttpResponseRedirect(self.get_success_url())

class DeanContractView(LoginRequiredMixin, View):
    template_name = 'contract/dean_department_contracts.html'

    def get(self, request):
        # Check if user is a dean
        if not request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD']).exists():
            return redirect('contract:redirect')
        
        try:
            # Get the dean's department
            dean_employee = Employee.objects.get(user=request.user)
            dean_department = dean_employee.department
            
            if not dean_department:
                messages.error(request, "You are not assigned to any department.")
                return redirect('dashboard')
            
            # Get contracts waiting for dean review
            dean_review_contracts = Contract.objects.filter(
                employee__department=dean_department,
                status='dean_review'
            ).select_related('employee', 'employee__department').order_by('-submission_date')
            
            # Calculate months remaining for each contract
            today = datetime.now().date()
            for contract in dean_review_contracts:
                renewal_date = contract.employee.hire_date + relativedelta(years=3)
                while renewal_date < today:
                    renewal_date += relativedelta(years=3)
                
                r_date = datetime(renewal_date.year, renewal_date.month, 1)
                t_date = datetime(today.year, today.month, 1)
                
                contract.months_remaining = ((r_date.year - t_date.year) * 12 + 
                                          r_date.month - t_date.month)
            
            context = {
                'department': dean_department,
                'dean_review_contracts': dean_review_contracts,
            }
            
            return render(request, self.template_name, context)
            
        except Employee.DoesNotExist:
            messages.error(request, "Employee profile not found.")
            return redirect('dashboard')

# Add this view class
class DeanReviewView(LoginRequiredMixin, View):
    template_name = 'contract/dean_review.html'
    
    def get(self, request, contract_id):
        # Check if user is a dean
        if not request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD']).exists():
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard')
        
        # Get the contract
        contract = get_object_or_404(Contract, pk=contract_id)
        
        # Check if the dean is from the same department as the employee
        dean_employee = get_object_or_404(Employee, user=request.user)
        if dean_employee.department != contract.employee.department:
            messages.error(request, "You can only review contracts from your department.")
            return redirect('contract:dean_department_contracts')
        
        # Get the latest dean review by this dean (if any)
        dean_review = DeanReview.objects.filter(
            contract=contract,
            dean=dean_employee
        ).first()
        
        # Get previous reviews by other deans
        previous_dean_reviews = DeanReview.objects.filter(
            contract=contract
        ).exclude(dean=dean_employee)
        
        # Prepare context data similar to the review view
        context = {
            'contract': contract,
            'first_name': contract.employee.first_name,
            'last_name': contract.employee.last_name,
            'ic_no': contract.employee.ic_no,
            'ic_colour': contract.employee.ic_colour,
            'phone_number': contract.employee.phone_number,
            'department': contract.employee.department.name if contract.employee.department else '',
            'dean_review': dean_review,
            'previous_dean_reviews': previous_dean_reviews,
        }
        
        # Add other context data as needed (similar to your ContractReviewView)
        # You can copy the relevant parts from your existing review view
        
        return render(request, self.template_name, context)

@login_required
def submit_dean_review(request, contract_id):
    # Check if user is a dean
    if not request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD']).exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Check if the dean is from the same department as the employee
    dean_employee = get_object_or_404(Employee, user=request.user)
    if dean_employee.department != contract.employee.department:
        messages.error(request, "You can only review contracts from your department.")
        return redirect('contract:dean_department_contracts')
    
    # Get form data
    comments = request.POST.get('dean_comments', '').strip()
    
    if not comments:
        messages.error(request, "Comments are required.")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Get or create dean review
    dean_review, created = DeanReview.objects.get_or_create(
        contract=contract,
        dean=dean_employee,
        defaults={
            'comments': comments
        }
    )
    
    if not created:
        # Update existing review
        dean_review.comments = comments
    
    # Handle document upload
    document = request.FILES.get('dean_documents')
    if document:
        dean_review.document = document.read()
        dean_review.document_name = document.name
    
    dean_review.save()
    
    # Update contract status to indicate dean has reviewed
    if contract.status == 'dean_review':
        # Change status back to pending for HR to review
        contract.status = 'pending'
        contract.save()
    
    # Create notification for HR
    try:
        hr_group = Group.objects.get(name='HR')
        hr_users = hr_group.user_set.all()
        
        for hr_user in hr_users:
            try:
                hr_employee = Employee.objects.get(user=hr_user)
                hr_message = f"Dean {dean_employee.get_full_name()} has submitted comments for contract {contract.contract_id} ({contract.employee.get_full_name()})."
                
                # Add document info to notification if a document was uploaded
                if document:
                    hr_message += f" A document has been attached to this decision."
                
                ContractNotification.objects.create(
                    employee=hr_employee,
                    message=hr_message,
                    contract=contract,
                    metadata={
                        'dean_review_id': dean_review.id
                    }
                )
            except Employee.DoesNotExist:
                continue
    except Group.DoesNotExist:
        pass
    
    messages.success(request, "Your comments have been submitted successfully to HR.")
    return redirect('contract:dean_department_contracts')

@login_required
def download_dean_document(request, contract_id, review_id=None):
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        messages.error(request, "You don't have permission to access this document.")
        return redirect('dashboard')
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the review
    if review_id:
        review = get_object_or_404(DeanReview, pk=review_id, contract=contract)
    else:
        # Get the latest review by the current dean if they're a dean
        if request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD']).exists():
            dean_employee = get_object_or_404(Employee, user=request.user)
            review = get_object_or_404(DeanReview, contract=contract, dean=dean_employee)
        else:
            # For HR or the employee, get the latest review
            review = get_object_or_404(DeanReview, contract=contract)
    
    if not review.document:
        messages.error(request, "No document found.")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Determine content type based on file extension
    filename = review.document_name
    content_type = 'application/octet-stream'  # Default
    if filename.endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    # Return the file
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def download_smt_document(request, contract_id, review_id=None):
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['SMT', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        messages.error(request, "You don't have permission to access this document.")
        return redirect('dashboard')
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the review
    if review_id:
        review = get_object_or_404(SMTReview, pk=review_id, contract=contract)
    else:
        # Get the latest review
        review = get_object_or_404(SMTReview, contract=contract)
    
    if not review.document:
        messages.error(request, "No document found.")
        return redirect('contract:contract_detail', pk=contract_id)
    
    # Determine content type based on file extension
    filename = review.document_name
    content_type = 'application/octet-stream'  # Default
    if filename.endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    # Return the file
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@require_POST
def forward_to_dean(request, contract_id):
    # Check if user is HR
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get the contract
        contract = Contract.objects.get(id=contract_id)
        
        # Update contract status
        contract.status = 'dean_review'
        contract.save()
        
        # Create notification for the department dean
        department = contract.employee.department
        if department:
            # Find dean users for this department
            dean_users = User.objects.filter(
                groups__name__in=['Dean', 'HOD'],
                employee__department=department
            )
            
            for dean_user in dean_users:
                try:
                    dean_employee = Employee.objects.get(user=dean_user)
                    ContractNotification.objects.create(
                        employee=dean_employee,
                        message=f"HR has forwarded {contract.employee.get_full_name()}'s contract renewal for your review.",
                        read=False,
                        contract=contract
                    )
                except Employee.DoesNotExist:
                    continue
        
        return JsonResponse({'status': 'success'})
    except Contract.DoesNotExist:
        return JsonResponse({'error': 'Contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class SMTReviewView(LoginRequiredMixin, View):
    template_name = 'contract/smt_review.html'
    
    def get(self, request, contract_id):
        # Check if user is an SMT member
        if not request.user.groups.filter(name='SMT').exists():
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard')
        
        # Get the contract
        contract = get_object_or_404(Contract, pk=contract_id)
        
        # Get the latest dean review (if any)
        dean_review = DeanReview.objects.filter(contract=contract).order_by('-created_at').first()
        
        # Prepare context data similar to the review view
        context = {
            'contract': contract,
            'first_name': contract.employee.first_name,
            'last_name': contract.employee.last_name,
            'ic_no': contract.employee.ic_no,
            'ic_colour': contract.employee.ic_colour,
            'phone_number': contract.employee.phone_number,
            'department': contract.employee.department.name if contract.employee.department else '',
            'dean_review': dean_review,
            'filter': request.GET.get('filter'),  # Pass the filter parameter for tab highlighting
        }
        
        # Add other context data as needed
        try:
            # Parse academic qualifications
            academic_quals = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
            context['academic_qualifications'] = academic_quals
        except json.JSONDecodeError:
            context['academic_qualifications'] = []
        
        # Add other context data similar to ContractReviewView
        # This ensures SMT has all the information they need
        
        return render(request, self.template_name, context)

@login_required
@require_POST
def smt_decision(request, contract_id):
    # Check if user is an SMT member
    if not request.user.groups.filter(name='SMT').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get the contract
        contract = Contract.objects.get(id=contract_id)
        
        # Get form data
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        
        # Validate the decision
        if decision not in ['approved', 'rejected', 'sent_back']:
            return JsonResponse({'error': 'Invalid decision'}, status=400)
        
        # Validate comments for rejection or send back
        if decision in ['rejected', 'sent_back'] and not comments.strip():
            return JsonResponse({'error': 'Comments are required for rejection or revision requests'}, status=400)
        
        # Create SMT review object
        smt_review = SMTReview(
            contract=contract,
            smt_member=request.user.employee,
            decision=decision,
            comments=comments
        )
        
        # Handle document upload
        document = request.FILES.get('smt_document')
        if document:
            smt_review.document = document.read()
            smt_review.document_name = document.name
        
        # Save the review
        smt_review.save()
        
        # Update contract status
        contract.status = decision
        contract.save()
        
        # Create notification for the employee
        notification_message = ""
        if decision == 'approved':
            notification_message = f"Your contract renewal (ID: {contract.contract_id}) has been approved by the SMT."
        elif decision == 'rejected':
            notification_message = f"Your contract renewal (ID: {contract.contract_id}) has been rejected by the SMT. Reason: {comments}"
        else:  # sent_back
            notification_message = f"Your contract renewal (ID: {contract.contract_id}) has been sent back for revision by the SMT. Comments: {comments}"
        
        # Add document info to notification if a document was uploaded
        if document:
            notification_message += f" A document has been attached to this decision."
        
        ContractNotification.objects.create(
            employee=contract.employee,
            message=notification_message,
            contract=contract,
            metadata={
                'smt_decision': decision,
                'smt_comments': comments,
                'decided_by': request.user.id,
                'has_document': bool(document)
            }
        )
        
        # Create notification for HR
        try:
            hr_group = Group.objects.get(name='HR')
            hr_users = hr_group.user_set.all()
            
            for hr_user in hr_users:
                try:
                    hr_employee = Employee.objects.get(user=hr_user)
                    hr_message = f"SMT has {decision} contract {contract.contract_id} for {contract.employee.get_full_name()}."
                    
                    # Add document info to notification if a document was uploaded
                    if document:
                        hr_message += f" A document has been attached to this decision."
                    
                    ContractNotification.objects.create(
                        employee=hr_employee,
                        message=hr_message,
                        contract=contract,
                        metadata={
                            'smt_decision': decision,
                            'smt_comments': comments,
                            'decided_by': request.user.id,
                            'has_document': bool(document),
                            'smt_review_id': smt_review.id
                        }
                    )
                except Employee.DoesNotExist:
                    continue
        except Group.DoesNotExist:
            pass
        
        return JsonResponse({'status': 'success'})
    except Contract.DoesNotExist:
        return JsonResponse({'error': 'Contract not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
class SMTContractsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'contract/smt_contracts.html'
    context_object_name = 'contracts'
    
    def test_func(self):
        # Check if user is in SMT group
        return self.request.user.groups.filter(name='SMT').exists()
    
    def get_queryset(self):
        filter_param = self.request.GET.get('filter')
        
        if filter_param == 'approved':
            # Show approved contracts
            return Contract.objects.filter(status='approved').order_by('-submission_date')
        elif filter_param == 'rejected':
            # Show rejected contracts
            return Contract.objects.filter(status='rejected').order_by('-submission_date')
        else:
            # Show contracts awaiting SMT review
            return Contract.objects.filter(status='smt_review').order_by('-submission_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter')
        context['departments'] = Department.objects.all()
        
        # Calculate months remaining for each contract
        today = timezone.now().date()
        for contract in context['contracts']:
            # Calculate based on employee hire date + 3 years
            renewal_date = contract.employee.hire_date + relativedelta(years=3)
            while renewal_date < today:
                renewal_date += relativedelta(years=3)
            
            r_date = datetime(renewal_date.year, renewal_date.month, 1)
            t_date = datetime(today.year, today.month, 1)
            
            contract.months_remaining = ((r_date.year - t_date.year) * 12 + 
                                      r_date.month - t_date.month)
                
        return context