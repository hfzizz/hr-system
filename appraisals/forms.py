from django import forms
from django.forms import inlineformset_factory
from .models import Appraisal, Module, CompletedResearch, OngoingResearch, ConferenceAttendance, ConferencePaper, ConsultancyWork, AdministrativePost, WithinUniversityActivity, OutsideUniversityActivity, UniversityCommitteeMembership, OutsideCommitteeMembership
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
    publications = forms.CharField(
        label="Publications",
        widget=forms.Textarea,
        required=False,
        help_text="List your publications in a standard format"
    )

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
            'ongoing_research',
            'publications',
            'attendance',
            'conference_papers',
            'consultancy_work',
            'administrative_posts',
            'participation_other_activities_university',
            'participation_other_activities_outside',
            'objectives_next_year',
            'appraiser_comments',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'incremental_date_of_present_post': forms.DateInput(attrs={'type': 'date'}),
            'date_of_last_appraisal': forms.DateInput(attrs={'type': 'date'}),
            'current_enrollment_details': forms.Textarea(attrs={'rows': 4}),
            'last_research': forms.Textarea(attrs={'rows': 4}),
            'publications': forms.Textarea(attrs={'help_text': 'List your publications in a standard format'}),
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

class SectionCForm(forms.ModelForm):
    """ General Traits Form """
    class Meta:
        model = Appraisal
        fields = [
        ]

class SectionDForm(forms.ModelForm):
    """ General Traits Form """
    class Meta:
        model = Appraisal
        fields = [
        ]

class SectionEForm(forms.ModelForm):
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

class CompletedResearchForm(forms.ModelForm):
    class Meta:
        model = CompletedResearch
        fields = ['title', 'start_date', 'end_date', 'funding_agency', 'grants']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

CompletedResearchFormSet = inlineformset_factory(
    Appraisal, CompletedResearch, form=CompletedResearchForm,
    extra=1, can_delete=True
)

class OngoingResearchForm(forms.ModelForm):
    class Meta:
        model = OngoingResearch
        fields = ['title', 'start_date', 'end_date', 'funding_agency', 'grants']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

OngoingResearchFormSet = inlineformset_factory(
    Appraisal, OngoingResearch, form=OngoingResearchForm,
    extra=1, can_delete=True
)

class ConferenceAttendanceForm(forms.ModelForm):
    class Meta:
        model = ConferenceAttendance
        fields = ['event_name', 'type', 'date', 'location', 'role', 'details']

ConferenceAttendanceFormSet = inlineformset_factory(
    Appraisal, ConferenceAttendance, form=ConferenceAttendanceForm,
    extra=1, can_delete=True
)

class ConferencePaperForm(forms.ModelForm):
    class Meta:
        model = ConferencePaper
        fields = ['author', 'year', 'title', 'volume', 'pages', 'doi']

ConferencePaperFormSet = inlineformset_factory(
    Appraisal, ConferencePaper, form=ConferencePaperForm,
    extra=1, can_delete=True
)

class ConsultancyWorkForm(forms.ModelForm):
    class Meta:
        model = ConsultancyWork
        fields = ['title', 'company_institute', 'start_date', 'end_date']

ConsultancyWorkFormSet = inlineformset_factory(
    Appraisal, ConsultancyWork, form=ConsultancyWorkForm,
    extra=1, can_delete=True
)

class AdministrativePostForm(forms.ModelForm):
    class Meta:
        model = AdministrativePost
        fields = ['position', 'from_date', 'to_date', 'details']

AdministrativePostFormSet = inlineformset_factory(
    Appraisal, AdministrativePost, form=AdministrativePostForm,
    extra=1, can_delete=True
)

class WithinUniversityActivityForm(forms.ModelForm):
    class Meta:
        model = WithinUniversityActivity
        fields = ['activity', 'role', 'date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

WithinUniversityActivityFormSet = inlineformset_factory(
    Appraisal, WithinUniversityActivity, form=WithinUniversityActivityForm,
    extra=1, can_delete=True
)

class OutsideUniversityActivityForm(forms.ModelForm):
    class Meta:
        model = OutsideUniversityActivity
        fields = ['activity', 'role', 'date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

OutsideUniversityActivityFormSet = inlineformset_factory(
    Appraisal, OutsideUniversityActivity, form=OutsideUniversityActivityForm,
    extra=1, can_delete=True
)

class UniversityCommitteeMembershipForm(forms.ModelForm):
    class Meta:
        model = UniversityCommitteeMembership
        fields = ['committee_name', 'position', 'from_date', 'to_date', 'details']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

UniversityCommitteeMembershipFormSet = inlineformset_factory(
    Appraisal, UniversityCommitteeMembership, form=UniversityCommitteeMembershipForm,
    extra=1, can_delete=True
)

class OutsideCommitteeMembershipForm(forms.ModelForm):
    class Meta:
        model = OutsideCommitteeMembership
        fields = ['organization', 'position', 'from_date', 'to_date', 'details']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

OutsideCommitteeMembershipFormSet = inlineformset_factory(
    Appraisal, OutsideCommitteeMembership, form=OutsideCommitteeMembershipForm,
    extra=1, can_delete=True
)

    