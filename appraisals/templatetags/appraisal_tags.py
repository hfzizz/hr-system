from django import template
from django.utils import timezone
from appraisals.models import AppraisalPeriod

register = template.Library()

@register.simple_tag
def is_appraisal_period():
    today = timezone.now().date()
    return AppraisalPeriod.objects.filter(
        is_active=True,
        # start_date__lte=today,
        # end_date__gte=today
    ).exists() 

@register.filter(name='addclass')
def addclass(field, css_class):
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    return field

