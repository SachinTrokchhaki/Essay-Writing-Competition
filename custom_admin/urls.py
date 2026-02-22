from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    
    # Root URL - this is what you're missing!
    path('', views.admin_root, name='root'),
    
    # Auth
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Competitions
    path('competitions/', views.competitions, name='competitions'),
    path('competitions/add/', views.competition_add, name='competition_add'),
    path('competitions/<int:pk>/edit/', views.competition_edit, name='competition_edit'),
    path('competitions/<int:pk>/delete/', views.competition_delete, name='competition_delete'),
    
    # Essays
    path('essays/', views.essays, name='essays'),
    path('essays/<int:pk>/', views.essay_detail, name='essay_detail'),
    path('essays/<int:pk>/edit/', views.essay_edit, name='essay_edit'),
    path('essays/<int:pk>/delete/', views.essay_delete, name='essay_delete'),
    path('essays/<int:pk>/review/', views.essay_review, name='essay_review'),
    
    # Export URLs
    path('essays/export/pdf/', views.export_essays_pdf, name='export_essays_pdf'),
    path('essays/export/csv/', views.export_essays_csv, name='export_essays_csv'),
    path('essays/<int:pk>/export/pdf/', views.export_essay_detail_pdf, name='export_essay_detail_pdf'),
    
    # Users
    path('users/', views.users, name='users'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    
    # Feedback
    path('feedback/', views.feedback, name='feedback'),
    path('feedback/<int:pk>/', views.feedback_detail, name='feedback_detail'),
    path('feedback/<int:pk>/reply/', views.feedback_reply, name='feedback_reply'),
    
    #ml linear regression
    path('ml/dashboard/', views.ml_dashboard, name='ml_dashboard'),
    path('ml/train/', views.train_model, name='train_model'),
    path('ml/results/', views.view_model_results, name='model_results'),
    path('ml/predict/<int:pk>/', views.predict_essay, name='predict_essay'),
]