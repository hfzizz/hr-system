from django.contrib.contenttypes.models import ContentType
from .models import DynamicTableConfig, TableColumn

class DynamicTableMixin:
    table_config_name = None
    default_columns = []  # Move default columns to specific views for better reusability

    def get_table_config(self):
        if not self.table_config_name:
            raise ValueError("table_config_name must be set")

        content_type = ContentType.objects.get_for_model(self.model)
        try:
            return DynamicTableConfig.objects.get(
                name=self.table_config_name,
                content_type=content_type
            )
        except DynamicTableConfig.DoesNotExist:
            # Create default configuration
            table_config = DynamicTableConfig.objects.create(
                name=self.table_config_name,
                content_type=content_type,
                is_active=True
            )
            
            # Create default columns
            self._create_default_columns(table_config)
            return table_config

    def _create_default_columns(self, table_config):
        """Override this method to define default columns for your model"""
        if self.default_columns:
            for column_data in self.default_columns:
                TableColumn.objects.create(
                    table_config=table_config,
                    **column_data
                )

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
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'table_columns': table_config.columns.filter(is_visible=True),
            'api_url': self.get_api_url(),
        })
        return context 