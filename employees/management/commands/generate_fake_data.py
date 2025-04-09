from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employees.models import Department, Employee, Qualification
from django.utils import timezone
from datetime import timedelta
import random
from faker import Faker

# Create Faker instance with required providers
fake = Faker()

# List of universities for realistic data
UNIVERSITIES = [
    'Universiti Brunei Darussalam',
    'National University of Singapore',
    'University of Malaya',
    'University of Oxford',
    'Harvard University',
    'Massachusetts Institute of Technology',
    'Stanford University',
    'University of Cambridge'
]

class Command(BaseCommand):
    help = 'Generates fake data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of employees to create'
        )

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write('Creating fake data...')

        # Create Departments
        departments = [
            'SDS',
            'FOS',
            'FASS',
            'UBDSBE',
            'IHS'
        ]
        dept_objects = []
        for dept_name in departments:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={'description': fake.text()}
            )
            dept_objects.append(dept)
            if created:
                self.stdout.write(f'Created department: {dept_name}')

      
        # Create Employees with Users
        for i in range(count):  # Create specified number of employees
            # Create User
            username = fake.user_name()
            email = fake.email()
            password = 'testpass123'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )

            # Create Employee
            dob = fake.date_of_birth(minimum_age=22, maximum_age=65)
            hire_date = fake.date_between(start_date='-5y', end_date='today')

            appointment_types = [
                'Permanent',
                'Contract',
                'Month-to-Month',
                'Daily-Rated'
            ]

            employee = Employee.objects.create(
                user=user,
                first_name=user.first_name,
                last_name=user.last_name,
                email=email,
                phone_number=fake.phone_number()[:15],
                gender=random.choice(['M', 'F']),
                date_of_birth=dob,
                hire_date=hire_date,
                department=random.choice(dept_objects),
                salary=random.uniform(2000, 8000),
                employee_status='active',
                address=fake.address(),
                ic_no=fake.unique.random_number(digits=8),
                ic_colour=random.choice(['Y', 'P', 'G', 'R']),
                post=fake.job(),
                appointment_type=random.choice(appointment_types)
            )

            # Create Qualifications
            num_qualifications = random.randint(1, 3)
            for _ in range(num_qualifications):
                from_date = fake.date_between(start_date='-10y', end_date='-5y')
                Qualification.objects.create(
                    employee=employee,
                    degree_diploma=random.choice(['Bachelor', 'Master', 'PhD']) + ' in ' + fake.word().title(),
                    university_college=random.choice(UNIVERSITIES),  # Use predefined list
                    from_date=from_date,
                    to_date=from_date + timedelta(days=random.randint(365*2, 365*4))
                )

            self.stdout.write(f'Created employee: {employee.get_full_name()}')

        self.stdout.write(self.style.SUCCESS('Successfully created fake data'))