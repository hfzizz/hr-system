from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, ListView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, FileResponse, HttpResponseNotFound, HttpResponseRedirect
from django.core.cache import cache
from .models import Contract, AdministrativePosition, DeanReview, SMTReview, MOEReview, PeerReview
from .forms import ContractRenewalForm, ContractForm
from appraisals.models import Appraisal, Module, AppraisalPublication
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
import logging
from django.urls import NoReverseMatch
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import KeepTogether
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from django.http import FileResponse
from django.conf import settings
import tempfile
import os
from PIL import Image
from zipfile import ZipFile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
import difflib
from appraisals.models import CompletedResearch, OngoingResearch


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
                if employee.appointment_type == 'Contract':
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
                
            # --- Auto-populate academic qualifications for new contract ---
            # Only if not editing an existing contract (i.e., not a draft or previous_contract)
            if not self.request.GET.get('edit') and not previous_contract:
                employee = self.request.user.employee
                qualifications = employee.get_qualifications().order_by('-from_date')
                qual_list = []
                for qual in qualifications:
                    qual_list.append({
                        'degree_diploma': qual.degree_diploma,
                        'university_college': qual.university_college,
                        'from_date': qual.from_date.strftime('%Y-%m-%d'),
                        'to_date': qual.to_date.strftime('%Y-%m-%d'),
                    })
                import json
                context['academic_qualifications_text'] = json.dumps(qual_list)
                
                # --- Auto-populate teaching modules for new contract ---
                modules = Module.objects.filter(employee=employee).order_by('code')
                modules_list = []
                for module in modules:
                    modules_list.append({
                        'title': module.title,
                        'level': module.level,
                        'languageMedium': module.languageMedium,
                        'no_of_students': module.no_of_students,
                        'percentage_jointly_taught': module.percentage_jointly_taught,
                        'hrs_weekly': module.hrs_weekly,
                    })
                context['teaching_modules_text'] = json.dumps(modules_list)
                
                # --- Auto-populate publications from completed appraisals ---
                # Get all completed appraisals for this employee
                
                # First check all appraisals regardless of status
                all_appraisals = Appraisal.objects.filter(employee=employee)
                
                # Now get only completed appraisals - order by date_created (oldest first)
                completed_appraisals = Appraisal.objects.filter(
                    employee=employee,
                    status='completed'
                ).order_by('date_created')  # Changed from '-date_created' to 'date_created' for oldest first
                
                # Get all publications from these appraisals
                publications = []
                if completed_appraisals.exists():
                    # Get unique publications from all completed appraisals
                    appraisal_publications = AppraisalPublication.objects.filter(
                        appraisal__in=completed_appraisals
                    ).order_by('year')  # Changed from '-year' to 'year' for oldest first
                    
                    # Format publications as text entries
                    for pub in appraisal_publications:
                        publications.append(f"{pub.title} ({pub.year})")
                
                # Check if there are publications directly in the Appraisal model
                all_publications_texts = []
                
                for appraisal in completed_appraisals:
                    if appraisal.publications:
                        all_publications_texts.append(appraisal.publications)
                
                # Combine all sources of publications
                if publications:
                    # If we have AppraisalPublication entries, use those
                    context['publications_text'] = '\n\n'.join(publications)
                elif all_publications_texts:
                    # Otherwise, use publications from Appraisal.publications field
                    context['publications_text'] = '\n\n'.join(all_publications_texts)
                else:
                    # If no publications found, check the Publication model as a last resort
                    from employees.models import Publication
                    employee_publications = Publication.objects.filter(employee=employee)
                    
                    if employee_publications.exists():
                        direct_publications = []
                        for pub in employee_publications:
                            pub_year = pub.year if pub.year else "N/A"
                            direct_publications.append(f"{pub.title} ({pub_year})")
                        
                        context['publications_text'] = '\n\n'.join(direct_publications)
                    else:
                        context['publications_text'] = ""
                
                # --- Auto-populate data from the 3 latest appraisals ---
                latest_appraisals = Appraisal.objects.filter(
                    employee=employee,
                    status='completed'  # Only use completed appraisals
                ).order_by('-date_created')[:3]
                
                # 1. Conference Attendance
                conference_attendance = []
                for appraisal in latest_appraisals:
                    attendance_entries = appraisal.conference_attendances.all()
                    for entry in attendance_entries:
                        conference_attendance.append({
                            'event_name': entry.event_name,
                            'type': entry.type,
                            'date': entry.date.isoformat() if entry.date else '',
                            'location': entry.location or '',
                            'role': entry.role or '',
                            'details': entry.details or ''
                        })
                context['conference_attendance_data'] = json.dumps(conference_attendance)
                
                # 2. Administrative Positions
                administrative_positions = []
                for appraisal in latest_appraisals:
                    admin_posts = appraisal.admin_post_entries.all()
                    for post in admin_posts:
                        administrative_positions.append({
                            'title': post.position,
                            'from_date': post.from_date.isoformat() if post.from_date else '',
                            'to_date': post.to_date.isoformat() if post.to_date else '',
                            'details': post.details or ''
                        })
                context['administrative_positions_data'] = json.dumps(administrative_positions)
                
                # 3. University Committees
                university_committees = []
                for appraisal in latest_appraisals:
                    committees = appraisal.university_committee_memberships.all()
                    for committee in committees:
                        university_committees.append({
                            'committee_name': committee.committee_name,
                            'position': committee.position,
                            'from_date': committee.from_date.isoformat() if committee.from_date else '',
                            'to_date': committee.to_date.isoformat() if committee.to_date else '',
                            'details': committee.details or ''
                        })
                context['university_committees_data'] = json.dumps(university_committees)
                
                # 4. External Committees
                external_committees = []
                for appraisal in latest_appraisals:
                    committees = appraisal.outside_committee_memberships.all()
                    for committee in committees:
                        external_committees.append({
                            'organization': committee.organization,
                            'position': committee.position,
                            'from_date': committee.from_date.isoformat() if committee.from_date else '',
                            'to_date': committee.to_date.isoformat() if committee.to_date else '',
                            'details': committee.details or ''
                        })
                context['external_committees_data'] = json.dumps(external_committees)
                
                # 5. Consultancy Work
                consultancy_work = []
                for appraisal in latest_appraisals:
                    consultancy_entries = appraisal.consultancy_works.all()
                    for entry in consultancy_entries:
                        consultancy_work.append({
                            'title': entry.title,
                            'company_institute': entry.company_institute,
                            'start_date': entry.start_date.isoformat() if entry.start_date else '',
                            'end_date': entry.end_date.isoformat() if entry.end_date else ''
                        })
                context['consultancy_work_data'] = json.dumps(consultancy_work)
                
                # 6. Conference Papers
                conference_papers = []
                for appraisal in latest_appraisals:
                    paper_entries = appraisal.conference_paper_entries.all()
                    for paper in paper_entries:
                        conference_papers.append({
                            'author': paper.author,
                            'year': paper.year,
                            'title': paper.title,
                            'volume': paper.volume or '',
                            'pages': paper.pages or '',
                            'doi': paper.doi or ''
                        })
                context['conference_papers_data'] = json.dumps(conference_papers)
                
                # 7. Participation Within University
                participation_within = []
                for appraisal in latest_appraisals:
                    activities = appraisal.within_university_activities.all()
                    for activity in activities:
                        participation_within.append({
                            'activity': activity.activity,
                            'role': activity.role,
                            'date': activity.date.isoformat() if activity.date else '',
                            'remarks': activity.remarks or ''
                        })
                context['participation_within_data'] = json.dumps(participation_within)
                
                # 8. Participation Outside University
                participation_outside = []
                for appraisal in latest_appraisals:
                    activities = appraisal.outside_university_activities.all()
                    for activity in activities:
                        participation_outside.append({
                            'activity': activity.activity,
                            'role': activity.role,
                            'date': activity.date.isoformat() if activity.date else '',
                            'remarks': activity.remarks or ''
                        })
                context['participation_outside_data'] = json.dumps(participation_outside)
        
        # Add contract type choices
        context['contract_type_choices'] = Contract.CONTRACT_TYPE_CHOICES
        
        # --- Auto-populate completed and ongoing research from latest 3 appraisals ---
        # Only for new contract forms (not editing/drafts)
        latest_appraisals = Appraisal.objects.filter(
            employee=employee,
            status='completed'
        ).order_by('-date_created')[:3]

        research_entries = []  # List of (title, status, entry_dict, appraisal_date)
        for appraisal in latest_appraisals:
            # Completed research
            for entry in appraisal.completed_researches.all():
                research_entries.append((entry.title.strip(), 'completed', {
                    'title': entry.title,
                    'startDate': entry.start_date.isoformat() if entry.start_date else '',
                    'endDate': entry.end_date.isoformat() if entry.end_date else '',
                    'fundingAgency': entry.funding_agency or '',
                    'grants': entry.grants or ''
                }, appraisal.date_created))
            # Ongoing research
            for entry in appraisal.ongoing_researches.all():
                research_entries.append((entry.title.strip(), 'ongoing', {
                    'title': entry.title,
                    'startDate': entry.start_date.isoformat() if entry.start_date else '',
                    'endDate': entry.end_date.isoformat() if entry.end_date else '',
                    'fundingAgency': entry.funding_agency or '',
                    'grants': entry.grants or ''
                }, appraisal.date_created))

        # Fuzzy group by title, preferring 'completed' if both exist
        grouped = []  # List of dicts
        used = set()
        threshold = 0.85
        for i, (title, status, entry_dict, date) in enumerate(research_entries):
            if i in used:
                continue
            # Find all similar titles
            group = [(i, title, status, entry_dict, date)]
            for j in range(i+1, len(research_entries)):
                if j in used:
                    continue
                other_title, other_status, other_entry, other_date = research_entries[j][0], research_entries[j][1], research_entries[j][2], research_entries[j][3]
                ratio = difflib.SequenceMatcher(None, title.lower(), other_title.lower()).ratio()
                if ratio >= threshold:
                    group.append((j, other_title, other_status, other_entry, other_date))
                    used.add(j)
            # From the group, prefer the most recent 'completed', else most recent 'ongoing'
            group.sort(key=lambda x: (x[2] == 'completed', x[4]), reverse=True)
            grouped.append(group[0][3])
            used.add(i)
        # Separate into completed and ongoing
        completed_research = []
        ongoing_research = []
        for entry in grouped:
            # Find the original status in research_entries
            for t, s, e, d in research_entries:
                if e == entry:
                    if s == 'completed':
                        completed_research.append(entry)
                    else:
                        ongoing_research.append(entry)
                    break
        context['completed_research_data'] = json.dumps(completed_research)
        context['ongoing_research_data'] = json.dumps(ongoing_research)
        
        return context


    def form_valid(self, form):
        is_draft = self.request.POST.get('is_draft') == 'true'
        form.instance.employee = self.request.user.employee
        if is_draft:
            existing_draft = Contract.objects.filter(employee=self.request.user.employee, status='draft').first()
            if existing_draft:
                # Update the existing draft instead of creating a new one
                for field in form.Meta.fields:
                    if field not in ['id', 'pk', 'employee', 'submission_date', 'status']:
                        setattr(existing_draft, field, getattr(form.instance, field))
                existing_draft.is_draft = True
                existing_draft.draft_saved_at = timezone.now()
                existing_draft.draft_saved_by = self.request.user.employee
                existing_draft.status = 'draft'
                form.instance = existing_draft  # Use the updated draft for the rest of the method
            else:
                form.instance.is_draft = True
                form.instance.draft_saved_at = timezone.now()
                form.instance.draft_saved_by = self.request.user.employee
                form.instance.status = 'draft'
        else:
            form.instance.is_draft = False
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

        # Handle publications (now as text)
        publications = self.request.POST.get('publications')
        form.instance.publications = publications if publications else ''

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
        administrative_positions_data = self.request.POST.get('administrative_positions_text')
        form.instance.administrative_positions_text = '[]'  # Default to empty list
        if administrative_positions_data:
            try:
                positions = json.loads(administrative_positions_data)
                for position in positions:
                    # Debug log
                    print(f"Debug - Administrative position data: {position}")
                    
                    # Get the date values
                    from_date = position.get('from_date', None) or position.get('fromDate', None)
                    to_date = position.get('to_date', None) or position.get('toDate', None)
                    
                    # Skip creating records with missing from_date
                    if not from_date:
                        print(f"Warning - Skipping administrative position due to missing from_date: {position}")
                        continue
                        
                    # Create and save each administrative position
                    AdministrativePosition.objects.create(
                        contract=form.instance,
                        title=position.get('position', ''),
                        from_date=from_date,
                        to_date=to_date or from_date,  # Use from_date as fallback if to_date is missing
                        details=position.get('details', '')
                    )
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error processing administrative positions: {str(e)}")
        
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
        
        # Handle fellowships and awards data
        fellowships_awards_data = self.request.POST.get('fellowships_awards_text')
        if fellowships_awards_data:
            try:
                fellowships_json = json.loads(fellowships_awards_data)
                form.instance.fellowships_awards_text = fellowships_awards_data
            except json.JSONDecodeError:
                form.instance.fellowships_awards_text = '[]'
        else:
            form.instance.fellowships_awards_text = '[]'
        
        response = super().form_valid(form)

        # Only notify HR if not saving as draft
        if not is_draft:
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
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': '/contract/employee-contracts/'
            })
        return response

    def get(self, request, *args, **kwargs):
        # If a draft exists for this user, load it for editing
        draft = Contract.objects.filter(employee=request.user.employee, is_draft=True).first()
        if draft:
            return redirect('contract:edit_submission', pk=draft.pk)
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

    def form_invalid(self, form):
        return super().form_invalid(form)

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

        contract_count = Contract.objects.filter(employee=employee).count() + 1

        return JsonResponse({
            'success': True,
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
            appointment_type='Contract'
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
        
        # Parse mentorship data
        try:
            mentorship_data = json.loads(contract.mentorship_text) if contract.mentorship_text else []
        except json.JSONDecodeError:
            mentorship_data = []
            print("Error parsing mentorship data")
            
        # Parse graduate supervision data
        try:
            grad_supervision_data = json.loads(contract.grad_supervision_text) if contract.grad_supervision_text else []
        except json.JSONDecodeError:
            grad_supervision_data = []
            print("Error parsing graduate supervision data")
        
        # Add committee data to context
        context['university_committees'] = university_committees
        context['external_committees'] = external_committees
        
        # Add mentorship and graduate supervision data to context
        context['mentorship_data'] = mentorship_data
        context['grad_supervision_data'] = grad_supervision_data
        
        # Get peer reviews
        peer_reviews = PeerReview.objects.filter(contract=contract).order_by('-created_at')
        context['peer_reviews'] = peer_reviews
        
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

        # Parse fellowships and awards data
        fellowships_awards = []
        if contract.fellowships_awards_text:
            try:
                fellowships_awards = json.loads(contract.fellowships_awards_text)
            except json.JSONDecodeError:
                fellowships_awards = []
                
        context['fellowships_awards'] = fellowships_awards

        # Add SMT approved flag for template logic
        context['smt_approved'] = contract.smt_reviews.filter(decision='smt_approved').exists()

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
        newly_enabled = []
        
        for employee_id in employee_ids:
            status, created = ContractRenewalStatus.objects.get_or_create(
                employee_id=employee_id
            )
            was_enabled = status.is_enabled
            status.is_enabled = (action == 'enable')
            status.save()
            # Only add if we are enabling and it was not enabled before
            if action == 'enable' and not was_enabled:
                newly_enabled.append(employee_id)
        
        return JsonResponse({'status': 'success', 'newly_enabled': newly_enabled})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def send_notification(request):
    if not request.user.groups.filter(name='HR').exists():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        employee_ids = data.get('employee_ids', [])
        if not employee_ids:
            return JsonResponse({'status': 'info', 'message': 'No employees specified for notification'})
        notifications_sent = 0

        employees = Employee.objects.filter(id__in=employee_ids)
        today = timezone.now().date()
        
        for employee in employees:
            # Calculate next renewal date
            renewal_date = employee.hire_date + relativedelta(years=3)
            while renewal_date < today:
                renewal_date += relativedelta(years=3)
            months_remaining = ((renewal_date.year - today.year) * 12 + renewal_date.month - today.month)
            submission_url = '/contract/form/'
            message = (
                f"Your contract renewal is due on {renewal_date.strftime('%B %d, %Y')}. "
                f"You have {months_remaining} months remaining. "
                "Please submit your contract renewal application. Use the link below:<br/>"
                f'<a href="{submission_url}" class="text-blue-600 hover:underline">Click here to submit</a>'
            )
            ContractNotification.objects.create(
                employee=employee,
                message=message
            )
            notifications_sent += 1
        # Move the return statement here, after the loop
            return JsonResponse({
                'status': 'success',
                'message': f'Notifications sent to {notifications_sent} employees'
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
                    # Create notification with just the message, no link
                    message = f"HR has forwarded contract {contract.contract_id} for {contract.employee.get_full_name()} for SMT review."
                    
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
        
        return JsonResponse({'status': 'success', 'redirect_url': reverse('contract:view_all_submissions')})
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
            return redirect('contract:view_all_submissions')
        
        today = datetime.now().date()
        filter_param = request.GET.get('filter')
        
        # For SMT users with specific filters
        if request.user.groups.filter(name='SMT').exists():
            if filter_param == 'smt_approved':
                in_process_contracts = Contract.objects.filter(
                    status='smt_approved'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
                moe_decision_contracts = Contract.objects.none()
            elif filter_param == 'smt_rejected':
                in_process_contracts = Contract.objects.filter(
                    status='smt_rejected'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
                moe_decision_contracts = Contract.objects.none()
            else:
                # Default view for SMT - show contracts waiting for review
                in_process_contracts = Contract.objects.filter(
                    status='smt_review'
                ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
                pending_contracts = Contract.objects.none()
                moe_decision_contracts = Contract.objects.none()
        elif request.user.groups.filter(name='HR').exists():
            # For HR users, show all contracts
            in_process_contracts = Contract.objects.filter(
                status__in=['smt_review', 'smt_approved', 'smt_rejected', 'sent_back', 'dean_review']
            ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]

            pending_contracts = Contract.objects.filter(
                status='pending'
            ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
            
            # Add MOE decision contracts
            moe_decision_contracts = Contract.objects.filter(
                status__in=['moe_approved', 'moe_rejected']
            ).select_related('employee', 'employee__department').order_by('-submission_date')[:100]
        else:
            # For other users
            in_process_contracts = Contract.objects.none()
            pending_contracts = Contract.objects.none()
            moe_decision_contracts = Contract.objects.none()
        
        # Pre-calculate months_remaining to avoid doing it in the template
        for contracts in [in_process_contracts, pending_contracts, moe_decision_contracts]:
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
            'moe_decision_contracts': moe_decision_contracts,
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
            status__in=['smt_approved', 'smt_rejected', 'moe_approved', 'moe_rejected']
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
            'ic_colour_display': IC_COLOURS.get(employee.ic_colour, employee.ic_colour),
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'contract_count': Contract.objects.filter(
                employee=self.object.employee,
                submission_date__lt=self.object.submission_date
            ).count() + 1,
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
            
        # Add research and consultancy data
        try:
            context['consultancy_work'] = json.loads(self.object.consultancy_work or '[]')
        except json.JSONDecodeError:
            context['consultancy_work'] = []
            
        try:
            context['research_history'] = json.loads(self.object.last_research or '[]')
        except json.JSONDecodeError:
            context['research_history'] = []
            
        try:
            context['ongoing_research'] = json.loads(self.object.ongoing_research or '[]')
        except json.JSONDecodeError:
            context['ongoing_research'] = []
            
        try:
            context['conference_papers'] = json.loads(self.object.conference_papers or '[]')
        except json.JSONDecodeError:
            context['conference_papers'] = []
            
        # Parse fellowships and awards data
        fellowships_awards = []
        if self.object.fellowships_awards_text:
            try:
                fellowships_awards = json.loads(self.object.fellowships_awards_text)
            except json.JSONDecodeError:
                fellowships_awards = []

        context['fellowships_awards'] = fellowships_awards

        # Get administrative positions from related model
        context['administrative_positions'] = self.object.administrative_positions.all()
            
        try:
            context['attendance_events'] = json.loads(self.object.attendance or '[]')
        except json.JSONDecodeError:
            context['attendance_events'] = []
            
        try:
            context['university_committees'] = json.loads(self.object.university_committees_text or '[]')
        except json.JSONDecodeError:
            context['university_committees'] = []
            
        try:
            context['external_committees'] = json.loads(self.object.external_committees_text or '[]')
        except json.JSONDecodeError:
            context['external_committees'] = []
        
        # Get dean reviews
        context['dean_reviews'] = DeanReview.objects.filter(contract=self.object).order_by('-created_at')
        
        # Get SMT reviews
        context['smt_reviews'] = SMTReview.objects.filter(contract=self.object).order_by('-created_at')
        
        # Get peer reviews
        context['peer_reviews'] = PeerReview.objects.filter(contract=self.object).order_by('-created_at')
        
        # Parse mentorship data
        try:
            context['mentorship_data'] = json.loads(self.object.mentorship_text) if self.object.mentorship_text else []
        except json.JSONDecodeError:
            context['mentorship_data'] = []
            print("Error parsing mentorship data")
            
        # Parse graduate supervision data
        try:
            context['grad_supervision_data'] = json.loads(self.object.grad_supervision_text) if self.object.grad_supervision_text else []
        except json.JSONDecodeError:
            context['grad_supervision_data'] = []
            print("Error parsing graduate supervision data")
        
        # Get all appraisals for this employee
        from appraisals.models import Appraisal
        appraisals = Appraisal.objects.filter(
            employee=self.object.employee
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
    
    # Parse fellowships and awards data
    fellowships_awards = []
    if contract.fellowships_awards_text:
        try:
            fellowships_awards = json.loads(contract.fellowships_awards_text)
        except json.JSONDecodeError:
            fellowships_awards = []
    else:
        fellowships_awards = []
    
    context = {
        'contract': contract,
        'teaching_modules': teaching_modules,
        'university_committees': university_committees,
        'external_committees': external_committees,
        'consultancy_work': consultancy_work,
        'research_history': research_history,
        'ongoing_research': ongoing_research,
        'conference_papers': conference_papers,
        'fellowships_awards': fellowships_awards,
        # Publications are now handled as text, no parsing needed
        'publications': contract.publications,
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
            status__in=['sent_back', 'draft']
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
        
        # Add contract table data to context
        contract = self.get_object()
        
        # Define employee variable here to fix the UnboundLocalError
        employee = contract.employee
        
        # Get administrative positions and convert to JSON
        admin_positions = contract.administrative_positions.all().values('title', 'from_date', 'to_date', 'details')
        admin_positions_list = list(admin_positions)
        # Convert dates to string format for JSON serialization
        for position in admin_positions_list:
            if position['from_date']:
                position['from_date'] = position['from_date'].strftime('%Y-%m-%d')
            if position['to_date']:
                position['to_date'] = position['to_date'].strftime('%Y-%m-%d')
            # Map title to position for consistency with the form
            position['position'] = position['title']
    
        # Make sure JSON fields are handled correctly
        # Handle JSON fields that might already be strings or might be objects
        def ensure_json_string(field_value):
            if field_value is None:
                return '[]'
            if isinstance(field_value, str):
                try:
                    # Try to parse and then re-stringify to ensure valid JSON
                    json.loads(field_value)
                    return field_value  # Already a valid JSON string
                except json.JSONDecodeError:
                    return '[]'  # Invalid JSON, return empty array
            else:
                # If it's an object (dict, list), convert to JSON string
                return json.dumps(field_value)
            
        # Make sure all JSON fields are properly serialized as strings
        contract_data = {
            'academic_qualifications_text': contract.academic_qualifications_text,
            'teaching_modules_text': contract.teaching_modules_text,
            'attendance': contract.attendance,
            'administrative_positions_text': json.dumps(admin_positions_list),
            'university_committees_text': contract.university_committees_text,
            'external_committees_text': contract.external_committees_text,
            'participation_within_text': contract.participation_within_text,
            'participation_outside_text': contract.participation_outside_text,
            'fellowships_awards_text': ensure_json_string(contract.fellowships_awards_text),
            'mentorship_text': ensure_json_string(contract.mentorship_text),
            'grad_supervision_text': ensure_json_string(contract.grad_supervision_text),
            'last_research': ensure_json_string(contract.last_research),
            'ongoing_research': ensure_json_string(contract.ongoing_research),
            'consultancy_work': ensure_json_string(contract.consultancy_work),
            'conference_papers': ensure_json_string(contract.conference_papers),
        }
        
        # Add debug data to context
        context['debug_data'] = {
            'last_research': contract.last_research,
            'ongoing_research': contract.ongoing_research,
            'consultancy_work': contract.consultancy_work,
            'conference_papers': contract.conference_papers,
        }
        
        context['contract_data_json'] = json.dumps(contract_data)
        
        # Parse academic qualifications data
        if contract.academic_qualifications_text:
            context['academic_qualifications_text'] = ensure_json_string(contract.academic_qualifications_text)
        
        # Parse teaching modules data
        if contract.teaching_modules_text:
            context['teaching_modules_text'] = ensure_json_string(contract.teaching_modules_text)
        
        # Publications are now handled as text, no parsing needed
        if contract.publications:
            context['publications_text'] = contract.publications
        else:
            # If no publications in contract, try to get them from appraisals
            # employee is already defined above
            completed_appraisals = Appraisal.objects.filter(
                employee=employee,
                status='completed'
            ).order_by('date_created')  # Changed from '-date_created' to 'date_created' for oldest first
            
            # Check if there are publications directly in the Appraisal model
            all_publications_texts = []
            for appraisal in completed_appraisals:
                if appraisal.publications:
                    all_publications_texts.append(appraisal.publications)
            
            if all_publications_texts:
                context['publications_text'] = '\n\n'.join(all_publications_texts)
        
        # --- Auto-populate data from the 3 latest appraisals ---
        latest_appraisals = Appraisal.objects.filter(
            employee=employee,
            status='completed'  # Only use completed appraisals
        ).order_by('-date_created')[:3]
        
        # 1. Conference Attendance
        conference_attendance = []
        for appraisal in latest_appraisals:
            attendance_entries = appraisal.conference_attendances.all()
            for entry in attendance_entries:
                conference_attendance.append({
                    'event_name': entry.event_name,
                    'type': entry.type,
                    'date': entry.date.isoformat() if entry.date else '',
                    'location': entry.location or '',
                    'role': entry.role or '',
                    'details': entry.details or ''
                })
        context['conference_attendance_data'] = json.dumps(conference_attendance)
        
        # 2. Administrative Positions
        administrative_positions = []
        for appraisal in latest_appraisals:
            admin_posts = appraisal.admin_post_entries.all()
            for post in admin_posts:
                administrative_positions.append({
                    'title': post.position,
                    'from_date': post.from_date.isoformat() if post.from_date else '',
                    'to_date': post.to_date.isoformat() if post.to_date else '',
                    'details': post.details or ''
                })
        context['administrative_positions_data'] = json.dumps(administrative_positions)
        
        # 3. University Committees
        university_committees = []
        for appraisal in latest_appraisals:
            committees = appraisal.university_committee_memberships.all()
            for committee in committees:
                university_committees.append({
                    'committee_name': committee.committee_name,
                    'position': committee.position,
                    'from_date': committee.from_date.isoformat() if committee.from_date else '',
                    'to_date': committee.to_date.isoformat() if committee.to_date else '',
                    'details': committee.details or ''
                })
        context['university_committees_data'] = json.dumps(university_committees)
        
        # 4. External Committees
        external_committees = []
        for appraisal in latest_appraisals:
            committees = appraisal.outside_committee_memberships.all()
            for committee in committees:
                external_committees.append({
                    'organization': committee.organization,
                    'position': committee.position,
                    'from_date': committee.from_date.isoformat() if committee.from_date else '',
                    'to_date': committee.to_date.isoformat() if committee.to_date else '',
                    'details': committee.details or ''
                })
        context['external_committees_data'] = json.dumps(external_committees)
        
        return context
    
    def form_valid(self, form):
        form.instance.employee = self.request.user.employee
        is_draft = self.request.POST.get('is_draft') == 'true'
        if is_draft:
            form.instance.status = 'draft'
            form.instance.is_draft = True
            form.instance.draft_saved_at = timezone.now()
            form.instance.draft_saved_by = self.request.user.employee
        else:
            form.instance.status = 'pending'
            form.instance.is_draft = False
        
        # Handle publications (now as text)
        publications = self.request.POST.get('publications')
        form.instance.publications = publications if publications else ''

        # Handle consultancy work
        consultancy_data = self.request.POST.get('consultancy_work')
        
        if consultancy_data:
            try:
                consultancy_json = json.loads(consultancy_data)
                # Add field validation here to ensure the structure is correct
                form.instance.consultancy_work = consultancy_data
            except json.JSONDecodeError:
                print("DEBUG - JSON decode error for consultancy_work")
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
                    from_date = position.get('fromDate') or position.get('from_date')
                    to_date = position.get('toDate') or position.get('to_date')
                    position_title = position.get('position') or position.get('title', '')
                    
                    AdministrativePosition.objects.create(
                        contract=self.object,
                        title=position_title,
                        from_date=from_date,
                        to_date=to_date,
                        details=position.get('details', '')
                    )
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error processing administrative positions: {str(e)}")
        
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
        
        # Handle fellowships and awards data
        fellowships_awards_data = self.request.POST.get('fellowships_awards_text')
        if fellowships_awards_data:
            try:
                fellowships_json = json.loads(fellowships_awards_data)
                self.object.fellowships_awards_text = fellowships_awards_data
            except json.JSONDecodeError:
                self.object.fellowships_awards_text = '[]'
        else:
            self.object.fellowships_awards_text = '[]'
        
        # Save the object again with all the updated fields
        self.object.save()
        
        # Only notify HR if not saving as draft
        if not is_draft:
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
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': '/contract/employee-contracts/'
            })
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
            
            # Get all department contracts regardless of status
            all_department_contracts = Contract.objects.filter(
                employee__department=dean_department
            ).select_related('employee', 'employee__department').order_by('-submission_date')
            
            # Calculate months remaining for each contract
            today = datetime.now().date()
            for contracts in [dean_review_contracts, all_department_contracts]:
                for contract in contracts:
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
                'all_department_contracts': all_department_contracts,
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
        
        # Fetch administrative positions
        administrative_positions = contract.administrative_positions.all()
        
        # Parse academic qualifications
        try:
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
        
        # Parse mentorship data
        try:
            mentorship_data = json.loads(contract.mentorship_text) if contract.mentorship_text else []
        except json.JSONDecodeError:
            mentorship_data = []
            print("Error parsing mentorship data")
            
        # Parse graduate supervision data
        try:
            grad_supervision_data = json.loads(contract.grad_supervision_text) if contract.grad_supervision_text else []
        except json.JSONDecodeError:
            grad_supervision_data = []
            print("Error parsing graduate supervision data")
        
        # Get peer reviews
        peer_reviews = PeerReview.objects.filter(contract=contract).order_by('-created_at')
        
        # IC Color mapping
        IC_COLOURS = {
            'Y': 'Yellow',
            'P': 'Purple',
            'G': 'Green',
            'R': 'Red'
        }
        
        # Prepare context data similar to the review view
        context = {
            'contract': contract,
            'first_name': contract.employee.first_name,
            'last_name': contract.employee.last_name,
            'ic_no': contract.employee.ic_no,
            'ic_colour': IC_COLOURS.get(contract.employee.ic_colour, contract.employee.ic_colour),
            'phone_number': contract.employee.phone_number,
            'department': contract.employee.department.name if contract.employee.department else '',
            'dean_review': dean_review,
            'previous_dean_reviews': previous_dean_reviews,
            'academic_qualifications': academic_quals,
            'teaching_modules': teaching_modules,
            'administrative_positions': administrative_positions,
            'participation_within': participation_within,
            'participation_outside': participation_outside,
            'university_committees': university_committees,
            'external_committees': external_committees,
            'mentorship_data': mentorship_data,
            'grad_supervision_data': grad_supervision_data,
            'peer_reviews': peer_reviews,
            'teaching_future_plan': contract.teaching_future_plan,
            'is_review': True,
        }
        
        # Add contract_count to the context
        contract_count = Contract.objects.filter(
            employee=contract.employee,
            submission_date__lt=contract.submission_date
        ).count() + 1
        context['contract_count'] = contract_count
        
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
        
        # Parse fellowships and awards data
        try:
            context['fellowships_awards'] = json.loads(contract.fellowships_awards_text) if contract.fellowships_awards_text else []
        except json.JSONDecodeError:
            context['fellowships_awards'] = []
        
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
        
        # Get peer reviews
        peer_reviews = PeerReview.objects.filter(contract=contract).order_by('-created_at')
        context['peer_reviews'] = peer_reviews
        
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
        if decision not in ['smt_approved', 'smt_rejected', 'sent_back']:
            return JsonResponse({'error': 'Invalid decision'}, status=400)
        
        # Validate comments for rejection or send back
        if decision in ['smt_rejected', 'sent_back'] and not comments.strip():
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
        
        # Update contract status - if approved, set back to pending for HR to print contract
        if decision == 'smt_approved':
            contract.status = 'pending'
        else:
            contract.status = decision
        contract.save()
        
        # Create notification for the employee
        notification_message = ""
        if decision == 'smt_rejected':
            notification_message = f"Your contract renewal {contract.contract_id} has been rejected by the SMT. Reason: {comments}"
        elif decision == 'sent_back':
            notification_message = f"Your contract renewal {contract.contract_id} has been sent back for revision by the SMT. Comments: {comments}"
        
        # Add document info to notification if a document was uploaded
        if document and decision != 'smt_approved':
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
            
            # Map decision codes to human-readable text
            decision_text = {
                'smt_approved': 'approved',
                'smt_rejected': 'rejected',
                'sent_back': 'sent back'
            }.get(decision, decision)  # Fallback to the original value if not found
            
            for hr_user in hr_users:
                try:
                    hr_employee = Employee.objects.get(user=hr_user)
                    hr_message = f"SMT has {decision_text} contract {contract.contract_id} for {contract.employee.get_full_name()}."
                    
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
        
        return redirect('contract:smt_contracts')
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
        # Get all contracts
        contracts = Contract.objects.all().order_by('-submission_date')
        
        # Add flags to indicate SMT review status
        for contract in contracts:
            # Check if this contract has been reviewed by SMT
            smt_reviews = contract.smt_reviews.all()
            contract.has_smt_review = smt_reviews.exists()
            
            # If it has reviews, get the latest decision
            if contract.has_smt_review:
                latest_review = smt_reviews.latest('created_at')
                contract.smt_decision = latest_review.decision
                contract.is_smt_approved = latest_review.decision == 'smt_approved'
                contract.is_smt_rejected = latest_review.decision == 'smt_rejected'
                contract.is_sent_back = latest_review.decision == 'sent_back'
                contract.smt_review_date = latest_review.created_at
                contract.smt_reviewer = latest_review.smt_member
            else:
                contract.smt_decision = None
                contract.is_smt_approved = False
                contract.is_smt_rejected = False
                contract.is_sent_back = False
        
        return contracts
    
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

@login_required
def preview_dean_document(request, contract_id, review_id):
    """View function to preview a dean document in the browser."""
    # Get the review object
    contract = get_object_or_404(Contract, pk=contract_id)
    review = get_object_or_404(DeanReview, pk=review_id, contract=contract)
    
    # Security check
    if not (request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponse("Permission denied", status=403)
    
    if not review.document:
        return HttpResponse("No document available", status=404)
    
    # Determine content type based on file extension
    filename = review.document_name
    content_type = 'application/octet-stream'  # Default
    
    if filename.lower().endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.lower().endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.lower().endswith('.doc'):
        content_type = 'application/msword'
    elif filename.lower().endswith(('.xls', '.xlsx')):
        content_type = 'application/vnd.ms-excel'
    elif filename.lower().endswith(('.ppt', '.pptx')):
        content_type = 'application/vnd.ms-powerpoint'
    
    # Create the response
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def print_contract_form(request, contract_id):
    # Check if user is HR
    if not request.user.groups.filter(name='HR').exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    try:
        # Get the contract
        contract = Contract.objects.get(id=contract_id)
        employee = contract.employee # Get employee from contract
        
        # Check if contract has been approved by SMT (Keep this check)
        smt_approves = False
        if contract.smt_reviews.exists():
            latest_smt_review = contract.smt_reviews.latest('created_at')
            smt_approves = latest_smt_review.decision == 'smt_approved'
        
        if not smt_approves:
            messages.error(request, "This contract has not been approved by SMT yet and cannot be printed for MOE.")
            # Redirect back to review page might be better here
            try:
                # Attempt to redirect to the review page for context
                return redirect('contract:review', pk=contract_id) 
            except NoReverseMatch:
                 # Fallback redirect if review URL fails
                return redirect('dashboard')

        # --- Start: Copy context preparation logic from ContractReviewView ---
        
        # Fetch administrative positions
        administrative_positions = contract.administrative_positions.all()
        
        try:
            academic_quals = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
        except json.JSONDecodeError:
            academic_quals = []
            logger.error(f"Error parsing academic qualifications for contract {contract_id}")

        try:
            teaching_modules = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
        except json.JSONDecodeError:
            teaching_modules = []
            logger.error(f"Error parsing teaching modules for contract {contract_id}")

        try:
            participation_within = json.loads(contract.participation_within_text) if contract.participation_within_text else []
            participation_outside = json.loads(contract.participation_outside_text) if contract.participation_outside_text else []
        except json.JSONDecodeError:
            participation_within = []
            participation_outside = []
            logger.error(f"Error parsing participation data for contract {contract_id}")
        
        try:
            university_committees = json.loads(contract.university_committees_text) if contract.university_committees_text else []
        except json.JSONDecodeError:
            university_committees = []
            logger.error(f"Error parsing university committees for contract {contract_id}")
        
        try:
            external_committees = json.loads(contract.external_committees_text) if contract.external_committees_text else []
        except json.JSONDecodeError:
            external_committees = []
            logger.error(f"Error parsing external committees for contract {contract_id}")

        peer_reviews = PeerReview.objects.filter(contract=contract).order_by('-created_at')
        
        IC_COLOURS = {
            'Y': 'Yellow', 'P': 'Purple', 'G': 'Green', 'R': 'Red'
        }

        # Get all appraisals for this employee
        appraisals = Appraisal.objects.filter(
            employee=contract.employee
        ).order_by('-date_of_last_appraisal')
        
        appraiser_comments = []
        for appraisal in appraisals:
            if appraisal.appraiser_comments and appraisal.appraiser_comments.strip():
                comment_data = {
                    'comment': appraisal.appraiser_comments.strip(),
                    'date': appraisal.date_of_last_appraisal.strftime('%Y-%m-%d'),
                    'appraiser_name': appraisal.appraiser.get_full_name() if appraisal.appraiser else 'Unknown Appraiser'
                }
                appraiser_comments.append(comment_data)

        try:
            attendance_events = json.loads(contract.attendance) if contract.attendance else []
        except json.JSONDecodeError:
            attendance_events = []
            logger.error(f"Error parsing attendance data for contract {contract_id}")

        try:
            consultancy_work = json.loads(contract.consultancy_work) if contract.consultancy_work else []
        except json.JSONDecodeError:
            consultancy_work = []
            logger.error(f"Error parsing consultancy work for contract {contract_id}")

        try:
            research_history = json.loads(contract.last_research) if contract.last_research else []
        except json.JSONDecodeError:
            research_history = []
            logger.error(f"Error parsing research history for contract {contract_id}")

        try:
            ongoing_research = json.loads(contract.ongoing_research) if contract.ongoing_research else []
        except json.JSONDecodeError:
            ongoing_research = []
            logger.error(f"Error parsing ongoing research for contract {contract_id}")

        try:
            conference_papers = json.loads(contract.conference_papers) if contract.conference_papers else []
        except json.JSONDecodeError:
            conference_papers = []
            logger.error(f"Error parsing conference papers for contract {contract_id}")

        # --- End: Copy context preparation logic ---

        # Render the contract form template with the comprehensive context
        context = {
            'contract': contract,
            'employee': employee, # Already fetched
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'ic_no': employee.ic_no,
            'ic_colour': IC_COLOURS.get(employee.ic_colour, employee.ic_colour),
            'phone_number': employee.phone_number,
            'department': employee.department.name if employee.department else '',
            'contract_count': Contract.objects.filter(
                employee=contract.employee,
                submission_date__lt=contract.submission_date
            ).count() + 1, # Assuming +1 is correct logic from review view
            'academic_qualifications': academic_quals,
            'teaching_modules': teaching_modules,
            'participation_within': participation_within,
            'participation_outside': participation_outside,
            'university_committees': university_committees,
            'external_committees': external_committees,
            'administrative_positions': administrative_positions,
            'consultancy_work': consultancy_work,
            'research_history': research_history,
            'ongoing_research': ongoing_research,
            'conference_papers': conference_papers,
            'attendance_events': attendance_events,
            'appraiser_comments': appraiser_comments,
            'dean_reviews': contract.dean_reviews.all().order_by('created_at'), # Consistent ordering
            'peer_reviews': peer_reviews, # Already fetched
            'smt_reviews': contract.smt_reviews.all().order_by('created_at'), # Consistent ordering
            'moe_reviews': contract.moe_reviews.all().order_by('created_at'), # Add MOE reviews
            'today': timezone.now().date(),
            # Include fields directly from contract model used by review.html sections
            'teaching_future_plan': contract.teaching_future_plan,
            'achievements_last_contract': contract.achievements_last_contract,
            'achievements_proposal': contract.achievements_proposal,
            'other_matters': contract.other_matters,
            'current_enrollment': contract.current_enrollment,
             # Add teaching document info if needed by the template part being copied
            'teaching_documents_name': contract.teaching_documents_name if contract.teaching_documents else None,
        }
        
        # Add mentorship and graduate supervision data
        try:
            context['mentorship_data'] = json.loads(contract.mentorship_text) if contract.mentorship_text else []
        except json.JSONDecodeError:
            context['mentorship_data'] = []
            logger.error(f"Error parsing mentorship data for contract {contract_id}")
            
        try:
            context['grad_supervision_data'] = json.loads(contract.grad_supervision_text) if contract.grad_supervision_text else []
        except json.JSONDecodeError:
            context['grad_supervision_data'] = []
            logger.error(f"Error parsing graduate supervision data for contract {contract_id}")
        
        return render(request, 'contract/print_contract_form.html', context)
    
    except Contract.DoesNotExist:
        messages.error(request, "Contract not found.")
        return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('dashboard')

@login_required
def preview_smt_document(request, contract_id, review_id):
    """View function to preview an SMT document in the browser."""
    # Get the review object
    contract = get_object_or_404(Contract, pk=contract_id)
    review = get_object_or_404(SMTReview, pk=review_id, contract=contract)
    
    # Security check
    if not (request.user.groups.filter(name__in=['SMT', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponse("Permission denied", status=403)
    
    if not review.document:
        return HttpResponse("No document available", status=404)
    
    # Determine content type based on file extension
    filename = review.document_name or "document.pdf"
    content_type = 'application/octet-stream'  # Default
    
    # Force PDF files to use the PDF content type, which is viewable in browsers
    if filename.lower().endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.lower().endswith('.docx'):
        # Most browsers can't preview DOCX, so we'll indicate this is not previewable
        return HttpResponse("This document type cannot be previewed in the browser. Please download it instead.", status=415)
    elif filename.lower().endswith('.doc'):
        return HttpResponse("This document type cannot be previewed in the browser. Please download it instead.", status=415)
    elif filename.lower().endswith(('.xls', '.xlsx')):
        return HttpResponse("This document type cannot be previewed in the browser. Please download it instead.", status=415)
    elif filename.lower().endswith(('.ppt', '.pptx')):
        return HttpResponse("This document type cannot be previewed in the browser. Please download it instead.", status=415)
    
    # Debugging: Log the content type and filename
    print(f"Serving SMT document for preview: {filename} with content type: {content_type}")
    
    # Create the response with proper content type
    response = HttpResponse(review.document, content_type=content_type)
    
    # Add Content-Disposition header for inline viewing
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    # Add headers to help with PDF viewing in browsers
    if content_type == 'application/pdf':
        response['X-Content-Type-Options'] = 'nosniff'
        response['Accept-Ranges'] = 'bytes'
    
    return response

@login_required
@require_POST
def moe_decision(request, contract_id):
    # Check if user is in HR group
    if not request.user.groups.filter(name='HR').exists():
        messages.error(request, 'You are not authorized to perform this action.')
        return redirect('contract:dashboard')
    
    try:
        # Get the contract
        contract = Contract.objects.get(id=contract_id)
        
        # Check if contract has been approved by SMT
        if contract.status != 'pending':
            messages.error(request, 'This contract is not in the correct state for MOE decision.')
            return redirect('contract:review', pk=contract_id)
        
        # Get form data
        decision = request.POST.get('decision')
        comments = request.POST.get('comments', '')
        
        # Validate the decision
        if decision not in ['moe_approved', 'moe_rejected']:
            messages.error(request, 'Invalid decision.')
            return redirect('contract:review', pk=contract_id)
        
        # Validate comments for rejection
        if decision == 'moe_rejected' and not comments.strip():
            messages.error(request, 'Comments are required for MOE rejection.')
            return redirect('contract:review', pk=contract_id)
        
        # Create MOE review object
        moe_review = MOEReview(
            contract=contract,
            hr_officer=request.user.employee,
            decision=decision,
            comments=comments
        )
        
        # Handle document upload
        document = request.FILES.get('document')
        if document:
            moe_review.document = document.read()
            moe_review.document_name = document.name
        
        # Save the review
        moe_review.save()
        
        # Update contract status
        contract.status = decision
        contract.save()
        
        # Create notification for the employee
        notification_message = ""
        if decision == 'moe_rejected':
            notification_message = f"Your contract renewal (ID: {contract.contract_id}) has been rejected by the Ministry of Education."
        else:  # moe_approved
            notification_message = f"Your contract renewal (ID: {contract.contract_id}) has been approved by the Ministry of Education."
        
        # Add comments to notification if provided
        if comments.strip():
            notification_message += f" Comments: {comments}"
        
        # Add document info to notification if a document was uploaded
        if document:
            notification_message += f" A document has been attached to this decision."
        
        ContractNotification.objects.create(
            employee=contract.employee,
            message=notification_message,
            contract=contract,
            metadata={
                'moe_decision': decision,
                'moe_comments': comments,
                'processed_by': request.user.employee.id,
                'has_document': bool(document),
                'moe_review_id': moe_review.id
            }
        )
        
        # Create notification for SMT
        try:
            smt_group = Group.objects.get(name='SMT')
            smt_users = smt_group.user_set.all()
            
            # Map decision codes to human-readable text
            decision_text = {
                'moe_approved': 'approved',
                'moe_rejected': 'rejected'
            }.get(decision, decision)
            
            for smt_user in smt_users:
                try:
                    smt_employee = Employee.objects.get(user=smt_user)
                    smt_message = f"MOE has {decision_text} contract {contract.contract_id} for {contract.employee.get_full_name()}."
                    
                    # Add document info to notification if a document was uploaded
                    if document:
                        smt_message += f" A document has been attached to this decision."
                    
                    ContractNotification.objects.create(
                        employee=smt_employee,
                        message=smt_message,
                        contract=contract,
                        metadata={
                            'moe_decision': decision,
                            'moe_comments': comments,
                            'processed_by': request.user.employee.id,
                            'has_document': bool(document),
                            'moe_review_id': moe_review.id
                        }
                    )
                except Employee.DoesNotExist:
                    continue
        except Group.DoesNotExist:
            pass
        
        messages.success(request, f'MOE decision has been recorded successfully.')
        return redirect('contract:view_all_submissions')  # Redirect to all submissions page
    
    except Contract.DoesNotExist:
        messages.error(request, 'Contract not found.')
        return redirect('contract:dashboard')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('contract:review', pk=contract_id)

@login_required
def download_moe_document(request, contract_id, review_id):
    """View function to download an MOE document."""
    # Get the review object
    contract = get_object_or_404(Contract, pk=contract_id)
    review = get_object_or_404(MOEReview, pk=review_id, contract=contract)
    
    # Security check
    if not (request.user.groups.filter(name__in=['HR', 'SMT']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponse("Permission denied", status=403)
    
    if not review.document:
        return HttpResponse("No document available", status=404)
    
    # Determine content type based on file extension
    filename = review.document_name or "moe_document.pdf"
    content_type = 'application/octet-stream'  # Default
    
    if filename.lower().endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.lower().endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.lower().endswith('.doc'):
        content_type = 'application/msword'
    elif filename.lower().endswith(('.xls', '.xlsx')):
        content_type = 'application/vnd.ms-excel'
    elif filename.lower().endswith(('.ppt', '.pptx')):
        content_type = 'application/vnd.ms-powerpoint'
    
    # Create the response
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

class EmployeeContractsView(LoginRequiredMixin, View):
    template_name = 'contract/employee_contracts.html'
    
    def get(self, request):
        # Check if user is an employee
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            messages.error(request, "You don't have an employee profile.")
            return redirect('home')
        
        # Get current contracts (those in process)
        current_contracts = Contract.objects.filter(
            employee=employee,
            status__in=['pending', 'dean_review', 'smt_review', 'sent_back']
        ).order_by('-submission_date')
        
        # Get previous contracts (completed ones, including those with MOE decisions)
        previous_contracts = Contract.objects.filter(
            employee=employee,
            status__in=['smt_approved', 'smt_rejected', 'moe_approved', 'moe_rejected']
        ).order_by('-submission_date')
        
        # Check if contract submission is enabled for this employee
        contract_status = ContractRenewalStatus.objects.filter(
            employee=employee
        ).first()
        contract_enabled = contract_status.is_enabled if contract_status else False
        
        # Get draft contracts (not submitted yet)
        draft_contracts = Contract.objects.filter(
            employee=employee,
            status='draft'
        ).order_by('-submission_date')
        context = {
            'current_contracts': current_contracts,
            'previous_contracts': previous_contracts,
            'draft_contracts': draft_contracts,
            'contract_enabled': contract_enabled
        }
        
        return render(request, self.template_name, context)

@login_required
def upload_peer_review(request, contract_id):
    # Check if user is authorized (Dean or HR)
    if not request.user.groups.filter(name__in=['Dean', 'HR']).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "You don't have permission to upload peer reviews."
            }, status=403)
        messages.error(request, "You don't have permission to upload peer reviews.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "Invalid request method."
            }, status=400)
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the employee uploading the review
    employee = get_object_or_404(Employee, user=request.user)
    
    # Get form data
    review_name = request.POST.get('peer_review_name', '').strip()
    
    # Get the file
    review_file = request.FILES.get('peer_review_file')
    
    if not review_name:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "Review name is required."
            }, status=400)
        messages.error(request, "Review name is required.")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    if not review_file:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "Review file is required."
            }, status=400)
        messages.error(request, "Review file is required.")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Check file size (limit to 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    if review_file.size > MAX_FILE_SIZE:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': f"File is too large. Maximum size is 10MB. Your file is {review_file.size / (1024 * 1024):.2f}MB."
            }, status=400)
        messages.error(request, f"File is too large. Maximum size is 10MB. Your file is {review_file.size / (1024 * 1024):.2f}MB.")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Create the peer review
    try:
        peer_review = PeerReview(
            contract=contract,
            name=review_name,
            document=review_file.read(),
            document_name=review_file.name,
            uploaded_by=employee
        )
        peer_review.save()
    except Exception as e:
        # Log the error for server-side debugging
        logger = logging.getLogger(__name__)
        logger.error(f"Error saving peer review: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f"Error saving peer review: {str(e)}"
            }, status=500)
        messages.error(request, f"Error saving peer review: {str(e)}")
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Peer review '{review_name}' has been uploaded successfully.",
            'review_id': peer_review.id,
            'review_name': peer_review.name,
            'document_name': peer_review.document_name,
            'created_at': peer_review.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # For non-AJAX requests
    messages.success(request, f"Peer review '{review_name}' has been uploaded successfully.")
    
    # Redirect back to the dean review page
    if request.user.groups.filter(name='Dean').exists():
        return redirect('contract:dean_review', contract_id=contract_id)
    else:
        return redirect('contract:review', pk=contract_id)

@login_required
def download_peer_review(request, contract_id, review_id):
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        messages.error(request, "You don't have permission to access this document.")
        return redirect('dashboard')
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the review
    review = get_object_or_404(PeerReview, pk=review_id, contract=contract)
    
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
def preview_peer_review(request, contract_id, review_id):
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the review
    review = get_object_or_404(PeerReview, pk=review_id, contract=contract)
    
    if not review.document:
        return HttpResponseNotFound("No document found.")
    
    # Determine content type based on file extension
    filename = review.document_name
    content_type = 'application/octet-stream'  # Default
    if filename.endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content_type = f'image/{filename.split(".")[-1]}'
    elif filename.endswith('.txt'):
        content_type = 'text/plain'
    
    # Return the file with Content-Disposition: inline to enable preview
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def delete_peer_review(request, contract_id, review_id):
    # Check if user is authorized (Dean or HR)
    if not request.user.groups.filter(name__in=['Dean', 'HR']).exists():
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "You don't have permission to delete peer reviews."
            }, status=403)
        messages.error(request, "You don't have permission to delete peer reviews.")
        return redirect('dashboard')
    
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error', 
                'message': "Invalid request method."
            }, status=400)
        return redirect('contract:dean_review', contract_id=contract_id)
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the review
    review = get_object_or_404(PeerReview, pk=review_id, contract=contract)
    
    # Delete the review
    review_name = review.name
    review.delete()
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': f"Peer review '{review_name}' has been deleted successfully."
        })
    
    # For non-AJAX requests
    messages.success(request, f"Peer review '{review_name}' has been deleted successfully.")
    
    # Redirect back to the dean review page
    if request.user.groups.filter(name='Dean').exists():
        return redirect('contract:dean_review', contract_id=contract_id)
    else:
        return redirect('contract:review', pk=contract_id)

@login_required
def preview_moe_document(request, contract_id, review_id):
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['Dean', 'SMT', 'HOD', 'HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the MOE review
    review = get_object_or_404(MOEReview, pk=review_id, contract=contract)
    
    if not review.document:
        return HttpResponseNotFound("No document found.")
    
    # Determine content type based on file extension
    filename = review.document_name
    content_type = 'application/octet-stream'  # Default
    if filename.endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content_type = f'image/{filename.split(".")[-1]}'
    elif filename.endswith('.txt'):
        content_type = 'text/plain'
    
    # Return the file with Content-Disposition: inline to enable preview
    response = HttpResponse(review.document, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def preview_document(request, contract_id, doc_type):
    """View function to preview a document (teaching portfolio, etc.) in the browser."""
    # Check if user is authorized
    if not (request.user.groups.filter(name__in=['Dean', 'SMT','HR']).exists() or 
            Contract.objects.filter(pk=contract_id, employee__user=request.user).exists()):
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    # Get the contract
    contract = get_object_or_404(Contract, pk=contract_id)
    
    # Get the document based on doc_type
    document = None
    filename = None
    
    if doc_type == 'teaching':
        document = contract.teaching_documents
        filename = contract.teaching_documents_name
    
    if not document:
        return HttpResponseNotFound("No document found.")
    
    # Determine content type based on file extension
    content_type = 'application/octet-stream'  # Default
    if filename.endswith('.pdf'):
        content_type = 'application/pdf'
    elif filename.endswith('.docx'):
        content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content_type = f'image/{filename.split(".")[-1]}'
    elif filename.endswith('.txt'):
        content_type = 'text/plain'
    
    # Return the file with Content-Disposition: inline to enable preview
    response = HttpResponse(document, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def download_merged_contract_pdf(request, contract_id):
    """
    Create a merged PDF with contract form and all attached documents.
    """
    if not request.user.groups.filter(name__in=['HR', 'Dean', 'SMT']).exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    try:
        contract = get_object_or_404(Contract, id=contract_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Prepare context (same as before) ---
            context = {
                'contract': contract,
                'employee': contract.employee,
                'first_name': contract.employee.first_name,
                'last_name': contract.employee.last_name,
                'ic_no': contract.employee.ic_no,
                'ic_colour': {'Y': 'Yellow', 'P': 'Purple', 'G': 'Green', 'R': 'Red'}.get(contract.employee.ic_colour, contract.employee.ic_colour),
                'phone_number': contract.employee.phone_number,
                'department': contract.employee.department.name if contract.employee.department else '',
                'contract_count': Contract.objects.filter(
                    employee=contract.employee,
                    submission_date__lt=contract.submission_date
                ).count() + 1,
                'today': timezone.now().date(),
            }
            # Parse JSON fields (copy from download_contract_zip)
            try:
                context['academic_qualifications'] = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
            except json.JSONDecodeError:
                context['academic_qualifications'] = []
            try:
                context['teaching_modules'] = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
            except json.JSONDecodeError:
                context['teaching_modules'] = []
            try:
                context['university_committees'] = json.loads(contract.university_committees_text) if contract.university_committees_text else []
            except json.JSONDecodeError:
                context['university_committees'] = []
            try:
                context['external_committees'] = json.loads(contract.external_committees_text) if contract.external_committees_text else []
            except json.JSONDecodeError:
                context['external_committees'] = []
            try:
                context['attendance_events'] = json.loads(contract.attendance) if contract.attendance else []
            except json.JSONDecodeError:
                context['attendance_events'] = []
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
            try:
                context['fellowships_awards'] = json.loads(contract.fellowships_awards) if contract.fellowships_awards else []
            except Exception:
                context['fellowships_awards'] = []
            try:
                context['mentorship_data'] = json.loads(contract.mentorship_data) if contract.mentorship_data else []
            except Exception:
                context['mentorship_data'] = []
            try:
                context['grad_supervision_data'] = json.loads(contract.grad_supervision_data) if contract.grad_supervision_data else []
            except Exception:
                context['grad_supervision_data'] = []
            context['administrative_positions'] = contract.administrative_positions.all()
            context['dean_reviews'] = contract.dean_reviews.all().order_by('created_at')
            context['peer_reviews'] = PeerReview.objects.filter(contract=contract).order_by('-created_at')
            context['smt_reviews'] = contract.smt_reviews.all().order_by('created_at')
            context['moe_reviews'] = contract.moe_reviews.all().order_by('created_at')
            context['teaching_future_plan'] = contract.teaching_future_plan
            context['achievements_last_contract'] = contract.achievements_last_contract
            context['achievements_proposal'] = contract.achievements_proposal
            context['other_matters'] = contract.other_matters
            context['current_enrollment'] = contract.current_enrollment
            context['teaching_documents_name'] = contract.teaching_documents_name if contract.teaching_documents else None
            # Appraisals
            appraisals = Appraisal.objects.filter(employee=contract.employee).order_by('-date_of_last_appraisal')
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
            # --- Generate contract form PDF using the new helper ---
            main_pdf_path = os.path.join(temp_dir, 'contract_form.pdf')
            generate_contract_form_pdf(context, main_pdf_path)
            # --- Continue with merging PDFs as before ---
            merger = PdfMerger()
            merger.append(main_pdf_path)
            added_documents = []
            if contract.teaching_documents:
                try:
                    if contract.teaching_documents_name.lower().endswith('.pdf'):
                        doc_pdf_path = os.path.join(temp_dir, 'teaching_document.pdf')
                        with open(doc_pdf_path, 'wb') as f:
                            f.write(contract.teaching_documents)
                        merger.append(doc_pdf_path)
                        added_documents.append(f"Teaching Document: {contract.teaching_documents_name}")
                except Exception as e:
                    print(f"Error adding teaching document: {str(e)}")
            for idx, review in enumerate(contract.dean_reviews.all()):
                if review.document:
                    try:
                        if review.document_name.lower().endswith('.pdf'):
                            doc_pdf_path = os.path.join(temp_dir, f'dean_review_{idx}.pdf')
                            with open(doc_pdf_path, 'wb') as f:
                                f.write(review.document)
                            merger.append(doc_pdf_path)
                            added_documents.append(f"Dean Review: {review.document_name}")
                    except Exception as e:
                        print(f"Error adding dean review document: {str(e)}")
            for idx, review in enumerate(context['peer_reviews']):
                if review.document:
                    try:
                        if review.document_name.lower().endswith('.pdf'):
                            doc_pdf_path = os.path.join(temp_dir, f'peer_review_{idx}.pdf')
                            with open(doc_pdf_path, 'wb') as f:
                                f.write(review.document)
                            merger.append(doc_pdf_path)
                            added_documents.append(f"Peer Review: {review.document_name}")
                    except Exception as e:
                        print(f"Error adding peer review document: {str(e)}")
            for idx, review in enumerate(contract.smt_reviews.all()):
                if review.document:
                    try:
                        if review.document_name.lower().endswith('.pdf'):
                            doc_pdf_path = os.path.join(temp_dir, f'smt_review_{idx}.pdf')
                            with open(doc_pdf_path, 'wb') as f:
                                f.write(review.document)
                            merger.append(doc_pdf_path)
                            added_documents.append(f"SMT Review: {review.document_name}")
                    except Exception as e:
                        print(f"Error adding SMT review document: {str(e)}")
            for idx, review in enumerate(contract.moe_reviews.all()):
                if review.document:
                    try:
                        if review.document_name.lower().endswith('.pdf'):
                            doc_pdf_path = os.path.join(temp_dir, f'moe_review_{idx}.pdf')
                            with open(doc_pdf_path, 'wb') as f:
                                f.write(review.document)
                            merger.append(doc_pdf_path)
                            added_documents.append(f"MOE Review: {review.document_name}")
                    except Exception as e:
                        print(f"Error adding MOE review document: {str(e)}")
            output_path = os.path.join(temp_dir, 'merged_contract.pdf')
            merger.write(output_path)
            merger.close()
            if added_documents:
                reader = PdfReader(output_path)
                writer = PdfWriter()
                cover_buffer = io.BytesIO()
                c = canvas.Canvas(cover_buffer, pagesize=A4)
                c.setFont("Helvetica-Bold", 18)
                c.drawString(72, 770, f"Contract Form: {contract.contract_id}")
                c.setFont("Helvetica", 12)
                c.drawString(72, 750, f"Employee: {contract.employee.get_full_name()}")
                c.drawString(72, 730, f"Department: {contract.employee.department.name if contract.employee.department else 'N/A'}")
                c.drawString(72, 710, f"Generated on: {timezone.now().strftime('%Y-%m-%d')}")
                c.setFont("Helvetica-Bold", 14)
                c.drawString(72, 650, "Table of Contents")
                c.setFont("Helvetica", 12)
                c.drawString(72, 630, "1. Contract Form")
                y_position = 610
                for idx, doc_name in enumerate(added_documents):
                    c.drawString(72, y_position, f"{idx + 2}. {doc_name}")
                    y_position -= 20
                c.save()
                cover_buffer.seek(0)
                cover_pdf = PdfReader(cover_buffer)
                writer.add_page(cover_pdf.pages[0])
                for page in reader.pages:
                    writer.add_page(page)
                final_output_path = os.path.join(temp_dir, 'final_contract.pdf')
                with open(final_output_path, 'wb') as f:
                    writer.write(f)
                with open(final_output_path, 'rb') as f:
                    response = FileResponse(f, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Contract_{contract.contract_id}_with_documents.pdf"'
                    return response
            else:
                with open(output_path, 'rb') as f:
                    response = FileResponse(f, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="Contract_{contract.contract_id}.pdf"'
                    return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('contract:print_contract_form', contract_id=contract_id)

@login_required
def download_contract_zip(request, contract_id):
    """
    Download a zip file containing the contract form PDF and all attached documents.
    """
    if not request.user.groups.filter(name__in=['HR', 'Dean', 'SMT']).exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')

    try:
        contract = get_object_or_404(Contract, id=contract_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Prepare context (same as before) ---
            context = {
                'contract': contract,
                'employee': contract.employee,
                'first_name': contract.employee.first_name,
                'last_name': contract.employee.last_name,
                'ic_no': contract.employee.ic_no,
                'ic_colour': {'Y': 'Yellow', 'P': 'Purple', 'G': 'Green', 'R': 'Red'}.get(contract.employee.ic_colour, contract.employee.ic_colour),
                'phone_number': contract.employee.phone_number,
                'department': contract.employee.department.name if contract.employee.department else '',
                'contract_count': Contract.objects.filter(
                    employee=contract.employee,
                    submission_date__lt=contract.submission_date
                ).count() + 1,
                'today': timezone.now().date(),
            }
            # Parse JSON fields (copy from download_merged_contract_pdf)
            try:
                context['academic_qualifications'] = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
            except json.JSONDecodeError:
                context['academic_qualifications'] = []
            try:
                context['teaching_modules'] = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
            except json.JSONDecodeError:
                context['teaching_modules'] = []
            try:
                context['university_committees'] = json.loads(contract.university_committees_text) if contract.university_committees_text else []
            except json.JSONDecodeError:
                context['university_committees'] = []
            try:
                context['external_committees'] = json.loads(contract.external_committees_text) if contract.external_committees_text else []
            except json.JSONDecodeError:
                context['external_committees'] = []
            try:
                context['attendance_events'] = json.loads(contract.attendance) if contract.attendance else []
            except json.JSONDecodeError:
                context['attendance_events'] = []
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
            try:
                context['fellowships_awards'] = json.loads(contract.fellowships_awards) if contract.fellowships_awards else []
            except Exception:
                context['fellowships_awards'] = []
            try:
                context['mentorship_data'] = json.loads(contract.mentorship_data) if contract.mentorship_data else []
            except Exception:
                context['mentorship_data'] = []
            try:
                context['grad_supervision_data'] = json.loads(contract.grad_supervision_data) if contract.grad_supervision_data else []
            except Exception:
                context['grad_supervision_data'] = []
            context['administrative_positions'] = contract.administrative_positions.all()
            context['dean_reviews'] = contract.dean_reviews.all().order_by('created_at')
            context['peer_reviews'] = PeerReview.objects.filter(contract=contract).order_by('-created_at')
            context['smt_reviews'] = contract.smt_reviews.all().order_by('created_at')
            context['moe_reviews'] = contract.moe_reviews.all().order_by('created_at')
            context['teaching_future_plan'] = contract.teaching_future_plan
            context['achievements_last_contract'] = contract.achievements_last_contract
            context['achievements_proposal'] = contract.achievements_proposal
            context['other_matters'] = contract.other_matters
            context['current_enrollment'] = contract.current_enrollment
            context['teaching_documents_name'] = contract.teaching_documents_name if contract.teaching_documents else None
            # Appraisals
            appraisals = Appraisal.objects.filter(employee=contract.employee).order_by('-date_of_last_appraisal')
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
            # --- Generate contract form PDF using the new helper ---
            main_pdf_path = os.path.join(temp_dir, 'contract_form.pdf')
            generate_contract_form_pdf(context, main_pdf_path)
            # --- Collect all files to add to zip ---
            files_to_zip = [(main_pdf_path, f"Contract_Form_{contract.contract_id}.pdf")]
            # Teaching document
            if contract.teaching_documents:
                teach_ext = os.path.splitext(contract.teaching_documents_name)[1].lower()
                teach_path = os.path.join(temp_dir, f'teaching_document{teach_ext}')
                with open(teach_path, 'wb') as f:
                    f.write(contract.teaching_documents)
                files_to_zip.append((teach_path, contract.teaching_documents_name))
            # Dean reviews
            for idx, review in enumerate(contract.dean_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    dean_path = os.path.join(temp_dir, f'dean_review_{idx}{ext}')
                    with open(dean_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((dean_path, f"Dean_{idx+1}_{review.document_name}"))
            # SMT reviews
            for idx, review in enumerate(contract.smt_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    smt_path = os.path.join(temp_dir, f'smt_review_{idx}{ext}')
                    with open(smt_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((smt_path, f"SMT_{idx+1}_{review.document_name}"))
            # MOE reviews
            for idx, review in enumerate(contract.moe_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    moe_path = os.path.join(temp_dir, f'moe_review_{idx}{ext}')
                    with open(moe_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((moe_path, f"MOE_{idx+1}_{review.document_name}"))
            # Peer reviews
            for idx, review in enumerate(context['peer_reviews']):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    peer_path = os.path.join(temp_dir, f'peer_review_{idx}{ext}')
                    with open(peer_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((peer_path, f"Peer_{idx+1}_{review.document_name}"))
            # --- Create zip file ---
            zip_path = os.path.join(temp_dir, f'Contract_{contract.contract_id}_with_documents.zip')
            with ZipFile(zip_path, 'w') as zipf:
                for file_path, arcname in files_to_zip:
                    zipf.write(file_path, arcname)
            # --- Return zip as response ---
            with open(zip_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="Contract_{contract.contract_id}_with_documents.zip"'
                return response
    except Exception as e:
        messages.error(request, f"Error generating ZIP: {str(e)}")
        return redirect('contract:print_contract_form', contract_id=contract_id)

# --- PDF generation helper for contract form, matching the HTML CV template ---
@login_required
def download_contract_zip(request, contract_id):
    """
    Download a zip file containing the contract form PDF and all attached documents.
    """
    if not request.user.groups.filter(name__in=['HR', 'Dean', 'SMT']).exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')

    try:
        contract = get_object_or_404(Contract, id=contract_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Prepare context (same as before) ---
            context = {
                'contract': contract,
                'employee': contract.employee,
                'first_name': contract.employee.first_name,
                'last_name': contract.employee.last_name,
                'ic_no': contract.employee.ic_no,
                'ic_colour': {'Y': 'Yellow', 'P': 'Purple', 'G': 'Green', 'R': 'Red'}.get(contract.employee.ic_colour, contract.employee.ic_colour),
                'phone_number': contract.employee.phone_number,
                'department': contract.employee.department.name if contract.employee.department else '',
                'contract_count': Contract.objects.filter(
                    employee=contract.employee,
                    submission_date__lt=contract.submission_date
                ).count() + 1,
                'today': timezone.now().date(),
            }
            # Parse JSON fields (copy from download_merged_contract_pdf)
            try:
                context['academic_qualifications'] = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
            except json.JSONDecodeError:
                context['academic_qualifications'] = []
            try:
                context['teaching_modules'] = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
            except json.JSONDecodeError:
                context['teaching_modules'] = []
            try:
                context['university_committees'] = json.loads(contract.university_committees_text) if contract.university_committees_text else []
            except json.JSONDecodeError:
                context['university_committees'] = []
            try:
                context['external_committees'] = json.loads(contract.external_committees_text) if contract.external_committees_text else []
            except json.JSONDecodeError:
                context['external_committees'] = []
            try:
                context['attendance_events'] = json.loads(contract.attendance) if contract.attendance else []
            except json.JSONDecodeError:
                context['attendance_events'] = []
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
            try:
                context['fellowships_awards'] = json.loads(contract.fellowships_awards) if contract.fellowships_awards else []
            except Exception:
                context['fellowships_awards'] = []
            try:
                context['mentorship_data'] = json.loads(contract.mentorship_data) if contract.mentorship_data else []
            except Exception:
                context['mentorship_data'] = []
            try:
                context['grad_supervision_data'] = json.loads(contract.grad_supervision_data) if contract.grad_supervision_data else []
            except Exception:
                context['grad_supervision_data'] = []
            context['administrative_positions'] = contract.administrative_positions.all()
            context['dean_reviews'] = contract.dean_reviews.all().order_by('created_at')
            context['peer_reviews'] = PeerReview.objects.filter(contract=contract).order_by('-created_at')
            context['smt_reviews'] = contract.smt_reviews.all().order_by('created_at')
            context['moe_reviews'] = contract.moe_reviews.all().order_by('created_at')
            context['teaching_future_plan'] = contract.teaching_future_plan
            context['achievements_last_contract'] = contract.achievements_last_contract
            context['achievements_proposal'] = contract.achievements_proposal
            context['other_matters'] = contract.other_matters
            context['current_enrollment'] = contract.current_enrollment
            context['teaching_documents_name'] = contract.teaching_documents_name if contract.teaching_documents else None
            # Appraisals
            appraisals = Appraisal.objects.filter(employee=contract.employee).order_by('-date_of_last_appraisal')
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
            # --- Generate contract form PDF using the new helper ---
            main_pdf_path = os.path.join(temp_dir, 'contract_form.pdf')
            generate_contract_form_pdf(context, main_pdf_path)
            # --- Collect all files to add to zip ---
            files_to_zip = [(main_pdf_path, f"Contract_Form_{contract.contract_id}.pdf")]
            # Teaching document
            if contract.teaching_documents:
                teach_ext = os.path.splitext(contract.teaching_documents_name)[1].lower()
                teach_path = os.path.join(temp_dir, f'teaching_document{teach_ext}')
                with open(teach_path, 'wb') as f:
                    f.write(contract.teaching_documents)
                files_to_zip.append((teach_path, contract.teaching_documents_name))
            # Dean reviews
            for idx, review in enumerate(contract.dean_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    dean_path = os.path.join(temp_dir, f'dean_review_{idx}{ext}')
                    with open(dean_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((dean_path, f"Dean_{idx+1}_{review.document_name}"))
            # SMT reviews
            for idx, review in enumerate(contract.smt_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    smt_path = os.path.join(temp_dir, f'smt_review_{idx}{ext}')
                    with open(smt_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((smt_path, f"SMT_{idx+1}_{review.document_name}"))
            # MOE reviews
            for idx, review in enumerate(contract.moe_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    moe_path = os.path.join(temp_dir, f'moe_review_{idx}{ext}')
                    with open(moe_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((moe_path, f"MOE_{idx+1}_{review.document_name}"))
            # Peer reviews
            for idx, review in enumerate(context['peer_reviews']):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    peer_path = os.path.join(temp_dir, f'peer_review_{idx}{ext}')
                    with open(peer_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((peer_path, f"Peer_{idx+1}_{review.document_name}"))
            # --- Create zip file ---
            zip_path = os.path.join(temp_dir, f'Contract_{contract.contract_id}_with_documents.zip')
            with ZipFile(zip_path, 'w') as zipf:
                for file_path, arcname in files_to_zip:
                    zipf.write(file_path, arcname)
            # --- Return zip as response ---
            with open(zip_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="Contract_{contract.contract_id}_with_documents.zip"'
                return response
    except Exception as e:
        messages.error(request, f"Error generating ZIP: {str(e)}")
        return redirect('contract:print_contract_form', contract_id=contract_id)

# --- PDF generation helper for contract form, matching the HTML CV template ---
@login_required
def download_contract_zip(request, contract_id):
    """
    Download a zip file containing the contract form PDF and all attached documents.
    """
    if not request.user.groups.filter(name__in=['HR', 'Dean', 'SMT']).exists():
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')

    try:
        contract = get_object_or_404(Contract, id=contract_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            # --- Prepare context (same as before) ---
            context = {
                'contract': contract,
                'employee': contract.employee,
                'first_name': contract.employee.first_name,
                'last_name': contract.employee.last_name,
                'ic_no': contract.employee.ic_no,
                'ic_colour': {'Y': 'Yellow', 'P': 'Purple', 'G': 'Green', 'R': 'Red'}.get(contract.employee.ic_colour, contract.employee.ic_colour),
                'phone_number': contract.employee.phone_number,
                'department': contract.employee.department.name if contract.employee.department else '',
                'contract_count': Contract.objects.filter(
                    employee=contract.employee,
                    submission_date__lt=contract.submission_date
                ).count() + 1,
                'today': timezone.now().date(),
            }
            # Parse JSON fields (copy from download_merged_contract_pdf)
            try:
                context['academic_qualifications'] = json.loads(contract.academic_qualifications_text) if contract.academic_qualifications_text else []
            except json.JSONDecodeError:
                context['academic_qualifications'] = []
            try:
                context['teaching_modules'] = json.loads(contract.teaching_modules_text) if contract.teaching_modules_text else []
            except json.JSONDecodeError:
                context['teaching_modules'] = []
            try:
                context['university_committees'] = json.loads(contract.university_committees_text) if contract.university_committees_text else []
            except json.JSONDecodeError:
                context['university_committees'] = []
            try:
                context['external_committees'] = json.loads(contract.external_committees_text) if contract.external_committees_text else []
            except json.JSONDecodeError:
                context['external_committees'] = []
            try:
                context['attendance_events'] = json.loads(contract.attendance) if contract.attendance else []
            except json.JSONDecodeError:
                context['attendance_events'] = []
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
            try:
                context['fellowships_awards'] = json.loads(contract.fellowships_awards) if contract.fellowships_awards else []
            except Exception:
                context['fellowships_awards'] = []
            try:
                context['mentorship_data'] = json.loads(contract.mentorship_data) if contract.mentorship_data else []
            except Exception:
                context['mentorship_data'] = []
            try:
                context['grad_supervision_data'] = json.loads(contract.grad_supervision_data) if contract.grad_supervision_data else []
            except Exception:
                context['grad_supervision_data'] = []
            context['administrative_positions'] = contract.administrative_positions.all()
            context['dean_reviews'] = contract.dean_reviews.all().order_by('created_at')
            context['peer_reviews'] = PeerReview.objects.filter(contract=contract).order_by('-created_at')
            context['smt_reviews'] = contract.smt_reviews.all().order_by('created_at')
            context['moe_reviews'] = contract.moe_reviews.all().order_by('created_at')
            context['teaching_future_plan'] = contract.teaching_future_plan
            context['achievements_last_contract'] = contract.achievements_last_contract
            context['achievements_proposal'] = contract.achievements_proposal
            context['other_matters'] = contract.other_matters
            context['current_enrollment'] = contract.current_enrollment
            context['teaching_documents_name'] = contract.teaching_documents_name if contract.teaching_documents else None
            # Appraisals
            appraisals = Appraisal.objects.filter(employee=contract.employee).order_by('-date_of_last_appraisal')
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
            # --- Generate contract form PDF using the new helper ---
            main_pdf_path = os.path.join(temp_dir, 'contract_form.pdf')
            generate_contract_form_pdf(context, main_pdf_path)
            # --- Collect all files to add to zip ---
            files_to_zip = [(main_pdf_path, f"Contract_Form_{contract.contract_id}.pdf")]
            # Teaching document
            if contract.teaching_documents:
                teach_ext = os.path.splitext(contract.teaching_documents_name)[1].lower()
                teach_path = os.path.join(temp_dir, f'teaching_document{teach_ext}')
                with open(teach_path, 'wb') as f:
                    f.write(contract.teaching_documents)
                files_to_zip.append((teach_path, contract.teaching_documents_name))
            # Dean reviews
            for idx, review in enumerate(contract.dean_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    dean_path = os.path.join(temp_dir, f'dean_review_{idx}{ext}')
                    with open(dean_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((dean_path, f"Dean_{idx+1}_{review.document_name}"))
            # SMT reviews
            for idx, review in enumerate(contract.smt_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    smt_path = os.path.join(temp_dir, f'smt_review_{idx}{ext}')
                    with open(smt_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((smt_path, f"SMT_{idx+1}_{review.document_name}"))
            # MOE reviews
            for idx, review in enumerate(contract.moe_reviews.all()):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    moe_path = os.path.join(temp_dir, f'moe_review_{idx}{ext}')
                    with open(moe_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((moe_path, f"MOE_{idx+1}_{review.document_name}"))
            # Peer reviews
            for idx, review in enumerate(context['peer_reviews']):
                if review.document:
                    ext = os.path.splitext(review.document_name)[1].lower()
                    peer_path = os.path.join(temp_dir, f'peer_review_{idx}{ext}')
                    with open(peer_path, 'wb') as f:
                        f.write(review.document)
                    files_to_zip.append((peer_path, f"Peer_{idx+1}_{review.document_name}"))
            # --- Create zip file ---
            zip_path = os.path.join(temp_dir, f'Contract_{contract.contract_id}_with_documents.zip')
            with ZipFile(zip_path, 'w') as zipf:
                for file_path, arcname in files_to_zip:
                    zipf.write(file_path, arcname)
            # --- Return zip as response ---
            with open(zip_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename="Contract_{contract.contract_id}_with_documents.zip"'
                return response
    except Exception as e:
        messages.error(request, f"Error generating ZIP: {str(e)}")
        return redirect('contract:print_contract_form', contract_id=contract_id)

# --- PDF generation helper for contract form, matching the HTML CV template ---
def generate_contract_form_pdf(context, output_path):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    custom_styles = {
        'CustomHeading1': ParagraphStyle(name='CustomHeading1', parent=styles['Heading1'], fontSize=16, spaceAfter=12, textColor=colors.navy),
        'CustomHeading2': ParagraphStyle(name='CustomHeading2', parent=styles['Heading2'], fontSize=14, spaceAfter=10, textColor=colors.darkblue),
        'CustomHeading3': ParagraphStyle(name='CustomHeading3', parent=styles['Heading3'], fontSize=12, spaceAfter=8, textColor=colors.darkblue),
        'CustomItalic': ParagraphStyle(name='CustomItalic', parent=styles['Italic'], fontSize=10),
        'CustomNormal': ParagraphStyle(name='CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)
    }
    for style_name, style in custom_styles.items():
        if style_name not in styles:
            styles.add(style)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    # University Header
    elements.append(Paragraph("University Contract Renewal Form", custom_styles['CustomHeading1']))
    elements.append(Paragraph("Human Resources Department", custom_styles['CustomNormal']))
    elements.append(Paragraph(f"Contract ID: {context['contract'].contract_id}", custom_styles['CustomNormal']))
    elements.append(Paragraph(f"Submission Date: {context['contract'].submission_date.strftime('%B %d, %Y')}", custom_styles['CustomNormal']))
    elements.append(Spacer(1, 20))
    # Document Title
    elements.append(Paragraph(f"{context['first_name']} {context['last_name']}", custom_styles['CustomHeading1']))
    elements.append(Paragraph("Contract Renewal Application", custom_styles['CustomHeading2']))
    elements.append(Spacer(1, 10))
    # Basic Information Summary Card
    elements.append(Paragraph("Basic Information", custom_styles['CustomHeading2']))
    info_data = [
        ["Position:", f"{context['contract'].present_post}"],
        ["Department:", f"{context['department']}"] ,
        ["IC Number:", f"{context['ic_no']} ({context['ic_colour']})"],
        ["Phone:", f"{context['phone_number']}"] ,
        ["Salary Scale:", f"{context['contract'].salary_scale_division}"],
        ["Past Contracts:", f"{context['contract_count']}"]
    ]
    info_table = Table(info_data, colWidths=[120, 350])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    # 2. Education
    elements.append(Paragraph("Education", custom_styles['CustomHeading2']))
    if context.get('academic_qualifications'):
        edu_data = [["Year", "Degree/Diploma", "Institution"]]
        for qual in context['academic_qualifications']:
            edu_data.append([
                qual.get('to_date', ''),
                qual.get('degree_diploma', ''),
                qual.get('university_college', '')
            ])
        edu_table = Table(edu_data, colWidths=[80, 200, 200])
        edu_table.setStyle(table_style)
        elements.append(edu_table)
    else:
        elements.append(Paragraph("No academic qualifications provided", custom_styles['CustomItalic']))
    if context.get('current_enrollment'):
        elements.append(Paragraph(f"Currently Enrolled: {context['current_enrollment']}", custom_styles['CustomNormal']))
    elements.append(Spacer(1, 15))
    # 3. Employment History
    elements.append(Paragraph("Employment History", custom_styles['CustomHeading2']))
    if context.get('administrative_positions'):
        emp_data = [["Period", "Position", "Details"]]
        for position in context['administrative_positions']:
            emp_data.append([
                f"{position.from_date} to {position.to_date}",
                position.title,
                position.details or ""
            ])
        emp_table = Table(emp_data, colWidths=[150, 150, 180])
        emp_table.setStyle(table_style)
        elements.append(emp_table)
    else:
        elements.append(Paragraph("No employment history provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 4. Administrative Positions
    elements.append(Paragraph("Administrative Positions & Appointments", custom_styles['CustomHeading2']))
    if context.get('administrative_positions'):
        admin_data = [["Date", "Position"]]
        for position in context['administrative_positions']:
            admin_data.append([
                position.from_date.strftime("%Y-%m-%d"),
                position.title
            ])
        admin_table = Table(admin_data, colWidths=[150, 330])
        admin_table.setStyle(table_style)
        elements.append(admin_table)
    else:
        elements.append(Paragraph("No administrative positions recorded", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 5. Academic, Social & Community Service
    elements.append(Paragraph("Academic, Social & Community Service", custom_styles['CustomHeading2']))
    if context.get('university_committees'):
        elements.append(Paragraph("University Committees", custom_styles['CustomHeading3']))
        uni_data = [["Date", "Committee", "Position"]]
        for committee in context['university_committees']:
            uni_data.append([
                committee.get('from_date', ''),
                committee.get('name', ''),
                committee.get('position', '')
            ])
        uni_table = Table(uni_data, colWidths=[100, 230, 150])
        uni_table.setStyle(table_style)
        elements.append(uni_table)
    if context.get('external_committees'):
        elements.append(Paragraph("External Committees", custom_styles['CustomHeading3']))
        ext_data = [["Date", "Organization", "Position"]]
        for committee in context['external_committees']:
            ext_data.append([
                committee.get('from_date', ''),
                committee.get('organization', ''),
                committee.get('position', '')
            ])
        ext_table = Table(ext_data, colWidths=[100, 230, 150])
        ext_table.setStyle(table_style)
        elements.append(ext_table)
    if not context.get('university_committees') and not context.get('external_committees'):
        elements.append(Paragraph("No committee positions recorded", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 6. Fellowships and Awards
    elements.append(Paragraph("Fellowships and Awards", custom_styles['CustomHeading2']))
    if context.get('fellowships_awards'):
        award_data = [["Date", "Award", "Organization"]]
        for award in context['fellowships_awards']:
            award_data.append([
                award.get('date', ''),
                award.get('title', ''),
                award.get('organization', '')
            ])
        award_table = Table(award_data, colWidths=[100, 200, 180])
        award_table.setStyle(table_style)
        elements.append(award_table)
    else:
        elements.append(Paragraph("No fellowships or awards provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 7. Current Research Areas & Interests
    elements.append(Paragraph("Current Research Areas & Interests", custom_styles['CustomHeading2']))
    if context.get('ongoing_research'):
        research_data = [["Research Title"]]
        for research in context['ongoing_research']:
            research_data.append([research.get('title', '')])
        research_table = Table(research_data, colWidths=[400])
        research_table.setStyle(table_style)
        elements.append(research_table)
    else:
        elements.append(Paragraph("No current research areas provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 8. Research Experience & Grants
    elements.append(Paragraph("Research Experience & Grants", custom_styles['CustomHeading2']))
    if context.get('research_history'):
        rh_data = [["Period", "Project", "Funding Agency"]]
        for research in context['research_history']:
            rh_data.append([
                f"{research.get('startDate', '')} - {research.get('endDate', '')}",
                research.get('title', ''),
                research.get('fundingAgency', '')
            ])
        rh_table = Table(rh_data, colWidths=[120, 180, 180])
        rh_table.setStyle(table_style)
        elements.append(rh_table)
    else:
        elements.append(Paragraph("No research experience records provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 9. Teaching Areas & Interests
    elements.append(Paragraph("Teaching Areas & Interests", custom_styles['CustomHeading2']))
    if context.get('teaching_modules'):
        tm_data = [["Module"]]
        for module in context['teaching_modules']:
            tm_data.append([module.get('title', '')])
        tm_table = Table(tm_data, colWidths=[400])
        tm_table.setStyle(table_style)
        elements.append(tm_table)
    else:
        elements.append(Paragraph("No teaching areas provided", custom_styles['CustomItalic']))
    if context.get('teaching_future_plan'):
        elements.append(Paragraph("Future Teaching Plans", custom_styles['CustomHeading3']))
        elements.append(Paragraph(context['teaching_future_plan'], custom_styles['CustomNormal']))
    elements.append(Spacer(1, 15))
    # 10. Teaching History & Modules Taught
    elements.append(Paragraph("Teaching History & Modules Taught", custom_styles['CustomHeading2']))
    if context.get('teaching_modules'):
        tmh_data = [["Module", "Level", "Language"]]
        for module in context['teaching_modules']:
            tmh_data.append([
                module.get('title', ''),
                module.get('level', ''),
                module.get('language', '')
            ])
        tmh_table = Table(tmh_data, colWidths=[180, 110, 110])
        tmh_table.setStyle(table_style)
        elements.append(tmh_table)
    else:
        elements.append(Paragraph("No teaching modules provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 11. Consultancy
    elements.append(Paragraph("Consultancy", custom_styles['CustomHeading2']))
    if context.get('consultancy_work'):
        cons_data = [["Date", "Company", "Project"]]
        for work in context['consultancy_work']:
            cons_data.append([
                work.get('startDate', ''),
                work.get('company', ''),
                work.get('title', '')
            ])
        cons_table = Table(cons_data, colWidths=[100, 180, 180])
        cons_table.setStyle(table_style)
        elements.append(cons_table)
    else:
        elements.append(Paragraph("No consultancy work records provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 12. Publications (Conference Papers)
    elements.append(Paragraph("Publications", custom_styles['CustomHeading2']))
    elements.append(Paragraph("Conference Papers", custom_styles['CustomHeading3']))
    if context.get('conference_papers'):
        pub_list = []
        for paper in context['conference_papers']:
            author = paper.get('author', '')
            title = paper.get('title', '')
            year = paper.get('year', '')
            pub_list.append(f"{author}, \"{title}\", {year}")
        for pub in pub_list:
            elements.append(Paragraph(pub, custom_styles['CustomNormal']))
    else:
        elements.append(Paragraph("No conference papers provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 13. Mentorship
    elements.append(Paragraph("Mentorship", custom_styles['CustomHeading2']))
    if context.get('mentorship_data'):
        ment_data = [["Name", "Programme", "Period"]]
        for mentorship in context['mentorship_data']:
            ment_data.append([
                mentorship.get('name', ''),
                mentorship.get('programme', ''),
                f"{mentorship.get('startDate', '')} to {mentorship.get('endDate', '')}"
            ])
        ment_table = Table(ment_data, colWidths=[150, 150, 150])
        ment_table.setStyle(table_style)
        elements.append(ment_table)
    else:
        elements.append(Paragraph("No mentorship information provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # 14. Supervision of Graduate Students
    elements.append(Paragraph("Supervision of Graduate Students", custom_styles['CustomHeading2']))
    if context.get('grad_supervision_data'):
        grad_data = [["Name", "Programme", "Status"]]
        for supervision in context['grad_supervision_data']:
            grad_data.append([
                supervision.get('name', ''),
                supervision.get('programme', ''),
                supervision.get('status', '')
            ])
        grad_table = Table(grad_data, colWidths=[150, 150, 150])
        grad_table.setStyle(table_style)
        elements.append(grad_table)
    else:
        elements.append(Paragraph("No graduate student supervision information provided", custom_styles['CustomItalic']))
    elements.append(Spacer(1, 15))
    # Achievements and Future Plans
    elements.append(Paragraph("Achievements and Future Plans", custom_styles['CustomHeading2']))
    elements.append(Paragraph("Achievements in Last Contract (Teaching / Research / Admin)", custom_styles['CustomHeading3']))
    elements.append(Paragraph(context.get('achievements_last_contract', 'N/A') or 'N/A', custom_styles['CustomNormal']))
    elements.append(Paragraph("Proposed Undertakings and Achievements if Renewed", custom_styles['CustomHeading3']))
    elements.append(Paragraph(context.get('achievements_proposal', 'N/A') or 'N/A', custom_styles['CustomNormal']))
    elements.append(Spacer(1, 15))
    # Other Matters
    elements.append(Paragraph("Other Matters", custom_styles['CustomHeading2']))
    elements.append(Paragraph(context.get('other_matters', 'N/A') or 'N/A', custom_styles['CustomNormal']))
    elements.append(Spacer(1, 15))
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("This document is automatically generated by the HR Contract Management System.", custom_styles['CustomItalic']))
    elements.append(Paragraph(f"Printed on: {context['today'].strftime('%B %d, %Y')}", custom_styles['CustomItalic']))
    doc.build(elements)
    return output_path