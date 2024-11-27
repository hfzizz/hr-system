from django.contrib import admin
from .models import AppraisalPeriod

@admin.register(AppraisalPeriod)
class AppraisalPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('is_active',)
