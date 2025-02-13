from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employee, AppointmentType, Qualification, Department
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Appointment(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='appointment',
        null=True,
        blank=True
    )
    type_of_appointment = models.ForeignKey(
        AppointmentType,
        on_delete=models.PROTECT,
        related_name='appointments'
    )
    first_appointment_govt = models.DateField(null=True, blank=True)
    first_appointment_ubd = models.DateField(null=True, blank=True)
    faculty_programme = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='appointments',
        verbose_name=_('Faculty/Department')
    )
    from_date = models.DateField()
    to_date = models.DateField()

    def __str__(self):
        employee_name = self.employee.last_name if self.employee else "No Employee"
        return f"{self.type_of_appointment.name} - {employee_name} ({self.from_date} to {self.to_date})"

    class Meta:
        ordering = ['-from_date']

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
    last_modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_appraisals'
    )
    last_modified_date = models.DateTimeField(auto_now=True)
    
    # Keep these fields but rename them to clarify they're snapshots
    appointments_at_time_of_review = models.ManyToManyField('Appointment', blank=True)
    post_at_time_of_review = models.CharField(max_length=100, null=True, blank=True)
    
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
        # If this is a new appraisal, populate the snapshot fields from employee
        if not self.pk:  # Check if this is a new instance
            self.post_at_time_of_review = self.employee.post
        
        super().save(*args, **kwargs)
        
        # Need to handle M2M relationships after save
        if not self.pk:
            for appointment in self.employee.appointments.all():
                self.appointments_at_time_of_review.add(appointment)

    def get_employee_appointment_type(self):
        """Returns the employee's appointment type or a default message."""
        try:
            # Assuming the field in Employee model is 'appointment_type'
            if hasattr(self.employee, 'appointment_type'):
                return self.employee.appointment_type.name
            return "Not specified"
        except AttributeError:
            return "Not specified"

    def get_employee_name(self):
        """Returns the employee's full name."""
        return self.employee.get_full_name() if self.employee else "Not assigned"

    def get_employee_ic_details(self):
        """Returns the employee's IC details."""
        try:
            return self.employee.ic_no or "Not provided"
        except AttributeError:
            return "Not provided"

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
