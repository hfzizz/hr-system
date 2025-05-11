from django.urls import path
from .views import teaching_portfolio_form, parse_pdf, summarize_text_view

app_name = 'teaching_portfolio'

urlpatterns = [
    path('list/', teaching_portfolio_form, name='list'),
    path('parse_pdf/', parse_pdf, name='parse_pdf'),
    path('summarize/', summarize_text_view, name='summarize_text'),
]
