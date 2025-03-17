from django.db import migrations
import uuid
from django.utils import timezone

def generate_contract_ids(apps, schema_editor):
    Contract = apps.get_model('contract', 'Contract')
    for contract in Contract.objects.all():
        if not contract.contract_id:
            # Get the year from submission date or use current year
            year = contract.submission_date.year if contract.submission_date else timezone.now().year
            
            # Get employee ID or use 'TEMP'
            employee_id = 'TEMP'
            if contract.employee:
                employee = contract.employee
                employee_id = getattr(employee, 'employee_id', 'TEMP')
            
            # Generate random suffix
            random_suffix = uuid.uuid4().hex[:4].upper()
            
            # Create contract ID
            contract.contract_id = f"CR-{year}-{employee_id}-{random_suffix}"
            contract.save(update_fields=['contract_id'])

class Migration(migrations.Migration):

    dependencies = [
        ('contract', '0011_contract_contract_id'),  # Replace with your previous migration
    ]

    operations = [
        migrations.RunPython(generate_contract_ids),
    ]