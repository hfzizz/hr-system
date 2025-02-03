from django.shortcuts import render
from rest_framework import viewsets
from employees.models import Employee
from .serializers import EmployeeSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response

# Create your views here.

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.select_related('user', 'department', 'appointment_type', 'appointment').all()
    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['department', 'employee_status', 'appointment_type']
    search_fields = ['employee_id', 'user__first_name', 'user__last_name', 'user__email']
    ordering_fields = [
        'employee_id', 
        'user__first_name', 
        'user__last_name', 
        'user__email', 
        'department__name', 
        'appointment_type__name'
    ]
    ordering = ['employee_id']

    def list(self, request, *args, **kwargs):
        print("Request received:", request.GET)  # Debug print
        queryset = self.filter_queryset(self.get_queryset())
        print("Queryset count:", queryset.count())  # Debug print
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            print("Response data:", response.data)  # Debug print
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
