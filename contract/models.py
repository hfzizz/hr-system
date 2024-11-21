from django.db import models
from django.contrib.auth import get_user_model
from django import forms

class FormTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(default="No description provided.")
    is_active = models.BooleanField(default=True)
    requires_employee = models.BooleanField(default=True, help_text="If checked, this form will require employee selection")

    def __str__(self):
        return self.name

class FormField(models.Model):
    FIELD_TYPES = (
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('file', 'File Upload'),
        ('email', 'Email Input'),
        ('url', 'URL Input'),
        ('tel', 'Telephone Input')
    )

    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=400, blank=True)
    choices = models.TextField(blank=True, help_text="For dropdown/radio, separate options with commas")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.template.name} - {self.label}"

class FormSubmission(models.Model):
    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        employee_name = self.employee.first_name if self.employee else "No employee"
        return f"Submission for {self.template.name} - {employee_name}"

class FormResponse(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='responses')
    field = models.ForeignKey(FormField, on_delete=models.CASCADE)
    value = models.TextField()
    file = models.FileField(upload_to='form_uploads/', blank=True, null=True)

    def __str__(self):
        return f"Response to {self.field.label}"

class FormFieldForm(forms.ModelForm):
    class Meta:
        model = FormField
        fields = ['label', 'field_type', 'required', 'help_text', 'choices', 'placeholder']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),}