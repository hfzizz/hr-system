from django import forms
from .models import FormTemplate, FormField
from employees.models import Employee

class FormTemplateForm(forms.ModelForm):
    class Meta:
        model = FormTemplate
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FormFieldForm(forms.ModelForm):
    class Meta:
        model = FormField
        fields = ['label', 'field_type', 'required', 'placeholder', 'help_text', 'choices']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-control'}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DynamicFormRenderer:
    def __init__(self, template):
        self.template = template

    def get_form(self, data=None, files=None, employee=None):
        form_fields = {}
        
        # Employee Selection Field
        if self.template.requires_employee:
            form_fields['employee'] = forms.ModelChoiceField(
                queryset=Employee.objects.filter(employee_status='active'),
                label='Select Employee',
                required=True,
                widget=forms.Select(attrs={
                    'class': 'form-control',
                    'id': 'employee-select',
                    'placeholder': 'Select an employee',
                    'hx-get': '/api/employees/',
                    'hx-trigger': 'change',
                    'hx-target': '#employee-details'
                }),
                empty_label="Select an employee"
            )

            # Add permanent employee information fields
            form_fields['employee_id'] = forms.CharField(
                label='Employee ID',
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-id'
                })
            )
            
            form_fields['first_name'] = forms.CharField(
                label='First Name',
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-first-name'
                })
            )
            
            form_fields['last_name'] = forms.CharField(
                label='Last Name',
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-last-name'
                })
            )
            
            form_fields['email'] = forms.EmailField(
                label='Email',
                required=False,
                widget=forms.EmailInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-email'
                })
            )
            
            form_fields['phone_number'] = forms.CharField(
                label='Phone Number',
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-phone'
                })
            )
            
            form_fields['position'] = forms.CharField(
                label='Position',
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'id': 'employee-position'
                })
            )

        # Add the dynamic form fields
        for field in self.template.fields.all():
            field_key = f'field_{field.id}'
            field_attrs = {
                'class': 'form-control',
                'placeholder': field.placeholder,
                'id': f'dynamic-{field_key}'
            }

            if field.field_type == 'text':
                form_fields[field_key] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.TextInput(attrs=field_attrs)
                )
            elif field.field_type == 'textarea':
                form_fields[field_key] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': field.placeholder})
                )
            elif field.field_type == 'number':
                form_fields[field_key] = forms.IntegerField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': field.placeholder})
                )
            elif field.field_type == 'date':
                form_fields[field_key] = forms.DateField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                )
            elif field.field_type in ['select', 'radio']:
                choices = [(choice.strip(), choice.strip()) for choice in field.choices.split(',') if choice.strip()]
                if field.field_type == 'select':
                    widget = forms.Select(attrs={'class': 'form-control'})
                else:
                    widget = forms.RadioSelect(attrs={'class': 'form-check-input'})
                form_fields[field_key] = forms.ChoiceField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    choices=choices,
                    widget=widget
                )
            elif field.field_type == 'checkbox':
                form_fields[field_key] = forms.BooleanField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                )
            elif field.field_type == 'file':
                form_fields[field_key] = forms.FileField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.FileInput(attrs={'class': 'form-control'})
                )
            elif field.field_type == 'email':
                form_fields[field_key] = forms.EmailField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': field.placeholder})
                )
            elif field.field_type == 'url':
                form_fields[field_key] = forms.URLField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': field.placeholder})
                )
            elif field.field_type == 'tel':
                form_fields[field_key] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    help_text=field.help_text,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'type': 'tel',
                        'placeholder': field.placeholder
                    })
                )               
                