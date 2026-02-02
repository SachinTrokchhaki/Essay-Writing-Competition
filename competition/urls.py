from django.urls import path
from . import views

app_name = 'competition'

urlpatterns = [
    path('<int:pk>/', views.competition_detail, name='detail'),
    path('<int:pk>/submit/', views.submit_essay, name='submit_essay'),
    
    path('save-draft/', views.save_draft, name='save_draft'),
    path('submit-final/', views.submit_final_essay, name='submit_final'),
    path('get-draft/<int:pk>/', views.get_draft, name='get_draft'),
    path('get-draft-content/<int:pk>/', views.get_draft_content, name='get_draft_content'),
]
