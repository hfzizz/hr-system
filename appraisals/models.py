from django.db import models
from employees.models import Employee

class Appraisal(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    performance_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1 to 5 scale
    feedback = models.TextField()
    appraisal_date = models.DateField()
    comments = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Appraisal for {self.employee.first_name} {self.employee.last_name} ({self.review_period_start} to {self.review_period_end})"
