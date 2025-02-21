from django.urls import path
from . import views

app_name = 'roles'

urlpatterns = [
    path('', views.RoleListView.as_view(), name='list'),
    path('create/', views.RoleCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.RoleUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.RoleDeleteView.as_view(), name='delete'),
] 