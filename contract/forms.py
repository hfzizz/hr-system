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
    contract_type = forms.ChoiceField(
        choices=Contract.CONTRACT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Contract
        fields = [
            'contract_type',
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
            'objectives_next_year',
            'appraiser_comments',
            'achievements_last_contract',
            'achievements_proposal',
            'other_matters',
            'teaching_modules_text',
            'participation_within_text',
            'participation_outside_text',
            'teaching_future_plan',
            'university_committees_text',
            'external_committees_text',
            'fellowships_awards_text',
            'mentorship_text',
            'grad_supervision_text',
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
            'objectives_next_year': forms.Textarea(attrs={'rows': 4}),
            'achievements_last_contract': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'achievements_proposal': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'other_matters': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'}),
            'teaching_documents': forms.FileInput(
                attrs={
                    'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100',
                    'accept': '.pdf,.docx'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['contract_type'].choices = Contract.CONTRACT_TYPE_CHOICES
        self.fields['contract_type'].required = True
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            })

class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = '__all__'  # or specify the fields you need 