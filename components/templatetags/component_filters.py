from django import template

register = template.Library()

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