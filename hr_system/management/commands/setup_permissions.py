from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from employees.models import Employee  # Update with the correct import for Employee model

class Command(BaseCommand):
    help = 'Setup HR group and permissions'

    def handle(self, *args, **kwargs):
        # Create or get HR group
        hr_group, created = Group.objects.get_or_create(name='HR')

        # Create permission for Employee model (add, change, delete)
        content_type = ContentType.objects.get_for_model(Employee)
        permission, created = Permission.objects.get_or_create(
            codename='can_manage_employees',
            name='Can manage employees',
            content_type=content_type
        )

        # Add permission to HR group
        hr_group.permissions.add(permission)

        # Create the 'hr_user' if it doesn't exist
        user, created = User.objects.get_or_create(username='hr_user', defaults={'password': 'admin'})

        if created:
            self.stdout.write(self.style.SUCCESS('User "hr_user" created successfully'))

        # Add HR group to the user
        user.groups.add(hr_group)

        self.stdout.write(self.style.SUCCESS('HR group and permissions setup complete'))
