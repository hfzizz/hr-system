from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Appraisal, AppraisalPeriod, AppraisalSection
from employees.models import Employee, Department
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .forms import ModuleFormSet, SectionAForm, SectionBForm, SectionCForm, SectionDForm, SectionEForm
from employees.forms import QualificationFormSet
from django.forms import inlineformset_factory
from django.core.exceptions import PermissionDenied
from django.template.context_processors import request
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
from django.urls import reverse
from django.db import transaction
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from datetime import datetime, timedelta
from django.core.cache import cache
from django.views.decorators.csrf import csrf_protect

logger = logging.getLogger(__name__)

# Constants
HR_GROUP_NAME = 'HR'
APPRAISER_GROUP_NAME = 'Appraiser'

# ============================================================================
# Appraisal Period Management Views
# =============================================================================


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
        
        # My Appraisals tab - show appraisals where user is the employee
        # Add appraisee_review status to show appraisals waiting for employee review
        context['my_appraisals'] = Appraisal.objects.filter(
            employee__user=user,
            status__in=['pending', 'primary_review', 'secondary_review', 'returned_to_appraisee','appraisee_review', 'hr_review', 'reassigned_review'],
        ).select_related('employee__user', 'appraiser__user', 'appraiser_secondary')
        
        # To help UI distinguish between pending forms and those needing review
        context['pending_appraisal_ids'] = list(Appraisal.objects.filter(
            employee__user=user,
            status='pending'
        ).values_list('appraisal_id', flat=True))
        
        context['appraisee_review_ids'] = list(Appraisal.objects.filter(
            employee__user=user,
            status='appraisee_review'
        ).values_list('appraisal_id', flat=True))
        
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
        appraisal.status = 'pending',
        appraisal.save()
    
class AppraiserWizard(BaseAppraisalWizard):
    form_list = [
        ('section_a_readonly', SectionAForm),  # Employee Information
        ('section_b', SectionBForm),  # General Traits
        ('section_c', SectionCForm),  # Local Staff Appraisal
        ('section_d', SectionDForm),  # Adverse Appraisal
    ]
    
    templates = {
        'section_a_readonly': 'appraisals/wizard/section_a_readonly.html',
        'section_b': 'appraisals/wizard/section_b.html',
        'section_c': 'appraisals/wizard/section_c.html',
        'section_d': 'appraisals/wizard/section_d.html',
    }

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        
        # Get the appraisal instance
        appraisal_id = self.kwargs.get('appraisal_id')
        if appraisal_id:
            try:
                appraisal = Appraisal.objects.get(appraisal_id=appraisal_id)
                context['appraisal'] = appraisal
            except Appraisal.DoesNotExist:
                pass
        
        context.update({
            'can_save_draft': True,
            'appraisal_id': appraisal_id,
            'is_edit': self.kwargs.get('is_edit', False)
        })
        return context

    def get_form_instance(self, step):
        """Initialize form instance with existing appraisal data"""
        appraisal_id = self.kwargs.get('appraisal_id') or self.kwargs.get('pk')
        
        if appraisal_id:
            try:
                # Only use appraisal_id field
                appraisal = Appraisal.objects.filter(
                    appraisal_id=appraisal_id
                ).select_related('employee', 'appraiser').first()
                
                if appraisal:
                    # Verify the appraisal has all required related objects
                    if not hasattr(appraisal, 'employee') or appraisal.employee is None:
                        logger.error(f"Appraisal {appraisal_id} has no associated employee")
                        raise Http404(f"Appraisal {appraisal_id} is incomplete (missing employee)")
                    
                    return appraisal
            except Exception as e:
                logger.error(f"Error fetching appraisal: {str(e)}")
        return None

    def dispatch(self, request, *args, **kwargs):
        # Check if 'appraisal_id' is in kwargs, otherwise try 'pk'
        appraisal_id = kwargs.get('appraisal_id') or kwargs.get('pk')
        
        if not appraisal_id:
            raise Http404("Appraisal ID not provided")
        
        try:
            # Only use appraisal_id field, not id since it doesn't exist
            appraisal = Appraisal.objects.filter(
                appraisal_id=appraisal_id
            ).select_related('employee', 'appraiser', 'appraiser_secondary').first()
            
            if not appraisal:
                raise Http404(f"Appraisal with ID {appraisal_id} not found")
            
            # Verify the appraisal has all required related objects
            if not hasattr(appraisal, 'employee') or appraisal.employee is None:
                logger.error(f"Appraisal {appraisal_id} has no associated employee")
                raise Http404(f"Appraisal {appraisal_id} is incomplete (missing employee)")
                
            # Check if user is authorized to review this appraisal
            # Add check for secondary appraiser
            is_primary_appraiser = appraisal.appraiser.user == request.user
            is_secondary_appraiser = appraisal.appraiser_secondary and appraisal.appraiser_secondary.user == request.user
            is_hr = request.user.groups.filter(name=HR_GROUP_NAME).exists()
            
            if not (is_primary_appraiser or is_secondary_appraiser or is_hr):
                # Correctly raise PermissionDenied instead of converting it to Http404
                raise PermissionDenied("You are not authorized to review this appraisal")
                    
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied as e:
            # Properly handle permission errors
            logger.warning(f"Permission denied: {str(e)}")
            raise  # Re-raise the PermissionDenied exception to trigger the 403 page
        except Exception as e:
            logger.error(f"Error in dispatch: {str(e)}")
            raise Http404(f"Error loading appraisal with ID {appraisal_id}: {str(e)}")

@login_required
def appraisal_wizard_section_a(request, appraisal_id):
    """Render section A of the appraisal wizard"""
    appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
    
    # Check permissions
    if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
        raise PermissionDenied("You are not authorized to review this appraisal")
        
    return render(request, 'appraisals/wizard/section_a_readonly.html', {
        'appraisal': appraisal,
    })

@login_required
def appraisal_wizard_section_c(request, appraisal_id):
    """Render section C of the appraisal wizard"""
    appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
    
    # Check permissions
    if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
        raise PermissionDenied("You are not authorized to review this appraisal")
        
    return render(request, 'appraisals/wizard/section_c.html', {
        'appraisal': appraisal,
    })

@login_required
def appraisal_wizard_section_d(request, appraisal_id):
    """Render section D of the appraisal wizard"""
    appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
    
    # Check permissions
    if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
        raise PermissionDenied("You are not authorized to review this appraisal")
        
    return render(request, 'appraisals/wizard/section_d.html', {
        'appraisal': appraisal,
    })

@login_required
def appraisal_wizard_section_e(request, appraisal_id):
    """Render section E of the appraisal wizard"""
    appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
    
    # Check permissions
    if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
        raise PermissionDenied("You are not authorized to review this appraisal")
        
    return render(request, 'appraisals/wizard/section_e.html', {
        'appraisal': appraisal,
    })
    
    
@require_POST
@login_required
def save_rating(request):
    """Save a rating value from a radio button selection"""
    try:
        field = request.POST.get('field')
        section = request.POST.get('section')
        value = request.POST.get('value')
        appraisal_id = request.POST.get('appraisal_id')
        # Get the appraiser from the current user
        appraiser = request.user.employee
        
        if not all([field, section, value, appraisal_id]):
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
            
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check if user has permission to modify this appraisal
        if not (appraisal.appraiser.user == request.user or 
                appraisal.appraiser_secondary.user == request.user or 
                request.user.groups.filter(name='HR').exists()):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # Get or create the appraisal section specific to this appraiser
        section_obj, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name=section,
            appraiser=appraiser  # This makes the section specific to this appraiser
        )
        
        # Update the field data
        if not section_obj.data:
            section_obj.data = {}
            
        section_obj.data[field] = value
        section_obj.save()
        
        return JsonResponse({'status': 'success', 'message': 'Rating saved'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@login_required
def save_text_field(request):
    """Save content from a textarea"""
    try:
        field = request.POST.get('field')
        section = request.POST.get('section')
        value = request.POST.get('value', '')  # Empty string is a valid text value
        appraisal_id = request.POST.get('appraisal_id')
        
        if not all([field, section, appraisal_id]):
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
            
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check if user has permission to modify this appraisal
        if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # Get or create the appraisal section
        section_obj, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name=section
        )
        
        # Update the field data
        if not section_obj.data:
            section_obj.data = {}
            
        section_obj.data[field] = value
        section_obj.save()
        
        return JsonResponse({'status': 'success', 'message': 'Text saved'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@csrf_protect
def save_field(request):
    """Universal handler for saving any field in any section"""
    try:
        # Get data from request
        field = request.POST.get('field')
        value = request.POST.get('value')
        section_name = request.POST.get('section')
        appraisal_id = request.POST.get('appraisal_id')
        
        if not all([field, section_name, appraisal_id]):
            return JsonResponse({'status': 'error', 'message': 'Missing required data'}, status=400)
        
        # Get the appraisal
        appraisal = Appraisal.objects.get(appraisal_id=appraisal_id)
        
        # Get or create the appropriate section
        section, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name=section_name,
            appraiser=request.user.employee  # Assuming the current user is the appraiser
        )
        
        # Update the data dictionary with the new field value
        data = section.data or {}
        data[field] = value
        section.data = data
        section.save()
        
        return JsonResponse({'status': 'success'})
        
    except Appraisal.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appraisal not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
# @require_GET
# @login_required
# def toggle_leadership_section(request):
#     """Toggle the leadership section visibility"""
#     try:
#         show = 'is_leadership_role' in request.GET
#         appraisal_id = request.GET.get('appraisal_id')
        
#         if not appraisal_id:
#             return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
            
#         appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
#         # Check if user has permission to view this appraisal
#         if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
#             return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
#         # Get or create the section object to store leadership role flag
#         section_obj, created = AppraisalSection.objects.get_or_create(
#             appraisal=appraisal,
#             section_name='B10'
#         )
        
#         if not section_obj.data:
#             section_obj.data = {}
            
#         # Update the section data to reflect leadership role status
#         section_obj.data['is_leadership_role'] = show
#         section_obj.save()
        
#         # Return HTML for leadership fields if showing
#         if show:
#             # HTML for leadership rating form elements
#             html = f"""
#             <div class="bg-white rounded p-4">
#                 <div class="mb-6">
#                     <label class="block text-gray-700 mb-2">Leadership qualities</label>
#                     <div class="flex items-center gap-4">
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_leadership" id="b10_leadership_1" value="1"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_leadership", "section": "B10", "value": "1", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_leadership_1">1</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_leadership" id="b10_leadership_2" value="2"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_leadership", "section": "B10", "value": "2", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_leadership_2">2</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_leadership" id="b10_leadership_3" value="3"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_leadership", "section": "B10", "value": "3", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_leadership_3">3</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_leadership" id="b10_leadership_4" value="4"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_leadership", "section": "B10", "value": "4", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_leadership_4">4</label>
#                         </div>
#                     </div>
#                 </div>
                
#                 <div class="mb-6">
#                     <label class="block text-gray-700 mb-2">Decision-making abilities</label>
#                     <div class="flex items-center gap-4">
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_decision_making" id="b10_decision_making_1" value="1"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_decision_making", "section": "B10", "value": "1", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_decision_making_1">1</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_decision_making" id="b10_decision_making_2" value="2"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_decision_making", "section": "B10", "value": "2", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_decision_making_2">2</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_decision_making" id="b10_decision_making_3" value="3"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_decision_making", "section": "B10", "value": "3", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_decision_making_3">3</label>
#                         </div>
#                         <div class="flex items-center">
#                             <input class="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded-full" 
#                                 type="radio" name="b10_decision_making" id="b10_decision_making_4" value="4"
#                                 hx-post="/appraisals/save-rating/"
#                                 hx-trigger="change"
#                                 hx-vals='{"field": "b10_decision_making", "section": "B10", "value": "4", "appraisal_id": "%s"}'
#                                 hx-swap="none"
#                                 hx-indicator="#save-indicator">
#                             <label class="ml-1 text-gray-700" for="b10_decision_making_4">4</label>
#                         </div>
#                     </div>
#                 </div>
#             </div>
#             """ (appraisal_id, appraisal_id, appraisal_id, appraisal_id, appraisal_id, appraisal_id, appraisal_id, appraisal_id)
            
#             return JsonResponse({'status': 'success', 'html': html})
#         else:
#             # If not showing leadership section, return empty HTML
#             return JsonResponse({'status': 'success', 'html': ''})
    
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@require_GET
@login_required
def toggle_leadership_section(request):
    """Toggle the leadership section visibility"""
    try:
        show = 'is_leadership_role' in request.GET
        appraisal_id = request.GET.get('appraisal_id')
        
        if not appraisal_id:
            return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
            
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check if user has permission to view this appraisal
        if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # Get or create the section object to store leadership role flag
        section_obj, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name='B10'
        )
        
        if not section_obj.data:
            section_obj.data = {}
            
        # Update the section data to reflect leadership role status
        section_obj.data['is_leadership_role'] = show
        section_obj.save()
        
        # Return a simplified response for debugging
        if show:
            # Just return a simple div for now to test if it works
            html = f"""
            <div class="bg-white rounded p-4">
                <p>Leadership section is now visible. Appraisal ID: {appraisal_id}</p>
            </div>
            """
            return JsonResponse({'status': 'success', 'html': html})
        else:
            return JsonResponse({'status': 'success', 'html': ''})
    
    except Exception as e:
        # Add more detailed error logging
        import traceback
        error_msg = f"Error in toggle_leadership_section: {str(e)}\n{traceback.format_exc()}"
        return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
    
@require_GET
@login_required
def toggle_other_relationship(request):
    """Show/hide the 'other relationship' input field"""
    try:
        relationship = request.GET.get('value', '')
        appraisal_id = request.GET.get('appraisal_id')
        
        if not appraisal_id:
            return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
            
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check if user has permission to view this appraisal
        if not (appraisal.appraiser.user == request.user or request.user.groups.filter(name='HR').exists()):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # This just returns CSS to show/hide the other field
        if relationship == 'Other':
            return HttpResponse("display: block;")
        else:
            return HttpResponse("display: none;")
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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

class AppraiserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Display and manage list of appraisers with traditional HTML table
    """
    model = Employee
    template_name = 'appraisals/appraiser_list.html'
    permission_required = 'appraisals.view_appraisal'
    context_object_name = 'appraisers'  # Changed to match the template context variable

    current_year = datetime.now().year
    year_range = list(range(current_year - 2, current_year + 4))

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

        context['employee_roles'] = Employee.objects.all()
        
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

        context['default_period'] = AppraisalPeriod.objects.filter(is_default=True).first()
        context['default_deadline'] = self.request.session.get('default_appraisal_deadline')

        
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
            is_active=True,
            is_default=True  # Make this the default period
        )
        
        # If this is the default period, unset any existing default periods
        if period.is_default:
            AppraisalPeriod.objects.filter(is_default=True).update(is_default=False)
            
        period.full_clean()
        period.save()
        
        # If it's an HTMX request, return just the updated message component
        if 'HX-Request' in request.headers:
            return render(request, 'appraisals/includes/period_success_message.html', {
                'default_period': period
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Appraisal period created successfully'
        })
            
    except Exception as e:
        logger.error(f"Error creating appraisal period: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
def set_default_period(request, period_id):
    """Set the default appraisal period using the given period_id"""
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Update the existing period
        period = get_object_or_404(AppraisalPeriod, id=period_id)
        period.start_date = start_date
        period.end_date = end_date
        
        # Make sure this is the default period
        AppraisalPeriod.objects.filter(is_default=True).update(is_default=False)
        period.is_default = True
        period.save()
        
        messages.success(request, f"Period successfully updated! The current default period is: {period.start_date.strftime('%b %d, %Y')} to {period.end_date.strftime('%b %d, %Y')}")
        
        # Always redirect to the list page - this forces a full page reload
        return redirect('appraisals:appraiser_list')
    
    # Handle GET request (likely redirect or return a 405 Method Not Allowed)
    return redirect('appraisals:appraiser_list')
    
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


def get_default_deadline(request):
    """
    Returns the default deadline date based on:
    1. Custom HR-set default deadline date (if set)
    2. Otherwise, uses the end date of the selected appraisal period
    """
    # Get period end date from request (if provided)
    period_end = AppraisalPeriod.objects.first().end_date 
    
    # Get the custom default deadline from session (if set)
    custom_deadline = request.session.get('default_appraisal_deadline')
    
    # Determine which date to use
    if custom_deadline:
        # Use the custom deadline set by HR
        deadline_date = custom_deadline
    elif period_end:
        # Use the end date of the selected period
        deadline_date = period_end
    else:
        # If no custom deadline or period end, use today's date plus 30 days
        from datetime import datetime, timedelta
        deadline_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Return the input with the deadline date
    return HttpResponse(f'''
        <input 
            id="review_period_end" 
            name="review_period_end" 
            type="date" 
            value="{deadline_date}"
            class="mt-1 block w-full pl-10 pr-3 py-2 bg-white text-gray-900 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        >
    ''')

@login_required
@permission_required('appraisals.can_manage_appraisals', raise_exception=True)
def set_default_deadline(request):
    """Set a custom default deadline for appraisals"""
    if request.method == 'POST':
        deadline_date = request.POST.get('deadline_date')
        
        # Store the deadline in Django's session
        if deadline_date:
            # If a date was provided, store it in the session
            try:
                request.session['default_appraisal_deadline'] = deadline_date
                messages.success(request, f"Custom deadline successfully set for {deadline_date}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error setting default deadline: {str(e)}")
                messages.error(request, "Error setting deadline")
        else:
            # If no date was provided, clear any existing deadline
            if 'default_appraisal_deadline' in request.session:
                del request.session['default_appraisal_deadline']
            messages.success(request, "Custom deadline cleared. System will use the end date of the appraisal period.")
    
    # Always redirect to the list page
    return redirect('appraisals:appraiser_list')


def  get_default_period(request):
    # Get the default appraisal period
    default_period = AppraisalPeriod.objects.filter(is_default=True).first()

    if default_period:
        # Check if the period is in the past (end year iss less than current year)
        current_year = datetime.now().year

        if default_period.end_date.year < current_year:
            # Create a new datetime object with the current year

            # Update start date with +1 year
            start_date = default_period.start_date.replace(year=default_period.start_date.year + 1)

            # Update the end date with the current year
            end_date = default_period.end_date.replace(year=current_year)

            # update the period with the new dates
            default_period.start_date = start_date
            default_period.end_date = end_date
            default_period.save()
    
    if default_period:
        # Return JavaScript to select the default period in the dropdown
        script = f"""
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const periodSelect = document.getElementById('period_select');
            if (periodSelect) {{
                // Look for the option with this period ID
                const options = periodSelect.querySelectorAll('option');
                for (const option of options) {{
                    if (option.value === '{default_period.id}') {{
                        option.selected = true;
                        // Trigger a change event to update any dependent fields
                        const event = new Event('change');
                        periodSelect.dispatchEvent(event);
                        break;
                    }}
                }}
            }}
        }});
        </script>
        """
        return HttpResponse(script)
    
    return HttpResponse('')  # Return empty if no default period

    
class AppraiserRoleView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Manage appraiser roles and permissions
    """
    template_name = 'appraisals/appraiser_roles.html'
    permission_required = 'auth.change_group'

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
            
            # Handle draft save vs. full submission
            if self.request.POST.get('save_draft') == 'true':
                self.object.status = 'pending'
            else:
                # If not saving as draft, set status to primary_review
                self.object.status = 'primary_review'
            
            self.object.save()
            
            # Save formsets
            qualification_formset.instance = self.object.employee
            qualification_formset.save()
            
            module_formset.instance = self.object.employee
            module_formset.save()
            
            # Add success message
            msg = 'Form saved as draft successfully.' if self.request.POST.get('save_draft') == 'true' else 'Form submitted successfully and sent for review.'
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
    
@require_POST
@csrf_protect
def save_multiple_fields(request):
    """Batch save multiple fields at once for better performance"""
    try:
        # Check if the data is coming as JSON or form data
        if request.content_type and 'application/json' in request.content_type:
            # Handle JSON data from request.body
            try:
                data = json.loads(request.body)
                fields = data.get('fields', [])
                appraisal_id = data.get('appraisal_id')
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        else:
            # Handle form data from request.POST
            appraisal_id = request.POST.get('appraisal_id')
            
            # For single field updates via standard form submission
            fields = [{
                'field': request.POST.get('field'),
                'section': request.POST.get('section'),
                'value': request.POST.get('value')
            }]
        
        if not appraisal_id:
            return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
        
        # Ensure we have a list of fields to update
        if not fields or not isinstance(fields, list):
            fields = []
            
        # Get the appraisal
        appraisal = Appraisal.objects.get(appraisal_id=appraisal_id)
        
        # Get the current user's employee record (for the appraiser)
        try:
            current_user = request.user.employee
        except AttributeError:
            return JsonResponse({'status': 'error', 'message': 'User has no associated employee record'}, status=403)
        
        # Group fields by section
        section_data = {}
        for field_info in fields:
            section_name = field_info.get('section')
            field = field_info.get('field')
            value = field_info.get('value')
            
            if not section_name or not field:
                continue
                
            if section_name not in section_data:
                section_data[section_name] = {}
            
            section_data[section_name][field] = value
        
        # Update all sections in a single transaction
        with transaction.atomic():
            for section_name, field_values in section_data.items():
                section, created = AppraisalSection.objects.get_or_create(
                    appraisal=appraisal,
                    section_name=section_name,
                    appraiser=current_user
                )
                
                # Update with new values
                data = section.data or {}
                data.update(field_values)
                section.data = data
                section.save()
        
        return JsonResponse({'status': 'success'})
        
    except Appraisal.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appraisal not found'}, status=404)
    except Exception as e:
        # Add more detailed error logging
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in save_multiple_fields: {str(e)}\n{error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
def save_draft(request):
    """Save the appraisal as a draft"""
    if request.method == 'POST':
        appraisal_id = request.POST.get('appraisal_id')
        section = request.POST.get('section')
        
        # First get the appraisal object
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)

        # Get the current user's employee record (assuming the appraiser is saving)
        current_employee = request.user.employee

        # Find or create the appropriate section record
        section_obj, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal, # Pass the appraisal object directly
            section_name=section,
            appraiser=current_employee,
            defaults={'data': {}}
        )

        # Update the section status in the data JSON
        data = section_obj.data or {}
        data['status'] = 'draft'
        section_obj.data = data
        section_obj.save()

        # Return a success message
        return HttpResponse(status=200, content="Section saved as draft successfully.")
    
    return HttpResponse(status=400, content="Invalid request")

@require_POST
@csrf_protect
def save_section_data(request):
    """Save all form data for a specific section at once"""
    try:
        # Parse input data
        appraisal_id = request.POST.get('appraisal_id')
        section = request.POST.get('section')
        is_draft = request.POST.get('is_draft') == 'true'
        
        if not all([appraisal_id, section]):
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        # Get the appraisal object
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check permissions
        if not (appraisal.appraiser.user == request.user or 
                (appraisal.appraiser_secondary and appraisal.appraiser_secondary.user == request.user) or
                request.user.groups.filter(name='HR').exists()):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
        # Get current user's employee record
        current_employee = request.user.employee
        

        #
        # Get or create section object
        section_obj, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name=section,
            # Here saved as primary appraiser even its the secondary appraiser saving
            appraiser=appraisal.appraiser,  # Use primary appraiser
            defaults={'data': {}}
        )
        
        # Extract all the form data for this section
        data = section_obj.data or {}
        section_prefix = section.lower()[0]
        
        # Process all fields that belong to this section
        for key, value in request.POST.items():
            if key.lower().startswith(section_prefix):
                data[key] = value
        
        # Add status info if this is a draft save
        if is_draft:
            data['status'] = 'draft'
        
        # Save the updated data
        section_obj.data = data
        section_obj.save()
        
        return JsonResponse({'status': 'success', 'message': 'Section data saved successfully'})
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in save_section_data: {str(e)}\n{error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
def get_section_data(request):
    """Get saved data for a section"""
    appraisal_id = request.GET.get('appraisal_id')
    section = request.GET.get('section')
    
    if not appraisal_id or not section:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check permissions - Add check for employee/appraisee
        is_appraiser = appraisal.appraiser.user == request.user
        is_secondary_appraiser = appraisal.appraiser_secondary and appraisal.appraiser_secondary.user == request.user
        is_hr = request.user.groups.filter(name='HR').exists()
        is_employee = appraisal.employee.user == request.user
        
        if not (is_appraiser or is_secondary_appraiser or is_hr or is_employee):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # First try to get data filled by the primary appraiser
        try:
            section_obj = AppraisalSection.objects.get(
                appraisal=appraisal,
                section_name=section,
                appraiser=appraisal.appraiser
            )
            return JsonResponse({'data': section_obj.data})
        except AppraisalSection.DoesNotExist:
            # If no data from primary appraiser, check if current user is secondary appraiser
            current_employee = request.user.employee
            if current_employee == appraisal.appraiser_secondary:
                # Check if secondary appraiser has filled any data
                try:
                    section_obj = AppraisalSection.objects.get(
                        appraisal=appraisal,
                        section_name=section,
                        appraiser=current_employee
                    )
                    return JsonResponse({'data': section_obj.data})
                except AppraisalSection.DoesNotExist:
                    return JsonResponse({'data': {}})
            else:
                # No data found for this section
                return JsonResponse({'data': {}})
            
    except Exception as e:
        logger.error(f"Error in get_section_data: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

    
@require_POST
@login_required
@csrf_protect
def update_appraisal_status(request):
    """Update the status of an appraisal based on the current appraiser role"""
    try:
        # Parse the request data
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            appraisal_id = data.get('appraisal_id')
            is_final_submit = data.get('is_final_submit', False)
            appraisee_agrees = data.get('appraisee_agrees', None)
        else:
            appraisal_id = request.POST.get('appraisal_id')
            is_final_submit = request.POST.get('is_final_submit') == 'true'
            appraisee_agrees = request.POST.get('appraisee_agrees')
        
        if not appraisal_id:
            return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
        
        # Get the appraisal
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Get the current user's employee record
        current_employee = request.user.employee
        
        # Determine what status to set based on who is submitting
        new_status = appraisal.status  # Default to keeping current status
        
        if is_final_submit:
            # Primary appraiser submitting
            if appraisal.appraiser == current_employee:
                # Check if this is a reassigned review
                if appraisal.status == 'reassigned_review':
                    # Reassigned appraiser is done, send directly to HR review
                    new_status = 'hr_review'
                    
                    # Log completion of reassigned review
                    section, created = AppraisalSection.objects.get_or_create(
                        appraisal=appraisal,
                        section_name='reassignment_history',
                        appraiser=current_employee
                    )
                    data = section.data or {}
                    data['completed_at'] = timezone.now().isoformat()
                    section.data = data
                    section.save()
                    
                elif appraisal.appraiser_secondary:
                    # If there's a secondary appraiser, move to secondary_review
                    new_status = 'secondary_review'
                else:
                    # No secondary appraiser, send to appraisee for review
                    new_status = 'appraisee_review'
                    
            # Secondary appraiser submitting
            elif appraisal.appraiser_secondary == current_employee:
                # Secondary appraiser is done, send to appraisee for review
                new_status = 'appraisee_review'
                
            # Appraisee submitting after review
            elif appraisal.employee == current_employee and appraisal.status == 'appraisee_review':
                # Check if appraisee agrees or disagrees
                if appraisee_agrees is not None:
                    if appraisee_agrees == 'true' or appraisee_agrees == True:
                        # Appraisee agrees, send to HR for final review
                        new_status = 'hr_review'
                    else:
                        # Appraisee disagrees, mark as disagreed
                        new_status = 'disagreed'
                        
                        # Log the dispute in a section
                        section, created = AppraisalSection.objects.get_or_create(
                            appraisal=appraisal,
                            section_name='dispute',
                            appraiser=current_employee
                        )
                        data = section.data or {}
                        data['disputed_at'] = timezone.now().isoformat()
                        data['reason'] = request.POST.get('dispute_reason', '')
                        section.data = data
                        section.save()
                
            # HR submitting (or other case)
            elif request.user.groups.filter(name=HR_GROUP_NAME).exists():
                current_status = appraisal.status
                
                if current_status in ['hr_review', 'reassigned_review']:
                    # HR finalizing after review
                    new_status = 'completed'
                elif current_status == 'disagreed':
                    # HR handling a disagreement - check if they're assigning a new appraiser
                    new_appraiser_id = request.POST.get('new_appraiser_id')
                    if new_appraiser_id:
                        try:
                            new_appraiser = Employee.objects.get(employee_id=new_appraiser_id)
                            
                            # Store the original appraisers for reference
                            section, created = AppraisalSection.objects.get_or_create(
                                appraisal=appraisal,
                                section_name='dispute_history',
                                appraiser=current_employee
                            )
                            data = section.data or {}
                            
                            # Add the original appraisers to history
                            if 'previous_appraisers' not in data:
                                data['previous_appraisers'] = []
                                
                            data['previous_appraisers'].append({
                                'primary_id': appraisal.appraiser.employee_id,
                                'primary_name': appraisal.appraiser.get_full_name(),
                                'secondary_id': appraisal.appraiser_secondary.employee_id if appraisal.appraiser_secondary else None,
                                'secondary_name': appraisal.appraiser_secondary.get_full_name() if appraisal.appraiser_secondary else None,
                                'reassigned_at': timezone.now().isoformat()
                            })
                            
                            section.data = data
                            section.save()
                            
                            # Assign the new appraiser (making sure they're not the same as before)
                            if (new_appraiser != appraisal.appraiser and 
                                (not appraisal.appraiser_secondary or new_appraiser != appraisal.appraiser_secondary)):
                                appraisal.appraiser = new_appraiser
                                appraisal.appraiser_secondary = None  # Clear secondary appraiser
                                new_status = 'reassigned'  # Mark as reassigned
                            else:
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': 'New appraiser must be different from previous appraisers'
                                }, status=400)
                        except Employee.DoesNotExist:
                            return JsonResponse({
                                'status': 'error', 
                                'message': 'Selected employee not found'
                            }, status=404)
                    else:
                        # HR can override and complete without reassignment
                        if request.POST.get('hr_override') == 'true':
                            new_status = 'completed'
                elif current_status == 'reassigned':
                    # HR has reassigned, now it should go to reassigned_review 
                    new_status = 'reassigned_review'
        
        # Update the appraisal status
        appraisal.status = new_status
        appraisal.save()
        
        # Return the new status and a redirect URL
        return JsonResponse({
            'status': new_status,
            'message': f'Appraisal status updated to {new_status}',
            'redirect_url': reverse('appraisals:form_detail', kwargs={'pk': appraisal_id})
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in update_appraisal_status: {str(e)}\n{error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# temp complete function
@require_POST
@login_required
@csrf_protect
def complete_appraisal(request):
    """Directly change an appraisal's status to completed (for authorized users only)"""
    try:
        # Parse the request data
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            appraisal_id = data.get('appraisal_id')
        else:
            appraisal_id = request.POST.get('appraisal_id')
        
        if not appraisal_id:
            return JsonResponse({'status': 'error', 'message': 'Missing appraisal_id'}, status=400)
        
        # Get the appraisal
        appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
        
        # Check if user has permission to complete appraisals (must be HR)
        if not request.user.groups.filter(name=HR_GROUP_NAME).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Only HR users can complete appraisals directly'
            }, status=403)
        
        # Log the manual completion
        section, created = AppraisalSection.objects.get_or_create(
            appraisal=appraisal,
            section_name='completion_history',
            appraiser=request.user.employee
        )
        
        data = section.data or {}
        data['completed_at'] = timezone.now().isoformat()
        data['completed_by'] = request.user.employee.get_full_name()
        data['previous_status'] = appraisal.status
        data['manually_completed'] = True
        section.data = data
        section.save()
        
        # Update the appraisal status to completed
        appraisal.status = 'completed'
        appraisal.save()
        
        # Return success response with redirect URL
        return JsonResponse({
            'status': 'success',
            'message': 'Appraisal marked as completed',
            'redirect_url': reverse('appraisals:form_detail', kwargs={'pk': appraisal_id})
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in complete_appraisal: {str(e)}\n{error_details}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class AppraiseeWizard(SessionWizardView):
    """
    Wizard view for appraisee to review the appraisal and provide response.
    All sections are read-only except for section E (appraisee's response).
    """
    form_list = [ 
        ('section_b', SectionBForm),  # Read-only
        ('section_c', SectionCForm),  # Read-only
        ('section_d', SectionDForm),  # Read-only
        ('section_e', SectionEForm),  # Editable
    ]
    
    templates = {
        'section_b': 'appraisals/appraisee/section_b_readonly.html',
        'section_c': 'appraisals/appraisee/section_c_readonly.html',
        'section_d': 'appraisals/appraisee/section_d_readonly.html',
        'section_e': 'appraisals/appraisee/section_e_appraisee.html',
    }
    
    def get_template_names(self):
        return [self.templates[self.steps.current]]
    
    def dispatch(self, request, *args, **kwargs):
        # Get the appraisal ID from the URL
        self.appraisal_id = kwargs.get('appraisal_id')
        
        # Get the appraisal object
        self.appraisal = get_object_or_404(Appraisal, appraisal_id=self.appraisal_id)
        
        # Check if the logged-in user is the appraisee
        if request.user.employee != self.appraisal.employee:
            messages.error(request, "You don't have permission to review this appraisal.")
            return redirect('appraisals:list')
            
        # Check if the appraisal is in the correct state
        if self.appraisal.status != 'appraisee_review':
            messages.error(request, "This appraisal is not currently available for your review.")
            return redirect('appraisals:list')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_initial(self, step):
        """Pre-populate forms with existing data from the database"""
        initial = {}
        
        # Get the appraisal sections
        try:
            if step == 'section_b':
                section = AppraisalSection.objects.get(
                    appraisal=self.appraisal,
                    section_name='goals'
                )
                if section.data and 'goals' in section.data:
                    initial['goals'] = section.data.get('goals', [])
                
            elif step == 'section_c':
                section = AppraisalSection.objects.get(
                    appraisal=self.appraisal,
                    section_name='performance'
                )
                if section.data:
                    initial['rating'] = section.data.get('rating', '')
                    initial['comments'] = section.data.get('comments', '')
                
            elif step == 'section_d':
                strengths_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='strengths'
                ).first()
                
                improvements_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='areas_for_improvement'
                ).first()
                
                training_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='training'
                ).first()
                
                if strengths_section and strengths_section.data:
                    initial['strengths'] = strengths_section.data.get('content', '')
                
                if improvements_section and improvements_section.data:
                    initial['areas_for_improvement'] = improvements_section.data.get('content', '')
                
                if training_section and training_section.data:
                    initial['training'] = training_section.data.get('content', '')
                    
            elif step == 'section_e':
                # For section E, check if there's an existing response
                response_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='appraisee_response'
                ).first()
                
                if response_section and response_section.data:
                    initial['agrees'] = response_section.data.get('agrees', True)
                    initial['comments'] = response_section.data.get('comments', '')
        
        except AppraisalSection.DoesNotExist:
            # If section doesn't exist, use empty initial data
            pass
            
        return initial
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        
        # Add appraisal object to the context
        context['appraisal'] = self.appraisal
        
        # Add a flag to indicate this is an appraisee review
        context['is_appraisee_review'] = True
        
        # Add step titles
        context['step_titles'] = {
            'section_b': 'Step 1: Goals & Objectives Review',
            'section_c': 'Step 2: Performance Review',
            'section_d': 'Step 3: Feedback Review',
            'section_e': 'Step 4: Your Response',
        }
        
        # Add section data directly to context so it can be displayed in read-only templates
        if self.steps.current == 'section_b':
            try:
                section = AppraisalSection.objects.get(
                    appraisal=self.appraisal,
                    section_name='goals'
                )
                if section.data:
                    context['goals_data'] = section.data.get('goals', [])
            except AppraisalSection.DoesNotExist:
                context['goals_data'] = []
                
        elif self.steps.current == 'section_c':
            try:
                section = AppraisalSection.objects.get(
                    appraisal=self.appraisal,
                    section_name='performance'
                )
                if section.data:
                    context['performance_data'] = section.data
            except AppraisalSection.DoesNotExist:
                context['performance_data'] = {}
                
        elif self.steps.current == 'section_d':
            feedback_data = {}
            
            try:
                strengths_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='strengths'
                ).first()
                
                if strengths_section and strengths_section.data:
                    feedback_data['strengths'] = strengths_section.data.get('content', '')
            except:
                feedback_data['strengths'] = ''
                
            try:
                improvements_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='areas_for_improvement'
                ).first()
                
                if improvements_section and improvements_section.data:
                    feedback_data['areas_for_improvement'] = improvements_section.data.get('content', '')
            except:
                feedback_data['areas_for_improvement'] = ''
                
            try:
                training_section = AppraisalSection.objects.filter(
                    appraisal=self.appraisal,
                    section_name='training'
                ).first()
                
                if training_section and training_section.data:
                    feedback_data['training'] = training_section.data.get('content', '')
            except:
                feedback_data['training'] = ''
                
            context['feedback_data'] = feedback_data
        
        return context
    
    def done(self, form_list, **kwargs):
        """Process the completed wizard and save data to the database"""
        # Extract the form data - we only need section_e
        section_e_form = None
        for form in form_list:
            if isinstance(form, SectionEForm):
                section_e_form = form
                break
        
        if section_e_form:
            # Extract appraisee's response
            agrees = section_e_form.cleaned_data.get('agrees', True)
            comments = section_e_form.cleaned_data.get('comments', '')
            
            # Save the appraisee's response
            response_section, created = AppraisalSection.objects.get_or_create(
                appraisal=self.appraisal,
                section_name='appraisee_response',
                appraiser=self.request.user.employee
            )
            
            response_data = response_section.data or {}
            response_data['agrees'] = agrees
            response_data['comments'] = comments
            response_data['responded_at'] = timezone.now().isoformat()
            response_section.data = response_data
            response_section.save()
            
            # Update the appraisal status based on agreement
            self.appraisal.status = 'hr_review' if agrees else 'disagreed'
            self.appraisal.save()
            
            messages.success(self.request, "Your response has been submitted successfully.")
        else:
            messages.error(self.request, "Error processing your response.")
            
        return redirect('appraisals:list')
    

@login_required
@require_POST
def save_appraisee_response(request):
    """
    Save the appraisee's response to their appraisal.
    This includes their agreement status, comments, and confirmation details.
    """
    appraisal_id = request.POST.get('appraisal_id')
    is_draft = request.POST.get('is_draft') == 'true'
    is_final_submit = request.POST.get('is_final_submit') == 'true'
    
    # Get the appraisal
    appraisal = get_object_or_404(Appraisal, appraisal_id=appraisal_id)
    
    # Check if user is authorized to respond to this appraisal
    if appraisal.employee.user != request.user:
        return JsonResponse({"success": False, "message": "You are not authorized to respond to this appraisal"}, status=403)
    
    # Check if appraisal is in the right status for a response
    if appraisal.status not in ['reviewed', 'response_pending', 'appraisee_review']:
        return JsonResponse({"success": False, "message": "This appraisal is not currently available for response"}, status=400)
    
    # Collect all data from the form
    data = {
        'r_agreement_status': request.POST.get('r_agreement_status'),
        'r_appraisee_comments': request.POST.get('r_appraisee_comments'),
        'r_response_date': request.POST.get('r_response_date'),
        'r_appraisee_name': request.POST.get('r_appraisee_name'),
        'r_confirmation': 'true' if 'r_confirmation' in request.POST else 'false'
    }
    
    # Save to appraisal data model
    appraisal_data, created = AppraisalSection.objects.update_or_create(
        appraisal=appraisal,
        section_name='response',
        defaults={'data': json.dumps(data)}
    )
    
    # If this is the final submission, update the appraisal status
    if is_final_submit:
        # Check the agreement status to determine the next status
        agreement_status = request.POST.get('r_agreement_status').lower().strip()
        if agreement_status == 'agree' or agreement_status == 'true':
            # If appraisee agrees, mark as completed
            appraisal.status = 'completed'
        else:
            # If appraisee disagrees, send to HR for review
            appraisal.status = 'hr_review'
            
        appraisal.response_date = datetime.now()
        appraisal.save()
        
        # You might want to send notifications here
        
        redirect_url = reverse('appraisals:form_list')  # Use named URL pattern
    else:
        # For drafts, keep the same status
        redirect_url = request.META.get('HTTP_REFERER', reverse('appraisals:form_list'))
    
    return JsonResponse({
        "success": True,
        "message": "Response submitted successfully" if is_final_submit else "Draft saved successfully",
        "redirect_url": redirect_url,
        "is_final": is_final_submit
    })