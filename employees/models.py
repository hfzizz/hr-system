from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.validators import RegexValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
import os

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
        
    class AppointmentType(models.TextChoices):
        PERMANENT = 'Permanent', _('Permanent')
        CONTRACT = 'Contract', _('Contract')
        MONTH_TO_MONTH = 'Month-to-Month', _('Month-to-Month')
        DAILY_RATED = 'Daily-Rated', _('Daily-Rated')

    employee_id = models.CharField(max_length=10, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=15,
    )
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        blank=True,
        null=True,
    )
    date_of_birth = models.DateField()
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
    post = models.CharField(
        max_length=100,
        help_text=_('Employee position/job title'),
        blank=True,
        null=True
    )
    appointment_type = models.CharField(
        max_length=50,
        choices=AppointmentType.choices,
        null=True,
        blank=True,
        help_text=_('Type of employment appointment')
    )
     # Scholar-related fields
    scholar_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Google Scholar ID")
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
    
    def get_qualifications(self):
        """Get all qualifications for this employee"""
        return Qualification.objects.filter(employee=self)

class Qualification(models.Model):
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='employee_qualifications',
        null=True,
        blank=True
    )
    degree_diploma = models.CharField(max_length=255)
    university_college = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()

    def __str__(self):
        return f"{self.degree_diploma} from {self.university_college}"

    class Meta:
        ordering = ['-from_date']

class Publication(models.Model):
    # Link to Employee
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="publications")

    # Core Publication Details
    title = models.CharField(max_length=500)
    publication_type = models.CharField(
        max_length=50, 
        choices=[
            ("journal", "Journal Article"), 
            ("conference", "Conference Paper"), 
            ("book", "Book"), 
            ("book_chapter", "Book Chapter"), 
            ("thesis", "Thesis"), 
            ("report", "Report"), 
            ("other", "Other"),
        ]
    )
    authors = models.TextField()  # Store as "Author 1, Author 2, Author 3"
    year = models.IntegerField()
    journal_name = models.CharField(max_length=255, blank=True, null=True)  # For journals
    volume = models.CharField(max_length=50, blank=True, null=True)
    issue = models.CharField(max_length=50, blank=True, null=True)
    pages = models.CharField(max_length=50, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)

    # Source & Unique Identifiers
    source_type = models.CharField(
        max_length=20, 
        choices=[
            ("manual", "Manual Entry"), 
            ("scopus", "Scopus"), 
            ("orcid", "ORCID"), 
            ("researcherid", "Researcher ID"), 
            ("googlescholar", "Google Scholar")
        ]
    )
    source_id = models.CharField(max_length=100, blank=True, null=True)  # Stores Scopus ID, ORCID Work ID, etc.
    
    # DOI & URLs
    doi = models.CharField(max_length=100, blank=True, null=True, unique=True)  # Some sources don't have DOIs
    url = models.URLField(blank=True, null=True)  # Link to publication

    # Fetched vs. Manual
    is_fetched = models.BooleanField(default=False)  # True if pulled from API, False if manually entered
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.year})"


def validate_file_size(value):
    filesize = value.size
    
    if filesize > 10 * 1024 * 1024:  # 10MB limit
        raise ValidationError("The maximum file size that can be uploaded is 10MB")

def employee_document_path(instance, filename):
    # Store the original filename for display
    instance.original_filename = filename
    # Get just the filename without any path
    clean_filename = os.path.basename(filename)
    return f'employee_documents/{instance.employee.id}/{clean_filename}'

class Document(models.Model):
    employee = models.ForeignKey(
        'Employee', 
        on_delete=models.CASCADE,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=employee_document_path)
    original_filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.first_name}'s document - {self.title}"

    def save(self, *args, **kwargs):
        if not self.original_filename and self.file:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file:
            try:
                # Check if file exists before trying to delete
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except (FileNotFoundError, ValueError):
                # If file is missing or path is invalid, just log it or pass
                print(f"File not found: {self.file.path}")
                pass
        super().delete(*args, **kwargs)

    @property
    def file_exists(self):
        """Check if the physical file exists"""
        if self.file:
            try:
                return os.path.isfile(self.file.path)
            except (FileNotFoundError, ValueError):
                return False
        return False
