from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='getattr')
def getattr_filter(obj, attr):
    """
    Gets an attribute of an object dynamically from a string name.
    Supports nested attributes using dot notation (e.g., 'user.email').
    """
    try:
        # Handle nested attributes (e.g., 'user.email')
        if '.' in attr:
            attrs = attr.split('.')
            value = obj
            for attr_name in attrs:
                value = getattr(value, attr_name)
            return value
        # Handle direct attributes
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return ''  # Return empty string if attribute doesn't exist 