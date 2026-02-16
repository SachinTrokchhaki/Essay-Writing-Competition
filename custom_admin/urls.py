from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('competitions/', views.competitions, name='competitions'),
    path('essays/', views.essays, name='essays'),
    path('users/', views.users, name='users'),
    path('feedback/', views.feedback, name='feedback'),
]