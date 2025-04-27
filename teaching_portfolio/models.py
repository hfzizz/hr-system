from django.db import models
from django.contrib.auth.models import User

class TeachingPortfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Teaching Philosophy
    teaching_philosophy_full = models.TextField(blank=True)
    teaching_philosophy_summary = models.TextField(blank=True)

    # Strategies, Objectives, Methodology
    learning_outcome_full = models.TextField(blank=True)
    learning_outcome_summary = models.TextField(blank=True)
    instructional_methodology_full = models.TextField(blank=True)
    instructional_methodology_summary = models.TextField(blank=True)
    other_means_to_enhance_learning_full = models.TextField(blank=True)
    other_means_to_enhance_learning_summary = models.TextField(blank=True)

    # Teaching History - Other Teaching
    other_teaching_full = models.TextField(blank=True)

    # Teaching Performance Indicators
    academic_leadership_full = models.TextField(blank=True)
    academic_leadership_summary = models.TextField(blank=True)
    contribution_teaching_materials_full = models.TextField(blank=True)
    contribution_teaching_materials_summary = models.TextField(blank=True)

    # Future Plan
    future_teaching_goals_full = models.TextField(blank=True)
    future_teaching_goals_summary = models.TextField(blank=True)
    future_steps_improve_teaching_full = models.TextField(blank=True)
    future_steps_improve_teaching_summary = models.TextField(blank=True)

    parsed_pdf_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Teaching Portfolio for {self.user.username}"

class TeachingModule(models.Model):
    portfolio = models.ForeignKey(TeachingPortfolio, on_delete=models.CASCADE, related_name='modules')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_modules')
    module_code = models.CharField(max_length=20, verbose_name="Module Code")
    module_title = models.CharField(max_length=200, verbose_name="Module Title")
    academic_year = models.CharField(max_length=20, verbose_name="Academic Year")
    semester = models.CharField(max_length=20, verbose_name="Semester")
    level = models.CharField(max_length=50, verbose_name="Level", blank=True)
    number_of_students = models.PositiveIntegerField(verbose_name="Number of Students", blank=True, null=True)
    role = models.CharField(max_length=100, verbose_name="Role", blank=True)
    description = models.TextField(verbose_name="Module Description", blank=True)
    hours_weekly = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    language_medium = models.CharField(max_length=100, blank=True)
    student_count = models.PositiveIntegerField(blank=True, null=True)
    joint_teaching_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.module_code} - {self.module_title} ({self.academic_year})"
