from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employee
from django.utils import timezone

class Appointment(models.Model):
    type_of_appointment = models.CharField(max_length=50, choices=[
        ('Permanent', 'Permanent'),
        ('Contract', 'Contract'),
        ('Month-to-Month', 'Month-to-Month'),
        ('Daily Rated', 'Daily Rated')
    ])
    first_appointment_govt = models.DateField(null=True, blank=True)
    first_appointment_ubd = models.DateField(null=True, blank=True)
    post = models.CharField(max_length=100)
    faculty_programme = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField()

class Qualification(models.Model):
    degree_diploma = models.CharField(max_length=100)
    university_college = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField()

class Module(models.Model):
    title = models.CharField(max_length=100)
    level = models.CharField(max_length=50)
    language_medium = models.CharField(max_length=50)
    no_of_students = models.IntegerField()
    percentage_jointly_taught = models.FloatField()
    hours_weekly = models.FloatField()

class Membership(models.Model):
    category = models.CharField(max_length=50, choices=[
        ('University Committees', 'University Committees'),
        ('Outside University', 'Outside University')
    ])
    position = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField()

class Appraisal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ]

    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='appraisals'
    )
    appraiser = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='conducted_appraisals',
        null=True,
        blank=True
    )
    date_created = models.DateTimeField(default=timezone.now)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    appointments = models.ManyToManyField(Appointment, blank=True)
    present_post = models.CharField(max_length=100, null=True, blank=True)
    salary_scale_division = models.CharField(max_length=50, null=True, blank=True)
    incremental_date = models.DateField(null=True, blank=True)
    date_of_last_appraisal = models.DateField(null=True, blank=True)
    academic_qualifications_text = models.TextField(
        blank=True,
        help_text="Academic qualifications details"
    )
    current_enrollment = models.TextField(blank=True, null=True)
    modules_taught = models.ManyToManyField(Module, blank=True)
    higher_degree_students_supervised = models.TextField(blank=True, null=True)
    last_research = models.TextField(blank=True, null=True)
    ongoing_research = models.TextField(blank=True, null=True)
    publications = models.TextField(blank=True, null=True)
    attendance = models.TextField(blank=True, null=True)
    conference_papers = models.TextField(blank=True, null=True)
    consultancy_work = models.TextField(blank=True, null=True)
    administrative_posts = models.TextField(blank=True, null=True)
    memberships = models.ManyToManyField(Membership, blank=True)
    participation_within_university = models.TextField(blank=True, null=True)
    participation_outside_university = models.TextField(blank=True, null=True)
    objectives_next_year = models.TextField(blank=True, null=True)
    appraiser_comments = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_created']
        permissions = [
            ("can_view_all_appraisals", "Can view all appraisals"),
            ("can_create_appraisal", "Can create appraisal"),
        ]

    def __str__(self):
        return f"Appraisal for {self.employee.first_name} {self.employee.last_name} ({self.date_created.date()})"

    def clean(self):
        if self.review_period_start and self.review_period_end:
            if self.review_period_start > self.review_period_end:
                raise ValidationError({
                    'review_period_end': 'Review period end date must be after start date.'
                })

        if self.appraiser and self.employee and self.appraiser == self.employee:
            raise ValidationError({
                'appraiser': 'Appraiser cannot be the same as the employee being appraised.'
            })

        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_employee_name(self):
        """Get employee's full name"""
        return self.employee.get_full_name()

    def get_employee_ic_details(self):
        """Get employee's IC details"""
        return f"{self.employee.ic_no} ({self.employee.ic_colour})"

    def get_employee_appointment_type(self):
        """Get employee's appointment type"""
        return self.employee.type_of_appointment

class AppraisalPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        permissions = [
            ("can_manage_periods", "Can manage appraisal periods"),
        ]

    def __str__(self):
        return f"Appraisal Period ({self.start_date} - {self.end_date})"

    def clean(self):
        if not self.start_date or not self.end_date:
            raise ValidationError("Both start date and end date are required")

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date")

        # Check if there's an overlap with other periods
        overlapping = AppraisalPeriod.objects.filter(
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        
        if self.pk:  # If updating existing period
            overlapping = overlapping.exclude(pk=self.pk)
            
        if overlapping.exists():
            raise ValidationError("This period overlaps with an existing period")

        # If trying to activate, check no other active periods
        if self.is_active:
            active_periods = AppraisalPeriod.objects.filter(is_active=True)
            if self.pk:
                active_periods = active_periods.exclude(pk=self.pk)
            if active_periods.exists():
                raise ValidationError("Another period is already active")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class AcademicQualification(models.Model):
    appraisal = models.ForeignKey(
        Appraisal,
        on_delete=models.CASCADE,
        related_name='academic_qualifications'
    )
    degree_diploma = models.CharField(max_length=255)
    university_college = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()

    class Meta:
        ordering = ['-to_date']

    def __str__(self):
        return f"{self.degree_diploma} from {self.university_college}"
