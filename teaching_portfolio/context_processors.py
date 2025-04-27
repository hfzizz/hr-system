from django.contrib.auth.models import Group

def appraisal_context_processor(request):
    """
    Context processor for appraisal-related data.
    Makes common appraisal data available to all templates.
    """
    context = {
        'is_hr': False,
        'is_appraiser': False,
        'can_manage_appraisals': False
    }

    if request.user.is_authenticated:
        # Check if user is in HR group
        context['is_hr'] = request.user.groups.filter(name='HR').exists()
        
        # Check if user is an appraiser
        context['is_appraiser'] = request.user.groups.filter(name='Appraiser').exists()
        
        # Check appraisal management permissions
        context['can_manage_appraisals'] = request.user.has_perm('appraisals.can_manage_appraisals')

    return context 