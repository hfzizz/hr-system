from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employee, Qualification
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

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
        ordering = ['title']

    def __str__(self):
        return self.title

class Appointment(models.Model):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name='appointment'
    )
    first_post_appointment_govt = models.CharField(max_length=255, null=True, blank=True)
    first_post_appointment_ubd = models.CharField(max_length=255, null=True, blank=True)
    faculty_programme_govt = models.CharField(max_length=255, verbose_name=_('Faculty/Programme'), null=True, blank=True)
    faculty_programme_ubd = models.CharField(max_length=255, verbose_name=_('Faculty/Programme'), null=True, blank=True)
    date_of_from_first_appointment_govt = models.DateField(null=True, blank=True)
    date_of_to_first_appointment_govt = models.DateField(null=True, blank=True)
    date_of_from_first_appointment_ubd = models.DateField(null=True, blank=True)
    date_of_to_first_appointment_ubd = models.DateField(null=True, blank=True)

    def __str__(self):
        employee_name = self.employee.last_name if self.employee else "No Employee"
        return f"{employee_name} ({self.date_of_from_first_appointment_govt} to {self.date_of_to_first_appointment_govt})"

    class Meta:
        ordering = ['-date_of_from_first_appointment_govt']

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

class Publications(models.Model):
    class PublicationType(models.TextChoices):
        JOURNAL = 'JOURNAL', _('Journal Article')
        CONFERENCE = 'CONFERENCE', _('Conference Paper')
        BOOK = 'BOOK', _('Book')
        BOOK_CHAPTER = 'BOOK_CHAPTER', _('Book Chapter')
        TECHNICAL_REPORT = 'TECHNICAL_REPORT', _('Technical Report')
        OTHER = 'OTHER', _('Other')
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='publications'
    )
    external_source = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('SCHOLAR', 'Google Scholar'),
            ('SCOPUS', 'Scopus'),
            ('MANUAL', 'Manually Entered')
        ],
        default='MANUAL',
        help_text=_("Source of publication data")
    )
    last_synced = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Last synchronization with external source")
    )
    # Common fields for all publication types
    title = models.CharField(
        max_length=255,
        help_text=_("Publication title")
    )
    authors = models.TextField(
        help_text=_("Authors (one per line or in BibTeX format)")
    )
    year = models.IntegerField(
        help_text=_("Publication year")
    )
    month = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Publication month")
    )
    publication_type = models.CharField(
        max_length=50,
        choices=PublicationType.choices,
        help_text=_("Type of publication")
    )
    
    # Optional common fields
    abstract = models.TextField(
        blank=True,
        null=True,
        help_text=_("Publication abstract")
    )
    keywords = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Keywords (comma-separated)")
    )
    doi = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Digital Object Identifier")
    )
    url = models.URLField(
        blank=True,
        null=True,
        help_text=_("URL to publication")
    )
    isbn = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("ISBN (for books)")
    )

    # Journal specific fields
    journal_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Name of journal")
    )
    volume = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Volume number")
    )
    issue = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Issue number")
    )
    pages = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Page range (e.g., 123-145)")
    )
    impact_factor = models.FloatField(
        blank=True,
        null=True,
        help_text=_("Journal impact factor")
    )

    # Conference specific fields
    conference_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Conference name")
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Conference location")
    )

    # Book specific fields
    publisher = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Publisher name")
    )
    editor = models.TextField(
        blank=True,
        null=True,
        help_text=_("Editor(s)")
    )
    chapter = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Chapter number/name")
    )
    edition = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Edition number/name")
    )

    # Additional metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    citation_count = models.IntegerField(
        default=0,
        help_text=_("Number of citations")
    )

    class Meta:
        verbose_name = _("Publication")
        verbose_name_plural = _("Publications")
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.title} ({self.year})"

    def clean(self):
        """Validate fields based on publication type"""
        if self.publication_type == self.PublicationType.JOURNAL:
            if not self.journal_name:
                raise ValidationError({
                    'journal_name': _('Journal name is required for journal articles')
                })
        elif self.publication_type == self.PublicationType.CONFERENCE:
            if not self.conference_name:
                raise ValidationError({
                    'conference_name': _('Conference name is required for conference papers')
                })
        elif self.publication_type in [self.PublicationType.BOOK, self.PublicationType.BOOK_CHAPTER]:
            if not self.publisher:
                raise ValidationError({
                    'publisher': _('Publisher is required for books and book chapters')
                })

    def get_citation_format(self, format_type='APA'):
        """Return formatted citation string"""
        # Implementation for different citation formats
        pass

class Appraisal(models.Model):
    appraisal_id = models.AutoField(primary_key=True)
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
        return self.ppost or "Not specified"
    

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


