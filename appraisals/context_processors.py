def hr_context(request):
    return {
        'is_hr': request.user.groups.filter(name='HR').exists() if request.user.is_authenticated else False
    } 