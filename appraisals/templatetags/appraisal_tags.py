from django import template
from django.utils import timezone
from appraisals.models import AppraisalPeriod

register = template.Library()

@register.simple_tag
def is_appraisal_period():
    today = timezone.now().date()
    return AppraisalPeriod.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).exists() 