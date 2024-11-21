from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import Group
from .models import Appraisal
from employees.models import Employee

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
    fields = ['employee', 'appraiser', 'review_period_start', 'review_period_end']
    template_name = 'appraisals/appraisal_assign.html'
    success_url = reverse_lazy('appraisals:appraisal_list')
    permission_required = 'appraisals.add_appraisal'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        try:
            # Try to get the Appraiser group
            appraiser_group = Group.objects.get(name='Appraiser')
            appraisers = Employee.objects.filter(user__groups=appraiser_group)
        except Group.DoesNotExist:
            # If the group doesn't exist, show all employees for now
            appraisers = Employee.objects.all()
            messages.warning(self.request, "Appraiser group not found. Showing all employees.")
        
        if not appraisers.exists():
            messages.warning(self.request, "No employees with Appraiser role found.")
        
        # Update the queryset
        form.fields['appraiser'].queryset = appraisers
        
        # Exclude employees who are already appraisers from the employee field
        form.fields['employee'].queryset = Employee.objects.exclude(
            Q(user__groups__name='Appraiser') | 
            Q(id__in=Appraisal.objects.values_list('employee', flat=True))
        )
        
        return form

    def form_valid(self, form):
        messages.success(self.request, 'Appraisal assignment created successfully.')
        return super().form_valid(form)