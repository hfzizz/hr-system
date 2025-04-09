from django import template
import math

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='cos')
def cosine(value):
    try:
        return math.cos(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter(name='sin')
def sine(value):
    try:
        return math.sin(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter(name='divide')
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter(name='filter_status')
def filter_status(status_data, status):
    """Get count for a specific status"""
    for item in status_data:
        if item['employee_status'] == status:
            return item['count']
    return 0

@register.filter
def subtract(value, arg):
    return float(value) - float(arg)

@register.filter
def status_color(status):
    colors = {
        'active': '#4ade80',    # green
        'on_leave': '#fbbf24',  # yellow
        'inactive': '#f87171'   # red
    }
    return colors.get(status, '#e5e7eb')  # default to gray 