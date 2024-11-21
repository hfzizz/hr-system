from django import forms
from .models import Appraisal
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
            'job_knowledge',
            'work_quality',
            'attendance',
            'communication',
            'teamwork',
            'achievements',
            'areas_for_improvement',
            'comments',
            'goals'
        ]
        widgets = {
            'achievements': forms.Textarea(attrs={'rows': 3}),
            'areas_for_improvement': forms.Textarea(attrs={'rows': 3}),
            'comments': forms.Textarea(attrs={'rows': 3}),
            'goals': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any specific initialization for employee form

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-input rounded-md shadow-sm mt-1 block w-full'}) 