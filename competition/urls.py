# competition/urls.py
from django.urls import path
from . import views

app_name = 'competition'

urlpatterns = [
    # Existing URLs...
    path('<int:pk>/', views.competition_detail, name='detail'),
    path('<int:pk>/submit/', views.submit_essay, name='submit_essay'),
    
    path('save-draft/', views.save_draft, name='save_draft'),
    path('submit-final/', views.submit_final_essay, name='submit_final'),
    path('get-draft/<int:pk>/', views.get_draft, name='get_draft'),
    path('get-draft-content/<int:pk>/', views.get_draft_content, name='get_draft_content'),
    
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('leaderboard/<int:pk>/', views.leaderboard, name='leaderboard_detail'),
    
    # path('my-results/', views.my_results, name='my_results'),
    # path('result/<int:pk>/', views.essay_result_detail, name='essay_result'),
    
    # Admin URLs
    path('admin/evaluate/<int:pk>/', views.evaluate_essay, name='admin_evaluate'),
    
    # NEW: Report URLs
    path('admin/report/essay/<int:pk>/', views.download_essay_pdf, name='download_essay_pdf'),
    path('admin/report/competition/<int:pk>/', views.download_competition_pdf, name='download_competition_pdf'),
    path('admin/report/view/<int:pk>/', views.view_essay_report, name='view_essay_report'),
]
