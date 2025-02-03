from rest_framework import serializers
from employees.models import Employee
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']

class EmployeeSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 
            'first_name', 'last_name', 'email',
            'phone_number', 'employee_status',
            'department', 'department_name',
            'appointment_type', 'appointment_type_name',
            'date_of_birth'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        print("Serialized data:", data)  # Debug print
        return data 