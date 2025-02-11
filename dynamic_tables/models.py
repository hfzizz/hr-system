from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class DynamicTable(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tables')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ("hr_crud_table", "Can perform CRUD operations on tables"),
            ("hr_view_table", "Can view HR tables"),
            ("hr_create_table", "Can create HR tables"),
            ("hr_edit_table", "Can edit HR tables"),
            ("hr_delete_table", "Can delete HR tables"),
            ("hr_manage_permissions", "Can manage HR table permissions"),
        ]

class TableViewPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    table = models.ForeignKey('DynamicTable', on_delete=models.CASCADE)
    view_config = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ('user', 'table')

# Keep existing TableColumn and TableRow models
class TableColumn(models.Model):
    COLUMN_TYPES = (
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('select', 'Selection'),
    )
    
    table = models.ForeignKey(DynamicTable, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    column_type = models.CharField(max_length=20, choices=COLUMN_TYPES)
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['order']

class TableRow(models.Model):
    table = models.ForeignKey(DynamicTable, on_delete=models.CASCADE)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Row {self.id}"