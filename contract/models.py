from django.db import models
from django.utils import timezone
from employees.models import Employee
from appraisals.models import Module, Membership
import os
from django.core.exceptions import ValidationError

class Contract(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent_back', 'Sent Back to Employee'),
        ('smt_review', 'Currently under SMT Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    CONTRACT_TYPE_CHOICES = [
        ('RENEWAL_3', 'Renewal of contract (3 years)'),
        ('EXTENSION_1', 'Extension of current contract (1 year)'),
        ('LOCAL_RENEWAL', 'New/Renewal of contract for local staff'),
        ('OTHER', 'Other'),
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
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Contract Status'
    )
    
    # Fields from Appraisal model
    present_post = models.CharField(max_length=100, null=True, blank=True)
    salary_scale_division = models.CharField(max_length=50, null=True, blank=True)
    incremental_date = models.DateField(null=True, blank=True)
    date_of_last_appraisal = models.DateField(null=True, blank=True)
    academic_qualifications_text = models.TextField(blank=True, null=True)
    current_enrollment = models.TextField(blank=True, null=True)
    modules_taught = models.ManyToManyField(Module, blank=True)
    higher_degree_students_supervised = models.TextField(blank=True, null=True)
    last_research = models.JSONField(blank=True, null=True)
    ongoing_research = models.JSONField(blank=True, null=True)
    publications = models.JSONField(blank=True, null=True)
    attendance = models.TextField(blank=True, null=True)
    conference_papers = models.JSONField(blank=True, null=True)
    consultancy_work = models.JSONField(blank=True, null=True)
    administrative_posts = models.TextField(blank=True, null=True)
    memberships = models.ManyToManyField(Membership, blank=True)
    participation_within_text = models.TextField(blank=True, null=True)
    participation_outside_text = models.TextField(blank=True, null=True)
    objectives_next_year = models.TextField(blank=True, null=True)
    appraiser_comments = models.TextField(blank=True, null=True)
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        verbose_name='Type of contract applied',
        default='RENEWAL_3'
    )
    teaching_modules_text = models.TextField(blank=True, null=True)
    teaching_future_plan = models.TextField(
        verbose_name="Teaching Future Plan",
        blank=True,
        null=True
    )
    
    # Achievement Section
    achievements_last_contract = models.TextField(
        verbose_name="What have you achieved in the last contract for Teaching / Research / Administrative Duties?",
        blank=True
    )
    achievements_proposal = models.TextField(
        verbose_name="What do you propose to undertake and achieve if your contract is renewed?",
        blank=True
    )
    
    # Others Section
    other_matters = models.TextField(
        verbose_name="Any other matters you wish to highlight?",
        blank=True
    )

    # Store teaching documents as binary data
    teaching_documents = models.BinaryField(null=True, blank=True)
    teaching_documents_name = models.CharField(max_length=255, null=True, blank=True)  # To store the original filename

    university_committees_text = models.TextField(blank=True, null=True)
    external_committees_text = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submission_date']

    def __str__(self):
        return f"Contract Renewal - {self.employee.get_full_name()} ({self.submission_date.date()})"

    def clean(self):
        if self.teaching_documents:
            ext = os.path.splitext(self.teaching_documents_name)[1]
            valid_extensions = ['.pdf', '.docx']
            if ext.lower() not in valid_extensions:
                raise ValidationError('Only PDF and DOCX files are allowed.')

class ContractRenewalStatus(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    enabled_date = models.DateTimeField(auto_now=True)
    contract_count = models.IntegerField(default=1)

    class Meta:
        verbose_name_plural = "Contract Renewal Statuses"

class ContractNotification(models.Model):
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    contract = models.ForeignKey('Contract', on_delete=models.CASCADE, null=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Contract Notification for {self.employee.get_full_name()} ({self.created_at.date()})"

class AdministrativePosition(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='administrative_positions')
    title = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title