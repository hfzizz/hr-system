from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet

app_name = 'api'  # This is important for the namespace

router = DefaultRouter()
router.register('employees', EmployeeViewSet, basename='employee')

urlpatterns = router.urls 