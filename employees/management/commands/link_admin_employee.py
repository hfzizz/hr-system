from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employees.models import Employee, Department
from django.utils import timezone

class Command(BaseCommand):
    help = 'Links existing admin user to a new employee record'

    def handle(self, *args, **options):
        try:
            # Get existing admin user
            user = User.objects.get(username='admin')
            
            # Get or create a department
            dept, _ = Department.objects.get_or_create(
                name='Administration',
                defaults={'description': 'Administration Department'}
            )

            # Create employee record
            employee = Employee.objects.create(
                user=user,
                employee_id='SU001',  # First employee
                first_name=user.first_name or 'Admin',
                last_name=user.last_name or 'User',
                email=user.email,
                phone_number='1234567890',
                gender='M',
                date_of_birth=timezone.now().date(),
                hire_date=timezone.now().date(),
                department=dept,
                salary=5000,
                employee_status='active',
                address='UBD',
                ic_no='12345678',
                ic_colour='Y',
                post='Administrator'
            )

            self.stdout.write(self.style.SUCCESS(f'Successfully linked admin user to employee record'))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error linking admin: {str(e)}'))