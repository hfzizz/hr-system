from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Employee(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    IC_COLOUR_CHOICES = [
        ('Y', 'Yellow'),
        ('P', 'Purple'),
        ('G', 'Green'),
        ('R', 'Red'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('Permanent', 'Permanent'),
        ('Contract', 'Contract'),
        ('Month-to-Month', 'Month-to-Month'),
        ('Daily Rated', 'Daily Rated'),
    ]
    
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )
    employee_id = models.CharField(max_length=10, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    hire_date = models.DateField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    post = models.CharField(max_length=100, null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    employee_status = models.CharField(max_length=50, choices=[('active', 'Active'), ('on_leave', 'On Leave'), ('inactive', 'Inactive')], default='active')
    roles = models.ManyToManyField('auth.Group', blank=True)
    address = models.TextField()
    profile_picture = models.ImageField(upload_to='employee_pics/', blank=True, null=True)
    ic_no = models.CharField(max_length=20, unique=True, verbose_name="IC Number", null=True, blank=True)
    ic_colour = models.CharField(max_length=1, choices=IC_COLOUR_CHOICES, verbose_name="IC Colour", null=True, blank=True)
    type_of_appointment = models.CharField(max_length=50, choices=APPOINTMENT_TYPE_CHOICES, verbose_name="Type of Appointment", null=True, blank=True)
    qualifications = models.ManyToManyField('appraisals.Qualification', blank=True)
    appointments = models.ManyToManyField('appraisals.Appointment', blank=True)
   

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_employee = Employee.objects.order_by('-employee_id').first()
            
            if last_employee:
                last_id = int(last_employee.employee_id[3:])
                new_id = last_id + 1
            else:
                new_id = 1
            
            self.employee_id = f'EMP{new_id:03d}'
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
