from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employee, Publication, Qualification
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

class AppraisalPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False, null=True, blank=True)
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Appraisal(models.Model):
    appraisal_id = models.AutoField(primary_key=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('primary_review', 'Under Primary Appraiser Review'),
        ('secondary_review', 'Under Secondary Appraiser Review'),
        ('pending_response', 'Pending Response'),
        ('disagreed', 'Disagreed'),
        ('reassigned', 'Reassigned'),
        ('reassigned_review', 'Under Reassigned Appraiser Review'),
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
    appraiser_secondary = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name='secondary_appraisals',
        null=True,
        blank=True
    )
    date_created = models.DateTimeField(default=timezone.now)
    appraisal_year = models.IntegerField(default=now().year)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    salary_scale_division = models.CharField(max_length=50, null=True, blank=True)
    incremental_date_of_present_post = models.DateField(null=True, blank=True)
    date_of_last_appraisal = models.DateField(null=True, blank=True)
    present_post = models.CharField(max_length=50, null=True, blank=True)
    current_enrollment_details = models.TextField(max_length=255, blank=True, null=True)
    higher_degree_students_supervised = models.TextField(blank=True, null=True)
    last_research = models.TextField(blank=True, null=True)
    ongoing_research = models.TextField(blank=True, null=True)
    publications = models.TextField(blank=True, null=True) # temporary
    attendance = models.TextField(blank=True, null=True)
    conference_papers = models.TextField(blank=True, null=True)
    consultancy_work = models.TextField(blank=True, null=True)
    administrative_posts = models.TextField(blank=True, null=True)
    participation_other_activities_university = models.TextField(blank=True, null=True)
    participation_other_activities_outside = models.TextField(blank=True, null=True)
    objectives_next_year = models.TextField(blank=True, null=True)
    appraiser_comments = models.TextField(blank=True, null=True)
    last_modified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='modified_appraisals'
    )    
    last_modified_date = models.DateTimeField(auto_now=True)
    appraisal_period_start=models.DateField(null=True, blank=True)
    appraisal_period_end=models.DateField(null=True, blank=True)
    review_period_start = models.DateField(
        help_text=_("Start date of review period"),
        null=True,
        blank=True
    )
    review_period_end = models.DateField(
        help_text=_("End date of review period"),
        null=True,
        blank=True
    )

    # Add these new fields for appointments
    first_post_govt = models.CharField(max_length=255, null=True, blank=True)
    faculty_programme_govt = models.CharField(max_length=255, null=True, blank=True)
    date_from_govt = models.DateField(null=True, blank=True)
    date_to_govt = models.DateField(null=True, blank=True)
    
    first_post_ubd = models.CharField(max_length=255, null=True, blank=True)
    faculty_programme_ubd = models.CharField(max_length=255, null=True, blank=True)
    date_from_ubd = models.DateField(null=True, blank=True)
    date_to_ubd = models.DateField(null=True, blank=True)

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
        
        if self.appraiser_secondary and self.employee and self.appraiser_secondary == self.employee:
            raise ValidationError({
                'appraiser_secondary': 'Secondary appraiser cannot be the same as the employee being appraised.'
            })
        
        if self.appraiser and self.appraiser_secondary and self.appraiser == self.appraiser_secondary:
            raise ValidationError({
                'appraiser_secondary': 'Secondary appraiser cannot be the same as the primary appraiser.'
            })

        super().clean()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_employee_appointment_type(self):
        """Returns the employee's appointment type or a default message."""
        try:
            # Assuming the field in Employee model is 'appointment_type'
            if hasattr(self.employee, 'appointment_type'):
                return self.employee.appointment_type
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
        
    def get_appraisal_period_display(self):
        """Returns formatted appraisal period string."""
        if self.appraisal_period_start and self.appraisal_period_end:
            return f"{self.appraisal_period_start.strftime('%d %b %Y')} - {self.appraisal_period_end.strftime('%d %b %Y')}"
        return 'Not Set'

    def get_review_period_display(self):
        """Returns formatted review period string."""
        if self.review_period_start and self.review_period_end:
            return f"{self.review_period_start.strftime('%d %b %Y')} - {self.review_period_end.strftime('%d %b %Y')}"
        return 'Not Set'

    def get_date_created_display(self):
        """Returns formatted creation date."""
        return self.date_created.strftime('%d %b %Y') if self.date_created else '-'

    def get_department_display(self):
        """Returns department name with proper null handling."""
        if self.employee and self.employee.department:
            return self.employee.department.name
        return 'Not Assigned'
    
    def get_date_of_last_appraisal(self):
        """Returns the date of the last appraisal if available."""
        last_appraisal = Appraisal.objects.filter(employee=self.employee).exclude(pk=self.pk).order_by('-date_created').first()
        return last_appraisal.date_created.date() if last_appraisal else None

    def get_present_post(self):
        """Returns the present post of the employee."""
        return self.employee.post or "Not specified"

    def get_latest_3_appraisals(self):
        """Returns the last three appraisals for the employee."""
        return Appraisal.objects.filter(employee=self.employee).order_by('-date_created')[:3]

class Module(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='modules'
    )
    code = models.CharField(max_length=20, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    level = models.CharField(max_length=20, null=True, blank=True)
    languageMedium = models.CharField(max_length=20, null=True, blank=True)
    no_of_students = models.IntegerField(null=True, blank=True)
    percentage_jointly_taught = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Percentage if jointly taught (0-100)")
    )
    hrs_weekly = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['code']  # Changed from incorrect field to 'code'
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f"{self.code} - {self.title}"
    
class AppraisalPublication(models.Model):
    appraisal = models.ForeignKey(Appraisal, on_delete=models.CASCADE, related_name="appraisal_publications")
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="appraisal_entries")
     # Snapshot Fields
    title = models.CharField(max_length=500)
    year = models.IntegerField()  # This is the publication year, copied from Publication

    date_added = models.DateTimeField(auto_now_add=True)

    def appraisal_year(self):
        return self.appraisal.appraisal_year  # Get the appraisal year

    def save(self, *args, **kwargs):
        if not self.year:  # Only set year if it's not already provided
            self.year = self.appraisal_year # Copy the publication year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.appraisal.appraisal_year} - {self.title}"

class Membership(models.Model):
    class CommitteeType(models.TextChoices):
        UNIVERSITY = 'UNIVERSITY', _('University Committees')
        EXTERNAL = 'EXTERNAL', _('Outside University')

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='memberships',
        blank=True,
        null=True
    )
    committee_type = models.CharField(
        max_length=20,
        choices=CommitteeType.choices,
        help_text=_("Type of committee membership"),
        null=True,
        blank=True
    )
    committee_name = models.CharField(
        max_length=255,
        help_text=_("Name of the committee"),
        null=True,
        blank=True
    )
    position = models.CharField(
        max_length=100,
        help_text=_("Position held in the committee"),
        null=True,
        blank=True
    )
    
    from_date = models.DateField(
        help_text=_("Start date of membership"),
        null=True,
        blank=True
    )
    to_date = models.DateField(
        help_text=_("End date of membership"),
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Committee Membership")
        verbose_name_plural = _("Committee Memberships")
        ordering = ['-from_date']

    def __str__(self):
        return f"{self.get_committee_type_display()} - {self.committee_name} ({self.position})"

    def clean(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError({
                'to_date': _('End date must be after start date.')
            })
        
class AppraisalSection(models.Model):
    """Stores section-specific data for appraisals"""
    appraisal = models.ForeignKey(Appraisal, on_delete=models.CASCADE, related_name='sections')
    section_name = models.CharField(max_length=50)  # e.g., 'B1', 'B2', etc.
    data = models.JSONField(default=dict, blank=True)  # Stores all field values for this section
    appraiser = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='appraisal_sections', null=True, blank=True)
    
    class Meta:
        unique_together = ('appraisal', 'section_name', 'appraiser')
        
    def __str__(self):
        return f"Section {self.section_name} for Appraisal {self.appraisal.appraisal_id} by {self.appraiser.name}"