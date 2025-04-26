from django import template

register = template.Library()

@register.inclusion_tag('components/data_table.html')
def render_data_table(items, columns, table_config=None, empty_message=None):
    # Get only visible columns
    visible_columns = [col for col in columns if col.get('visible', True)]

    return {
        'items': items,
        'columns': columns,
        'visible_columns': visible_columns,
        'table_config': table_config or {},
        'empty_message': empty_message or "No items found."
    }

@register.inclusion_tag('components/table_filters.html')
def render_table_filters(departments=None, posts=None):
    return {
        'departments': departments,
        'posts': posts,
    }

@register.inclusion_tag('components/column_selector.html')
def render_column_selector(columns):
    return {
        'columns': columns
    }

@register.filter
def getattr_filter(obj, attr):
    """
    Gets an attribute of an object dynamically from a string name
    """
    try:
        # First try to get the attribute
        result = getattr(obj, attr)
        # If it's callable (like a method), call it
        if callable(result):
            return result()
        return result
    except (AttributeError, TypeError):
        return ''
