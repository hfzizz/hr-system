from django import forms
from django.contrib.auth.models import User, Group
from .models import Employee
from django.db import models

class EmployeeForm(forms.ModelForm):
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
        required=False
    )
    email = forms.EmailField(required=True)

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
            'position',
            'department',
            'salary',
            'employee_status',
            'roles',
            'address',
            'profile_picture'
        ]

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already in use.')
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

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'address',
            'profile_picture'
        ]

    def save(self, commit=True):
        employee = super().save(commit=False)
        if employee.user:
            # Sync user information
            employee.user.first_name = employee.first_name
            employee.user.last_name = employee.last_name
            employee.user.email = employee.email
            employee.user.save()

            # Sync groups with roles
            employee.user.groups.clear()
            for role in employee.roles.all():
                group, created = Group.objects.get_or_create(name=role.name)
                employee.user.groups.add(group)

        if commit:
            employee.save()
        return employee


