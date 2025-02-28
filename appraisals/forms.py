from django import forms
from django.forms import inlineformset_factory
from .models import Appraisal, Appointment
from employees.models import Employee, Qualification

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
    ic_no = forms.CharField(disabled=True)
    ic_colour = forms.CharField(disabled=True)
    date_of_birth = forms.DateField(disabled=True)

    # Fields from Appointment model (related to Employee)
    first_post_appointment_govt = forms.CharField(disabled=True)
    faculty_programme_govt = forms.CharField(disabled=True)
    date_of_from_first_appointment_govt = forms.DateField(disabled=True)
    date_of_to_first_appointment_govt = forms.DateField(disabled=True)
    first_post_appointment_ubd = forms.CharField(disabled=True)
    faculty_programme_ubd = forms.CharField(disabled=True)
    date_of_from_first_appointment_ubd = forms.DateField(disabled=True)
    date_of_to_first_appointment_ubd = forms.DateField(disabled=True)

    class Meta:
        model = Appraisal
        fields = [
            'employee',
            'appraiser',
            'ic_no',
            'ic_colour',
            'date_of_birth',
            'review_period_start',
            'review_period_end',
            'present_post',
            'salary_scale_division',
            'incremental_date_of_present_post',
            'date_of_last_appraisal',
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any field customization here if needed

class SectionBForm(forms.ModelForm):
    """ General Traits Form """
    class Meta:
        model = Appraisal
        fields = [
        ]

        
        
class AppraisalForm(forms.ModelForm):
    class Meta:
        model = Appraisal
        fields = [
            # 'employee',
            # 'appraiser',
            # 'review_period_start',
            # 'review_period_end',
            # 'post_at_time_of_review',
            # 'salary_scale_division',
            # 'incremental_date',
            # 'date_of_last_appraisal',
            # 'academic_qualifications_text',
            # 'current_enrollment',
            # 'modules_taught',
            # 'higher_degree_students_supervised',
            # 'last_research',
            # 'ongoing_research',
            # 'publications',
            # 'attendance',
            # 'conference_papers',
            # 'consultancy_work',
            # 'administrative_posts',
            # 'memberships',
            # 'participation_within_university',
            # 'participation_outside_university',
            # 'objectives_next_year',
            # 'appraiser_comments',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any field customization here if needed
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class AcademicQualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = ['degree_diploma', 'university_college', 'from_date', 'to_date']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Create inline formset for AcademicQualification
AcademicQualificationFormSet = inlineformset_factory(
    parent_model=Employee,
    model= Qualification,
    form=AcademicQualificationForm,
    extra=1,
    can_delete=True,
    fields=['degree_diploma', 'university_college', 'from_date', 'to_date']
)

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'first_post_appointment_govt',
            'first_post_appointment_ubd',
            'faculty_programme_govt',
            'faculty_programme_ubd',
            'date_of_from_first_appointment_govt',
            'date_of_to_first_appointment_govt',
            'date_of_from_first_appointment_ubd',
            'date_of_to_first_appointment_ubd'
        ]