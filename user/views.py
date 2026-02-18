# user/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import datetime
import re
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
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            
            # Save additional fields
            if form.cleaned_data.get('identity_doc'):
                user.identity_doc = form.cleaned_data['identity_doc']
            if form.cleaned_data.get('dob'):
                user.dob = form.cleaned_data['dob']
                
            user.save()
            
            # Create profile
            from .models import UserProfile
            UserProfile.objects.get_or_create(user=user)

            messages.success(request, "✅ Account created successfully! Please login.")
            return redirect('user:login')
        else:
            # Collect all errors for display
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            
            # Show first error as message
            if error_messages:
                messages.error(request, error_messages[0])
    else:
        form = UserRegisterForm()

    return render(request, 'user/register.html', {'form': form})


# ---------- CHECK USERNAME AVAILABILITY ----------
def check_username(request):
    """AJAX endpoint to check if username is available"""
    username = request.GET.get('username', '').strip()
    
    if not username:
        return JsonResponse({'available': False, 'error': 'Username required'})
    
    # Validate length
    if len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Too short (min 3 chars)'})
    
    if len(username) > 20:
        return JsonResponse({'available': False, 'error': 'Too long (max 20 chars)'})
    
    # Validate characters
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return JsonResponse({'available': False, 'error': 'Invalid characters'})
    
    # Check if exists
    exists = User.objects.filter(username=username).exists()
    
    if exists:
        return JsonResponse({'available': False, 'error': 'Username taken'})
    
    return JsonResponse({'available': True, 'error': None})


# ---------- CHECK EMAIL AVAILABILITY ----------
def check_email(request):
    """AJAX endpoint to check if email is available"""
    email = request.GET.get('email', '').strip()
    
    if not email:
        return JsonResponse({'available': False, 'error': 'Email required'})
    
    # Basic email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return JsonResponse({'available': False, 'error': 'Invalid email format'})
    
    # Check if exists
    exists = User.objects.filter(email=email).exists()
    
    if exists:
        return JsonResponse({'available': False, 'error': 'Email already registered'})
    
    return JsonResponse({'available': True, 'error': None})


# ---------- LOGOUT ----------
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('user:login')


# ---------- MY PROFILE (DASHBOARD) ----------
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
        pending_count = user_essays.filter(status='submitted').count()
        accepted_count = user_essays.filter(status='accepted').count()
        rejected_count = user_essays.filter(status='rejected').count()
        
        # Calculate success rate
        total_reviewed = accepted_count + rejected_count
        success_rate = (accepted_count / total_reviewed * 100) if total_reviewed > 0 else 0
        
        # Recent essays (all essays ordered by updated_at)
        recent_essays = user_essays.order_by('-updated_at')[:5]
        
        # Active competitions
        try:
            active_competitions = EssayCompetition.objects.filter(
                is_active=True,
                deadline__gte=today
            ).order_by('deadline')[:5]
            
            # Add days_left to each competition for template
            for competition in active_competitions:
                days_left = (competition.deadline - today).days
                competition.days_left = max(0, days_left)
                
        except Exception as e:
            print(f"Competition error: {e}")
            active_competitions = []
        
        # Get competitions where user has accepted essays for leaderboards
        user_competitions_with_leaderboards = EssayCompetition.objects.filter(
            essays__user=user,
            essays__status='accepted'
        ).distinct()
        
    except Exception as e:
        print(f"Profile error: {e}")
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
        'user_competitions_with_leaderboards': user_competitions_with_leaderboards,
    }
    
    return render(request, 'user/profile.html', context)


# ---------- EDIT PROFILE ----------
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


# ---------- MY ESSAYS ----------
@login_required
def my_essays(request):
    try:
        # Get all user essays
        all_essays = Essay.objects.filter(user=request.user).select_related('competition')
        
        # Separate by status using utility-like filtering
        submitted_essays = all_essays.filter(
            status__in=['submitted', 'accepted']
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
            'accepted_essays_count': accepted_essays_count,
        }
    except Exception as e:
        print(f"Error in my_essays: {e}")
        context = {
            'submitted_essays': [],
            'rejected_essays': [],
            'saved_drafts': [],
            'total_count': 0,
            'accepted_essays_count': 0,
        }
    
    return render(request, 'user/my_essays.html', context)


# ---------- DELETE ESSAY ----------
@login_required
def delete_essay(request, pk):
    essay = get_object_or_404(Essay, pk=pk, user=request.user)
    if request.method == 'POST':
        essay.delete()
        messages.success(request, 'Essay deleted successfully.')
        return redirect('user:my_essays')
    return redirect('user:my_essays')


# ---------- UTILITY FUNCTION ----------
def get_user_essay_stats(user):
    """Get statistics about user's essays"""
    from competition.models import Essay
    
    essays = Essay.objects.filter(user=user)
    
    stats = {
        'total': essays.count(),
        'drafts': essays.filter(status='draft').count(),
        'submitted': essays.filter(status='submitted').count(),
        'pending': essays.filter(status='submitted').count(),
        'accepted': essays.filter(status='accepted').count(),
        'rejected': essays.filter(status='rejected').count(),
    }
    
    # Calculate success rate
    total_reviewed = stats['accepted'] + stats['rejected']
    stats['success_rate'] = (stats['accepted'] / total_reviewed * 100) if total_reviewed > 0 else 0
    
    return stats
