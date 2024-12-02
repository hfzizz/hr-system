from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.validators import RegexValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Employee(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHER = 'O', _('Other')
        NOT_SPECIFIED = 'N', _('Prefer not to say')
    
    class ICColour(models.TextChoices):
        YELLOW = 'Y', _('Yellow')
        PURPLE = 'P', _('Purple')
        GREEN = 'G', _('Green')
        RED = 'R', _('Red')
    
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ON_LEAVE = 'on_leave', _('On Leave')
        INACTIVE = 'inactive', _('Inactive')

    employee_id = models.CharField(max_length=10, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=15,
        help_text=_('Contact phone number')
    )
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        blank=True,
        null=True,
        help_text=_('Employee gender')
    )
    date_of_birth = models.DateField(help_text=_('Date of birth'))
    hire_date = models.DateField(help_text=_('Date of hiring'))
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='employees'
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Employee salary')
    )
    employee_status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    roles = models.ManyToManyField('auth.Group', blank=True)
    address = models.TextField()
    profile_picture = models.ImageField(
        upload_to='employee_pics/', 
        blank=True, 
        null=True
    )
    ic_no = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name=_("IC Number"), 
        null=True, 
        blank=True
    )
    ic_colour = models.CharField(
        max_length=1,
        choices=ICColour.choices,
        verbose_name=_("IC Colour"),
        null=True,
        blank=True
    )
    qualifications = models.ManyToManyField(
        'Qualification', 
        blank=True,
        related_name='employees'
    )
    post = models.CharField(
        max_length=100,
        help_text=_('Employee position/job title'),
        blank=True,
        null=True
    )
    appointment_type = models.ForeignKey(
        'AppointmentType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text=_('Type of employment appointment')
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['email']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['ic_no']),
        ]

    def clean(self):
        if self.date_of_birth and self.hire_date:
            if self.date_of_birth > self.hire_date:
                raise ValidationError(_('Date of birth cannot be after hire date'))

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None

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
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class AppointmentType(models.Model):
    APPOINTMENT_CHOICES = [
        ('Permanent', 'Permanent'),
        ('Contract', 'Contract'),
        ('Month-to-Month', 'Month-to-Month'),
        ('Daily-Rated', 'Daily-Rated')
    ]

    name = models.CharField(
        max_length=50,
        unique=True,
        choices=APPOINTMENT_CHOICES
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Qualification(models.Model):
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='employee_qualifications',
        null=True, 
        blank=True
    )
    degree_diploma = models.CharField(max_length=200)
    university_college = models.CharField(max_length=200)
    from_date = models.DateField()
    to_date = models.DateField()

    def __str__(self):
        return f"{self.degree_diploma} from {self.university_college}"

    class Meta:
        ordering = ['-from_date']
