from django import forms
from django.contrib.auth.models import User, Group
from .models import Employee

class EmployeeForm(forms.ModelForm):
    employee_id = forms.CharField(
        disabled=True,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 bg-gray-50',
        })
    )
    username = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Meta:
        model = Employee
        fields = [
            'employee_id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'date_of_birth',
            'hire_date',
            'position',
            'department',
            'salary',
            'employee_status',
            'roles',
            'address',
            'profile_picture'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'roles': forms.CheckboxSelectMultiple(attrs={
                'class': 'h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate next employee ID if this is a new employee
        if not self.instance.pk:
            try:
                # Get the last valid employee ID
                last_employee = Employee.objects.filter(
                    employee_id__regex=r'^\d+$'  # Match only numbers
                ).order_by('-employee_id').first()

                if last_employee and last_employee.employee_id:
                    # Get the number and increment
                    try:
                        next_id = int(last_employee.employee_id) + 1
                    except ValueError:
                        next_id = 1
                else:
                    next_id = 1

                self.initial['employee_id'] = f'{next_id:04d}'  # Format as 0001, 0002, etc.
            except Exception as e:
                print(f"Error generating employee_id: {e}")
                self.initial['employee_id'] = '0001'  # Fallback value

        # Add classes to all fields
        for field in self.fields:
            if field != 'employee_id':  # Skip employee_id as it has its own styling
                self.fields[field].widget.attrs.update({
                    'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6'
                })

        # If this is an existing employee, pre-select their roles
        if self.instance and self.instance.pk:
            # Set initial values for roles
            self.initial['roles'] = [role.id for role in self.instance.roles.all()]
            self.fields['roles'].initial = self.instance.roles.all()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

    def save(self, commit=True):
        employee = super().save(commit=False)
        
        if employee.user:
            # Update user information
            employee.user.first_name = self.cleaned_data['first_name']
            employee.user.last_name = self.cleaned_data['last_name']
            employee.user.email = self.cleaned_data['email']
            employee.user.save()

            # Sync groups with roles
            employee.user.groups.clear()
            for role in self.cleaned_data['roles']:
                group, created = Group.objects.get_or_create(name=role.name)
                employee.user.groups.add(group)

        if commit:
            employee.save()
            self.save_m2m()  # Save many-to-many relationships
            
        return employee

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


