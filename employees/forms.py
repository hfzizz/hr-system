from django import forms
from django.contrib.auth.models import User
from .models import Employee, Qualification, Publication
from django.db import models
from django.forms import  formset_factory, BaseModelFormSet, inlineformset_factory
from django.urls import reverse_lazy


class EmployeeProfileForm(forms.ModelForm):
    employee_id = forms.CharField(
        disabled=True,
        required=False,
    )
    username = forms.CharField(
        max_length=150,
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True
    )
    email = forms.EmailField(required=True)
    appointment_type = forms.ChoiceField(
        choices=Employee.AppointmentType.choices,
        required=True
    )

    class Meta:
        model = Employee
        fields = [
            'employee_id',
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'date_of_birth',
            'gender',
            'hire_date',
            'department',
            'post',
            'salary',
            'employee_status',
            'appointment_type',
            'roles',
            'address',
            'profile_picture',
            'ic_no',
            'ic_colour',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if self.instance:
            exists = Employee.objects.filter(email=email).exclude(pk=self.instance.pk).exists()
            if exists:
                raise forms.ValidationError("This email is already in use.")
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate next employee ID if this is a new employee
        if not self.instance.pk:
            try:
                # Get the highest employee ID using aggregation
                highest_id = Employee.objects.aggregate(
                    max_id=models.Max('employee_id')
                )['max_id']
                
                if highest_id:
                    # Convert to integer and increment
                    try:
                        next_id = int(highest_id) + 1
                    except ValueError:
                        next_id = 1
                else:
                    next_id = 1
                    
                # Format the new ID with leading zeros
                new_id = f'{next_id:04d}'
                self.initial['employee_id'] = new_id
                self.instance.employee_id = new_id
                
            except Exception as e:
                print(f"Error generating employee_id: {e}")
                # Generate a timestamp-based ID as fallback
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                self.initial['employee_id'] = timestamp
                self.instance.employee_id = timestamp

        # Add classes to all fields
        for field_name, field in self.fields.items():
            if field_name != 'employee_id':  # Skip employee_id as it has its own styling
                field.widget.attrs.update({
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
                })

    def clean(self):
        cleaned_data = super().clean()
        print("Form cleaned data:", cleaned_data)  # Debug print
        return cleaned_data

    def is_valid(self):
        valid = super().is_valid()
        if not valid:
            print("Form errors:", self.errors)  # Debug print
        return valid

class ProfileForm(forms.ModelForm):
    # Add User model fields as form fields
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)

    class Meta:
        model = Employee
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'phone_number',
            'date_of_birth',
            'ic_no',
            'ic_colour',
            'gender',
            'address',
            'profile_picture',
            
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        employee = super().save(commit=False)
        
        # Update the related User model fields
        user = employee.user
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.password = self.cleaned_data['password']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            employee.save()
        
        return employee

class QualificationForm(forms.ModelForm):
    class Meta:
        model = Qualification
        fields = [
            'degree_diploma',
            'university_college',
            'from_date',
            'to_date'
        ]
        widgets = {
            'degree_diploma': forms.TextInput(
                attrs={
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6',
                    'placeholder': 'Enter degree or diploma name'
                }
            ),
            'university_college': forms.TextInput(
                attrs={
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6',
                    'placeholder': 'Enter institution name'
                }
            ),
            'from_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
                }
            ),
            'to_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind CSS classes to all fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.DateInput):  # Skip date inputs as they're already styled
                field.widget.attrs.update({
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
                })

class BaseQualificationFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('from_date') and form.cleaned_data.get('to_date'):
                    if form.cleaned_data['from_date'] > form.cleaned_data['to_date']:
                        raise forms.ValidationError('Start date cannot be after end date.')

QualificationFormSet = inlineformset_factory(
    Employee,
    Qualification,
    fields=['degree_diploma', 'university_college', 'from_date', 'to_date'],
    extra=1,
    can_delete=True
)

# Define field mapping for each publication type
PUB_TYPE_FIELDS = {
    "book": ["publisher"],
    "article": ["journal", "volume", "number", "pages"],
    "booklet": ["howpublished", "month"],
    "inbook": ["booktitle", "publisher", "address", "page"],
    "incollection": ["editor", "booktitle", "publisher", "address", "pages"],
    "inproceedings": ["booktitle", "series", "pages", "publisher", "address"],
    "manual": ["organization", "address"],
    "mastersthesis": ["school", "address", "month"],
    "misc": ["howpublished", "note"],
    "phdthesis": ["school", "address", "month"],
    "proceedings": ["editor", "series", "volume", "publisher", "address"],
    "techreport": ["institution", "address", "number", "month"],
    "unpublished": [],
}

class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = ['title', 'author', 'year', 'pub_type', 'additional_fields']
        widgets = {
            'additional_fields': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pub_type'].widget.attrs.update({
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'hx-get': reverse_lazy('employee:load_type_fields_publication'),
            'hx-target': 'next div',
            'hx-trigger': 'change'
        })

# In your views.py or forms.py where the FormSet is defined
PublicationFormSet = inlineformset_factory(
    Employee,
    Publication,
    form=PublicationForm,
    extra=1,
    can_delete=True,
    fields=['title', 'author', 'year', 'pub_type', 'additional_fields']
)

