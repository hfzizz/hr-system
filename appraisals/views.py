from django.views.generic import ListView, CreateView
from .models import Appraisal

class AppraisalListView(ListView):
    model = Appraisal
    template_name = 'appraisal_list.html'
    context_object_name = 'appraisals'

class AppraisalCreateView(CreateView):
    model = Appraisal
    fields = ['employee', 'rating', 'review', 'date']
    template_name = 'appraisal_form.html'
    success_url = '/appraisals/'  # Redirect to a success page after form submission