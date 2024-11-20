from django.db import models
from employees.models import Employee
from django.utils import timezone

class Appraisal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='appraisals')
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
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
