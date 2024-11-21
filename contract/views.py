from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import FormTemplate, FormField, FormSubmission, FormResponse
from .forms import FormTemplateForm, FormFieldForm, DynamicFormRenderer
from django.db import models
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.messages.views import SuccessMessageMixin
from employees.models import Employee

class FormTemplateListView(LoginRequiredMixin, ListView):
    model = FormTemplate
    template_name = 'contract/template_list.html'
    context_object_name = 'templates'

class FormTemplateCreateView(LoginRequiredMixin, CreateView):
    model = FormTemplate
    form_class = FormTemplateForm
    template_name = 'contract/template_form.html'
    success_url = reverse_lazy('contract_renewal:template_list')

class FormTemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = FormTemplate
    success_url = reverse_lazy('contract_renewal:template_list')
    success_message = 'Template deleted successfully.'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)

class FormTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = FormTemplate
    template_name = 'contract_renewal/template_form.html'
    form_class = FormTemplateForm
    
    def get_success_url(self):
        return reverse_lazy('contract:template_list')

@login_required
def manage_fields(request, template_id):
    template = get_object_or_404(FormTemplate, id=template_id)
    
    if request.method == 'POST':
        form = FormFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.template = template
            last_order = template.fields.aggregate(models.Max('order'))['order__max']
            field.order = (last_order or 0) + 1
            field.save()
            request.session['temp_message'] = f'Field "{field.label}" added successfully!'
            return redirect('contract:manage_fields', template_id=template_id)
        else:
            messages.error(request, f'Form validation failed: {form.errors}', extra_tags='safe')
    else:
        form = FormFieldForm()

    fields = template.fields.all().order_by('order')
    
    temp_message = request.session.pop('temp_message', None)
    if temp_message:
        messages.success(request, temp_message, extra_tags='safe')
    
    context = {
        'template': template,
        'form': form,
        'fields': fields,
    }
    return render(request, 'contract/manage_fields.html', context)

@login_required
def fill_form(request, template_id):
    template = get_object_or_404(FormTemplate, id=template_id)
    form_renderer = DynamicFormRenderer(template)
    
    if request.method == 'POST':
        form = form_renderer.get_form(data=request.POST, files=request.FILES)
        if form.is_valid():
            submission = FormSubmission.objects.create(
                template=template,
                submitted_by=request.user,
                employee=form.cleaned_data.get('employee') if template.requires_employee else None
            )
            
            for field in template.fields.all():
                field_key = f'field_{field.id}'
                if field.field_type == 'file':
                    file = request.FILES.get(field_key)
                    if file:
                        FormResponse.objects.create(
                            submission=submission,
                            field=field,
                            file=file
                        )
                else:
                    value = form.cleaned_data.get(field_key)
                    if value is not None:
                        FormResponse.objects.create(
                            submission=submission,
                            field=field,
                            value=str(value)
                        )
            
            messages.success(request, 'Form submitted successfully.')
            return redirect('contract_renewal:submission_list')  
    else:
        form = form_renderer.get_form()
    
    return render(request, 'contract_renewal/fill_form.html', {
        'template': template,
        'form': form
    })

class SubmissionListView(LoginRequiredMixin, ListView):
    model = FormSubmission
    template_name = 'contract_renewal/submission_list.html'
    context_object_name = 'submissions'

@login_required
def delete_field(request, field_id):
    field = get_object_or_404(FormField, id=field_id)
    template_id = field.template.id
    
    if request.method == 'POST':
        field.delete()
        # Simply add the success message
        messages.success(request, 'Field deleted successfully!', extra_tags='safe')
        return HttpResponseRedirect(reverse('contract_renewal:manage_fields', args=[template_id]))
    
    return redirect('contract_renewal:manage_fields', template_id=template_id)

@login_required
def edit_field(request, field_id):
    field = get_object_or_404(FormField, id=field_id)
    template_id = field.template.id
    
    if request.method == 'POST':
        form = FormFieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, f'Field "{field.label}" updated successfully!', extra_tags='safe')
        else:
            messages.error(request, f'Form validation failed: {form.errors}', extra_tags='safe')
    
    return redirect('contract_renewal:manage_fields', template_id=template_id)

@login_required
def update_template_settings(request, template_id):
    template = get_object_or_404(FormTemplate, id=template_id)
    
    if request.method == 'POST':
        template.requires_employee = request.POST.get('requires_employee') == 'on'
        template.save()
        messages.success(request, 'Template settings updated successfully!')
    
    return redirect('contract_renewal:manage_fields', template_id=template_id)

@login_required
def get_employee_data(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
        data = {
            'employee_id': employee.employee_id,
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email,
            'phone_number': employee.phone_number,
            'position': employee.position,
            'address': employee.address,
            'date_of_birth': employee.date_of_birth.isoformat() if employee.date_of_birth else None,
            'hire_date': employee.hire_date.isoformat() if employee.hire_date else None,
            'salary': str(employee.salary) if employee.salary else None,
            'department': employee.department.name if employee.department else None,
        }
        return JsonResponse(data)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)

@login_required
def delete_submission(request, pk):
    """
    View to handle deletion of form submissions.
    Only allows POST requests for security and only by authenticated users.
    """
    if request.method == 'POST':
        submission = get_object_or_404(FormSubmission, pk=pk)
        
        # Optional: Add permission check
        if submission.submitted_by == request.user or request.user.is_staff:
            # Delete associated files if any
            for response in submission.responses.all():
                if response.file:
                    response.file.delete()
            
            # Delete the submission
            submission.delete()
            messages.success(request, 'Submission deleted successfully.')
        else:
            messages.error(request, 'You do not have permission to delete this submission.')
            
    return redirect('contract_renewal:submission_list')