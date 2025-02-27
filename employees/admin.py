from django.contrib import admin
from .models import Employee, Department, AppointmentType

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'first_name', 'last_name', 'department']
    list_filter = ['department', 'employee_status', 'appointment_type']
    search_fields = ['first_name', 'last_name', 'employee_id']

@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']