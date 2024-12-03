from django import forms
from .models import Contract
from employees.models import Employee

class ContractRenewalForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        empty_label="Select Employee",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    incremental_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_of_last_appraisal = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Contract
        fields = [
            'employee',
            'present_post',
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
            'achievements_last_contract',
            'achievements_proposal',
            'other_matters',
        ]
        widgets = {
            'academic_qualifications_text': forms.Textarea(attrs={'rows': 4}),
            'current_enrollment': forms.Textarea(attrs={'rows': 4}),
            'higher_degree_students_supervised': forms.Textarea(attrs={'rows': 4}),
            'last_research': forms.Textarea(attrs={'rows': 4}),
            'ongoing_research': forms.Textarea(attrs={'rows': 4}),
            'publications': forms.Textarea(attrs={'rows': 4}),
            'attendance': forms.Textarea(attrs={'rows': 4}),
            'conference_papers': forms.Textarea(attrs={'rows': 4}),
            'consultancy_work': forms.Textarea(attrs={'rows': 4}),
            'administrative_posts': forms.Textarea(attrs={'rows': 4}),
            'participation_within_university': forms.Textarea(attrs={'rows': 4}),
            'participation_outside_university': forms.Textarea(attrs={'rows': 4}),
            'objectives_next_year': forms.Textarea(attrs={'rows': 4}),
            'achievements_last_contract': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'achievements_proposal': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'other_matters': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }) 