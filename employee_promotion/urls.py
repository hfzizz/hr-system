from django.urls import path
from .views import PromotionFormView

app_name = 'employee_promotion'

urlpatterns = [
    path('list/', PromotionFormView.as_view(), name='list'),
]
