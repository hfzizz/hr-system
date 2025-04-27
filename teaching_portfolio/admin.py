from django.contrib import admin
from .models import AppraisalPeriod, Appraisal

@admin.register(AppraisalPeriod)
class AppraisalPeriodAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('is_active',)

@admin.register(Appraisal)
class AppraisalAdmin(admin.ModelAdmin):
    list_display = [
        'appraisal_id',  # Add this line
        'employee',
        'review_period_start',  # Changed from 'period'
        'appraiser',
        'date_created',         # Changed from 'created_at'
        'status'
    ]
    readonly_fields = ['appraisal_id']  # Add this line to show in detail view
    list_display_links = ['appraisal_id', 'employee']  # Make ID clickable
    list_filter = ['status', 'review_period_start']
    search_fields = ['appraisal_id', 'employee__user__first_name', 'employee__user__last_name', 'appraiser__user__first_name', 'appraiser__user__last_name']