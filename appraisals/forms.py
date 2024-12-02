from django import forms
from django.forms import inlineformset_factory
from .models import Appraisal, AcademicQualification
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

class AppraisalForm(forms.ModelForm):
    class Meta:
        model = Appraisal
        fields = [
            'employee',
            'appraiser',
            'review_period_start',
            'review_period_end',
            'post_at_time_of_review',
            'salary_scale_division',
            'incremental_date',
            'date_of_last_appraisal',
            'academic_qualifications_text',
            'current_enrollment',
            'modules_taught',
            'higher_degree_students_supervised',
            'last_research',
            'ongoing_research',
            'publications',
            'attendance',
            'conference_papers',
            'consultancy_work',
            'administrative_posts',
            'memberships',
            'participation_within_university',
            'participation_outside_university',
            'objectives_next_year',
            'appraiser_comments',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any field customization here if needed
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class AcademicQualificationForm(forms.ModelForm):
    class Meta:
        model = AcademicQualification
        fields = ['degree_diploma', 'university_college', 'from_date', 'to_date']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Create inline formset for AcademicQualification
AcademicQualificationFormSet = inlineformset_factory(
    parent_model=Appraisal,
    model=AcademicQualification,
    form=AcademicQualificationForm,
    extra=1,
    can_delete=True,
    fields=['degree_diploma', 'university_college', 'from_date', 'to_date']
)