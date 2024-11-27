from django.db import models
from django.core.exceptions import ValidationError
from employees.models import Employee
from django.utils import timezone

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
    
    # Performance Ratings (1-5 scale)
    job_knowledge = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True)
    work_quality = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True)
    attendance = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True)
    communication = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True)
    teamwork = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True, blank=True)
    
    # Comments
    achievements = models.TextField(blank=True, default="")
    areas_for_improvement = models.TextField(blank=True, default="")
    comments = models.TextField(blank=True, default="")
    
    # Goals
    goals = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ['-date_created']
        permissions = [
            ("can_view_all_appraisals", "Can view all appraisals"),
            ("can_create_appraisal", "Can create appraisal"),
        ]

    def __str__(self):
        return f"Appraisal for {self.employee.first_name} {self.employee.last_name} ({self.date_created.date()})"

    def clean(self):
        # Validate review period dates
        if self.review_period_start and self.review_period_end:
            if self.review_period_start > self.review_period_end:
                raise ValidationError({
                    'review_period_end': 'Review period end date must be after start date.'
                })

        # Validate that appraiser is not the same as employee
        if self.appraiser and self.employee and self.appraiser == self.employee:
            raise ValidationError({
                'appraiser': 'Appraiser cannot be the same as the employee being appraised.'
            })

        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def calculate_average_rating(self):
        ratings = [
            self.job_knowledge,
            self.work_quality,
            self.attendance,
            self.communication,
            self.teamwork
        ]
        valid_ratings = [r for r in ratings if r is not None]
        return sum(valid_ratings) / len(valid_ratings) if valid_ratings else None

    @property
    def is_complete(self):
        return self.status == 'completed'

    @property
    def can_be_edited(self):
        return self.status != 'completed'

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
