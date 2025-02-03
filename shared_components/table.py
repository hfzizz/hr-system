from django.contrib.contenttypes.models import ContentType
from django.db import models

class DynamicTableConfig(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'content_type')

class TableColumn(models.Model):
    DATA_TYPES = (
        ('string', 'String'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('object', 'Object'),
    )

    table_config = models.ForeignKey(DynamicTableConfig, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=255)  # Database field name
    display_name = models.CharField(max_length=255)  # User-friendly name
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    field_path = models.CharField(max_length=255)  # For nested object access
    order = models.IntegerField(default=0)
    is_sortable = models.BooleanField(default=True)
    is_filterable = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']

class DynamicTableMixin:
    table_config_name = None
    
    def get_table_config(self):
        if not self.table_config_name:
            raise ValueError("table_config_name must be set")
            
        content_type = ContentType.objects.get_for_model(self.model)
        config, created = DynamicTableConfig.objects.get_or_create(
            name=self.table_config_name,
            content_type=content_type
        )
        
        if created:
            self._create_default_columns(config)
            
        return config
    
    def _create_default_columns(self, config):
        """Override this method to define default columns for your model"""
        pass
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply sorting
        sort_by = self.request.GET.get('sort')
        if sort_by:
            direction = '-' if sort_by.startswith('-') else ''
            field = sort_by.lstrip('-')
            if self.get_table_config().columns.filter(name=field, is_sortable=True).exists():
                queryset = queryset.order_by(f"{direction}{field}")
        
        # Apply filtering
        filters = {}
        for param, value in self.request.GET.items():
            if param.startswith('filter_'):
                field = param.replace('filter_', '')
                if self.get_table_config().columns.filter(name=field, is_filterable=True).exists():
                    filters[field] = value
        
        if filters:
            queryset = queryset.filter(**filters)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_config = self.get_table_config()
        
        context.update({
            'table_config': table_config,
            'content_type_id': table_config.content_type_id,
            'table_columns': table_config.columns.filter(is_visible=True),
            'api_url': self.get_api_url(),
        })
        
        return context
    
    def get_api_url(self):
        """Override this method to provide the API endpoint for table operations"""
        return None 