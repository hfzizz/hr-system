from django import forms
from django.contrib.auth.models import User
from .models import Employee

class EmployeeForm(forms.ModelForm):
    employee_id = forms.CharField(
        disabled=True,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 bg-gray-50',
        })
    )
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

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

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data

    def save(self, commit=True):
        # Create User instance
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Create Employee instance
        employee = super().save(commit=False)
        employee.user = user
        
        if commit:
            employee.save()
            self.save_m2m()
        
        return employee
