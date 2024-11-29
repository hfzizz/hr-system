from django.db import models
from django.utils import timezone
from employees.models import Employee
from appraisals.models import Module, Membership

class Contract(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    # Personal Details (from Employee model)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    ic_no = models.CharField(max_length=20, null=True, blank=True)
    ic_colour = models.CharField(max_length=1, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    department = models.ForeignKey('employees.Department', on_delete=models.SET_NULL, null=True, blank=True)
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contracts')
    submission_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Fields from Appraisal model
    present_post = models.CharField(max_length=100, null=True, blank=True)
    salary_scale_division = models.CharField(max_length=50, null=True, blank=True)
    incremental_date = models.DateField(null=True, blank=True)
    date_of_last_appraisal = models.DateField(null=True, blank=True)
    academic_qualifications_text = models.TextField(blank=True, null=True)
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
        ordering = ['-submission_date']

    def __str__(self):
        return f"Contract Renewal - {self.employee.get_full_name()} ({self.submission_date.date()})"