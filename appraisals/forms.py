from django import forms
from django.forms import inlineformset_factory
from .models import Appraisal, Module
from employees.models import Employee

class HRAppraisalForm(forms.ModelForm):
    class Meta:
        model = Appraisal
        fields = [
            'employee',
            'appraiser',
            'review_period_start',
            'review_period_end',
            'status'
        ]
        widgets = {
            'review_period_start': forms.DateInput(attrs={'type': 'date'}),
            'review_period_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any specific initialization for HR form

class SectionAForm(forms.ModelForm):
    """ Personal Details Form """
    # Fields from Employee model
    ic_no = forms.CharField(disabled=True, required=False)
    ic_colour = forms.CharField(disabled=True, required=False)
    date_of_birth = forms.DateField(disabled=True, required=False)
    present_post = forms.CharField(disabled=True, required=False)
    
    # Override employee and appraiser to display names
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.HiddenInput(),
        disabled=True
    )
    appraiser = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        widget=forms.HiddenInput(),
        disabled=True
    )

    # Add these fields directly to the form
    first_post_govt = forms.CharField(max_length=255, required=False, label="First Post (Government)")
    faculty_programme_govt = forms.CharField(max_length=255, required=False, label="Faculty/Programme (Government)")
    date_from_govt = forms.DateField(required=False, label="From Date (Government)")
    date_to_govt = forms.DateField(required=False, label="To Date (Government)")
    
    first_post_ubd = forms.CharField(max_length=255, required=False, label="First Post (UBD)")
    faculty_programme_ubd = forms.CharField(max_length=255, required=False, label="Faculty/Programme (UBD)")
    date_from_ubd = forms.DateField(required=False, label="From Date (UBD)")
    date_to_ubd = forms.DateField(required=False, label="To Date (UBD)")

    class Meta:
        model = Appraisal
        fields = [
            'employee', 'appraiser',
            'ic_no', 'ic_colour', 'date_of_birth',
            'first_post_govt', 'faculty_programme_govt', 'date_from_govt', 'date_to_govt',
            'first_post_ubd', 'faculty_programme_ubd', 'date_from_ubd', 'date_to_ubd',
            'present_post', 'salary_scale_division',
            'incremental_date_of_present_post', 'date_of_last_appraisal',
            'current_enrollment_details',
            'higher_degree_students_supervised',
            'last_research',
            'ongoing_research'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'incremental_date_of_present_post': forms.DateInput(attrs={'type': 'date'}),
            'date_of_last_appraisal': forms.DateInput(attrs={'type': 'date'}),
            'current_enrollment_details': forms.Textarea(attrs={'rows': 4}),
            'last_research': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the actual employee and appraiser instances
        if self.instance and self.instance.employee:
            employee = self.instance.employee
            # Set initial values from Employee model
            self.initial.update({
                'employee': employee,
                'ic_no': employee.ic_no,
                'ic_colour': employee.ic_colour,
                'date_of_birth': employee.date_of_birth,
                'present_post': employee.post,  # Assuming position field exists in Employee model
            })
            
            # Set the fields as initial data
            self.fields['employee'].initial = employee
            self.fields['ic_no'].initial = employee.ic_no
            self.fields['ic_colour'].initial = employee.ic_colour
            self.fields['date_of_birth'].initial = employee.date_of_birth
            self.fields['present_post'].initial = employee.post
        
        if self.instance and self.instance.appraiser:
            self.initial['appraiser'] = self.instance.appraiser
            self.fields['appraiser'].initial = self.instance.appraiser

        self.qualification_formset = None
        self.appointment_formset = None

        # Make employee and appraiser readonly
        self.fields['employee'].widget.attrs['readonly'] = True
        self.fields['appraiser'].widget.attrs['readonly'] = True
        
     
class SectionBForm(forms.ModelForm):
    """ General Traits Form """
    class Meta:
        model = Appraisal
        fields = [
        ]


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = [
            'code',
            'title',
            'level',
            'languageMedium',
            'no_of_students',
            'percentage_jointly_taught',
            'hrs_weekly'
        ]

ModuleFormSet = inlineformset_factory(
    parent_model=Employee,
    model=Module,
    form=ModuleForm,
    extra=1,
    can_delete=True,
    fields=[
        'code',
        'title',
        'level',
        'languageMedium',
        'no_of_students',
        'percentage_jointly_taught',
        'hrs_weekly'
    ]
)


    