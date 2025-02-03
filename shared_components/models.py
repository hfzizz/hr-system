from django.db import models
from django.contrib.contenttypes.models import ContentType

# Create your models here.

class DynamicTableConfig(models.Model):
    name = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.content_type}"

class TableColumn(models.Model):
    DATA_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('choice', 'Choice'),
        ('url', 'URL'),
        ('email', 'Email'),
    ]

    table_config = models.ForeignKey(DynamicTableConfig, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    field_path = models.CharField(max_length=100, help_text="Dot notation path to the field (e.g., 'user.email')")
    is_sortable = models.BooleanField(default=True)
    is_filterable = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.display_name} ({self.data_type})"

class ColumnChoice(models.Model):
    column = models.ForeignKey(TableColumn, on_delete=models.CASCADE, related_name='choices')
    value = models.CharField(max_length=100)
    display_text = models.CharField(max_length=100)
    
    def __str__(self):
        return self.display_text
