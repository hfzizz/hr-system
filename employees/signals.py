from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Employee
from django.contrib.auth.models import Group

@receiver(m2m_changed, sender=Employee.roles.through)
def sync_user_groups(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Clear existing groups
        instance.user.groups.clear()

        # Add groups based on roles
        for role in instance.roles.all():
            group, created = Group.objects.get_or_create(name=role.name)
            instance.user.groups.add(group) 