from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
import datetime
from .forms import UserLoginForm, UserRegisterForm, UserUpdateForm
from competition.models import Essay, EssayCompetition

User = get_user_model()


# ---------- LOGIN ----------
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('user:my_profile')
    else:
        form = UserLoginForm()

    return render(request, 'user/login.html', {'form': form})


# ---------- REGISTER ----------
def register(request):
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            # Ensure profile is created
            from .models import UserProfile
            UserProfile.objects.get_or_create(user=user)

            messages.success(request, "Account created successfully. Please login.")
            return redirect('user:login')
    else:
        form = UserRegisterForm()

    return render(request, 'user/register.html', {'form': form})


# ---------- LOGOUT ----------
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('user:login')


# ---------- PROFILE VIEWS ----------
@login_required
def my_profile(request):
    user = request.user
    today = datetime.date.today()
    
    try:
        # Get user essays
        user_essays = Essay.objects.filter(user=user).select_related('competition')
        
        # Count essays by status
        total_submissions = user_essays.count()
        draft_count = user_essays.filter(status='draft').count()
        submitted_count = user_essays.filter(status='submitted').count()
        pending_count = user_essays.filter(status='pending_review').count()
        accepted_count = user_essays.filter(status='accepted').count()
        rejected_count = user_essays.filter(status='rejected').count()
        
        # Calculate success rate
        total_reviewed = accepted_count + rejected_count
        success_rate = (accepted_count / total_reviewed * 100) if total_reviewed > 0 else 0
        
        # Recent essays (non-draft)
        recent_essays = user_essays.exclude(
            status='draft'
        ).order_by('-updated_at')[:5]
        
        # Active competitions
        try:
            active_competitions = EssayCompetition.objects.filter(
                is_active=True,
                deadline__gte=today
            ).order_by('deadline')[:5]
        except:
            active_competitions = []
        
        # Get competitions where user has accepted essays for leaderboards
        user_competitions_with_leaderboards = EssayCompetition.objects.filter(
            essay__user=user,
            essay__status='accepted'
        ).distinct()
        
    except Exception as e:
        # If models don't exist yet, use defaults
        total_submissions = 0
        draft_count = 0
        submitted_count = 0
        pending_count = 0
        accepted_count = 0
        rejected_count = 0
        success_rate = 0
        recent_essays = []
        active_competitions = []
        user_competitions_with_leaderboards = []
    
    context = {
        'user': user,
        'today': today,
        'total_submissions': total_submissions,
        'draft_count': draft_count,
        'submitted_count': submitted_count,
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'success_rate': success_rate,
        'recent_essays': recent_essays,
        'active_competitions': active_competitions,
        'user_competitions_with_leaderboards': user_competitions_with_leaderboards,  # Add this
    }
    
    return render(request, 'user/profile.html', context)


@login_required
def edit_profile(request):
    user = request.user
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.country = request.POST.get('country', '')
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('user:my_profile')
    
    context = {'user': user}
    return render(request, 'user/edit_profile.html', context)


@login_required
def my_essays(request):
    try:
        # Get all user essays
        all_essays = Essay.objects.filter(user=request.user).select_related('competition')
        
        # Separate by status using utility-like filtering
        submitted_essays = all_essays.filter(
            status__in=['submitted', 'pending_review', 'accepted']
        ).order_by('-submitted_at')
        
        rejected_essays = all_essays.filter(status='rejected').order_by('-updated_at')
        saved_drafts = all_essays.filter(status='draft').order_by('-updated_at')
        
        # Count accepted essays for notification
        accepted_essays_count = all_essays.filter(status='accepted').count()
        
        context = {
            'submitted_essays': submitted_essays,
            'rejected_essays': rejected_essays,
            'saved_drafts': saved_drafts,
            'total_count': all_essays.count(),
            'accepted_essays_count': accepted_essays_count,  # Add this
        }
    except Exception as e:
        print(f"Error in my_essays: {e}")
        context = {
            'submitted_essays': [],
            'rejected_essays': [],
            'saved_drafts': [],
            'total_count': 0,
            'accepted_essays_count': 0,  # Add this
        }
    
    return render(request, 'user/my_essays.html', context)


# Utility function to get user essay statistics
def get_user_essay_stats(user):
    """Get statistics about user's essays"""
    from competition.models import Essay
    
    essays = Essay.objects.filter(user=user)
    
    stats = {
        'total': essays.count(),
        'drafts': essays.filter(status='draft').count(),
        'submitted': essays.filter(status='submitted').count(),
        'pending': essays.filter(status='pending_review').count(),
        'accepted': essays.filter(status='accepted').count(),
        'rejected': essays.filter(status='rejected').count(),
    }
    
    # Calculate success rate
    total_reviewed = stats['accepted'] + stats['rejected']
    stats['success_rate'] = (stats['accepted'] / total_reviewed * 100) if total_reviewed > 0 else 0
    
    return stats  # Important: return the stats dictionary


@login_required
def delete_essay(request, pk):
    from django.shortcuts import get_object_or_404
    essay = get_object_or_404(Essay, pk=pk, user=request.user)
    if request.method == 'POST':
        essay.delete()
        messages.success(request, 'Essay deleted successfully.')
        return redirect('user:my_essays')
    return redirect('user:my_essays')