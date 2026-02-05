# core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from competition.models import Essay
from .forms import FeedbackForm
from .models import Feedback
from datetime import date

def home(request):
    """Homepage view with competitions"""
    try:
        # Import inside function to avoid circular imports
        from competition.models import EssayCompetition
        
        # Get active competitions - SIMPLIFIED VERSION
        competitions = EssayCompetition.objects.filter(
            is_active=True
        ).order_by('-created_at')  # Changed to just use -created_at
        
        # Debug: Check what we got
        print(f"DEBUG: Found {competitions.count()} active competitions")
        
    except Exception as e:
        # If there's any error (model doesn't exist, etc.), show empty list
        competitions = []
        print(f"Debug: Could not load competitions - {e}")
    
    # Get approved feedback for homepage
    try:
        approved_feedback = Feedback.objects.filter(
            status='approved',
            show_on_homepage=True
        ).order_by('-created_at')[:6]
    except:
        approved_feedback = []
    
    # Handle feedback form submission
    if request.method == 'POST' and 'submit_feedback' in request.POST:
        if request.user.is_authenticated:
            form = FeedbackForm(request.POST, user=request.user)
            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.user = request.user
                feedback.save()
                messages.success(request, 'Thank you for your feedback!')
                return redirect('core:home')
            else:
                messages.error(request, 'Please check the form for errors.')
        else:
            messages.error(request, 'Please login to submit feedback.')
    
    context = {
        'competitions': competitions,
        'approved_feedback': approved_feedback,
    }
    
    # IMPORTANT: Make sure this line is at the end and not inside any condition
    return render(request, "core/index.html", context)

def terms(request):
    return render(request, "core/terms-of-service.html")

def privacy(request):
    return render(request, "core/privacy-policy.html")

def custom_404(request, exception):
    value = request.path.strip('/')
    context = {
        'value': value,
        'title': 'Page Not Found',
        'message': f'The page "{value}" was not found.'
    }
    return render(request, 'core/404.html', context, status=404)

