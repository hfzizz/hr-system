from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class PromotionFormView(LoginRequiredMixin, TemplateView):
    template_name = 'employee_promotion/list.html'