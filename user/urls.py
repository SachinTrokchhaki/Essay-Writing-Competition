from django .urls import path
from . import views

app_name = "user"

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('my-essays/', views.my_essays, name='my_essays'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('delete-essay/<int:pk>/', views.delete_essay, name='delete_essay'),
]