from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Appraisal
from .forms import AppraisalForm

class AppraisalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Appraisal
    template_name = 'appraisals/appraisal_list.html'
    context_object_name = 'appraisals'
    permission_required = 'appraisals.view_appraisal'

    def get_queryset(self):
        if self.request.user.has_perm('appraisals.can_view_all_appraisals'):
            return Appraisal.objects.all()
        return Appraisal.objects.filter(employee__user=self.request.user)

class AppraisalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Appraisal
    template_name = 'appraisals/appraisal_detail.html'
    permission_required = 'appraisals.view_appraisal'

class AppraisalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Appraisal
    form_class = AppraisalForm
    template_name = 'appraisals/appraisal_form.html'
    success_url = reverse_lazy('appraisals:appraisal_list')
    permission_required = 'appraisals.add_appraisal'

    def form_valid(self, form):
        form.instance.appraiser = self.request.user.employee
        messages.success(self.request, 'Appraisal created successfully.')
        return super().form_valid(form)

class AppraisalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Appraisal
    form_class = AppraisalForm
    template_name = 'appraisals/appraisal_form.html'
    success_url = reverse_lazy('appraisals:appraisal_list')
    permission_required = 'appraisals.change_appraisal'

    def form_valid(self, form):
        messages.success(self.request, 'Appraisal updated successfully.')
        return super().form_valid(form)