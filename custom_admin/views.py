from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json

from competition.models import EssayCompetition, Essay
from core.models import Feedback
from user.models import CustomUser

def is_admin(user):
    return user.is_staff or user.is_superuser

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, 'Invalid credentials or not an admin user')
    
    return render(request, 'custom_admin/login.html')

def admin_logout(request):
    logout(request)
    return redirect('custom_admin:login')

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def dashboard(request):
    # Basic stats
    total_users = CustomUser.objects.count()
    total_competitions = EssayCompetition.objects.filter(is_active=True).count()
    total_essays = Essay.objects.count()
    accepted_essays = Essay.objects.filter(status='accepted').count()
    
    # FIXED: Use created_at instead of date_joined
    today = timezone.now().date()
    new_users_today = CustomUser.objects.filter(created_at__date=today).count()
    
    # Pending essays
    pending_essays = Essay.objects.filter(status='submitted').count()
    
    # Upcoming competitions
    upcoming_competitions = EssayCompetition.objects.filter(
        deadline__gt=timezone.now(),
        is_active=True
    ).count()
    
    # Acceptance rate
    acceptance_rate = (accepted_essays / total_essays * 100) if total_essays > 0 else 0
    
    # Weekly submissions
    daily_submissions = []
    daily_labels = []
    
    for i in range(6, -1, -1):  # Last 7 days
        day = timezone.now() - timedelta(days=i)
        count = Essay.objects.filter(
            submitted_at__date=day.date()
        ).count()
        daily_submissions.append(count)
        daily_labels.append(day.strftime('%a'))  # Mon, Tue, etc.
    
    # Competition stats for chart
    active_comps = EssayCompetition.objects.filter(
        is_active=True, 
        deadline__gt=timezone.now()
    ).count()
    expired_comps = EssayCompetition.objects.filter(
        deadline__lt=timezone.now()
    ).count()
    upcoming_comps = EssayCompetition.objects.filter(
        is_active=True,
        deadline__gt=timezone.now() + timedelta(days=7)
    ).count()
    
    # Recent essays
    recent_essays = Essay.objects.select_related('user', 'competition').order_by('-submitted_at')[:5]
    
    # Recent feedback
    recent_feedback = Feedback.objects.order_by('-created_at')[:5]
    
    # FIXED: Use created_at instead of date_joined for ordering
    top_users = CustomUser.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).filter(essay_count__gt=0).order_by('-accepted_count')[:5]
    
    # Calculate success rate for each user
    for user in top_users:
        if user.essay_count > 0:
            user.success_rate = (user.accepted_count / user.essay_count) * 100
        else:
            user.success_rate = 0
    
    context = {
        'total_users': total_users,
        'total_competitions': total_competitions,
        'total_essays': total_essays,
        'accepted_essays': accepted_essays,
        'new_users_today': new_users_today,
        'pending_essays': pending_essays,
        'upcoming_competitions': upcoming_competitions,
        'acceptance_rate': round(acceptance_rate, 1),
        'weekly_labels': json.dumps(daily_labels),
        'weekly_data': json.dumps(daily_submissions),
        'competition_stats': json.dumps([active_comps, expired_comps, upcoming_comps]),
        'recent_essays': recent_essays,
        'recent_feedback': recent_feedback,
        'top_users': top_users,
        'now': timezone.now(),
    }
    
    return render(request, 'custom_admin/dashboard.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def competitions(request):
    competitions_list = EssayCompetition.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).order_by('-deadline')
    
    context = {
        'competitions': competitions_list,
        'now': timezone.now(),
    }
    
    return render(request, 'custom_admin/competitions.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essays(request):
    essays_list = Essay.objects.select_related('user', 'competition').all().order_by('-submitted_at')
    
    # Apply filters
    status = request.GET.get('status')
    competition_id = request.GET.get('competition')
    search = request.GET.get('search')
    
    if status:
        essays_list = essays_list.filter(status=status)
    if competition_id:
        essays_list = essays_list.filter(competition_id=competition_id)
    if search:
        essays_list = essays_list.filter(
            Q(title__icontains=search) | 
            Q(user__username__icontains=search) |
            Q(content__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(essays_list, 20)
    page_number = request.GET.get('page')
    essays_page = paginator.get_page(page_number)
    
    # Get all competitions for filter dropdown
    competitions = EssayCompetition.objects.all()
    
    context = {
        'essays': essays_page,
        'competitions': competitions,
    }
    
    return render(request, 'custom_admin/essays.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def users(request):
    # FIXED: Use created_at instead of date_joined
    users_list = CustomUser.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).order_by('-created_at')  # Changed from date_joined to created_at
    
    # Statistics
    total_users = users_list.count()
    # FIXED: Use last_login for active users today
    active_users = users_list.filter(last_login__date=timezone.now().date()).count()
    users_with_essays = users_list.filter(essay_count__gt=0).count()
    # FIXED: Use created_at for new users
    new_users = users_list.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
    
    # Pagination
    paginator = Paginator(users_list, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'total_users': total_users,
        'active_users': active_users,
        'users_with_essays': users_with_essays,
        'new_users': new_users,
    }
    
    return render(request, 'custom_admin/users.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def feedback(request):
    feedback_list = Feedback.objects.all().order_by('-created_at')
    
    # Handle status update
    if request.method == 'POST':
        feedback_id = request.POST.get('feedback_id')
        action = request.POST.get('action')
        
        if feedback_id and action:
            feedback_item = get_object_or_404(Feedback, id=feedback_id)
            if action == 'approve':
                feedback_item.status = 'approved'
                messages.success(request, f'Feedback from {feedback_item.name} approved')
            elif action == 'reject':
                feedback_item.status = 'rejected'
                feedback_item.show_on_homepage = False
                messages.success(request, f'Feedback from {feedback_item.name} rejected')
            elif action == 'feature':
                feedback_item.show_on_homepage = True
                messages.success(request, f'Feedback from {feedback_item.name} featured')
            feedback_item.save()
            return redirect('custom_admin:feedback')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        feedback_list = feedback_list.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(feedback_list, 20)
    page_number = request.GET.get('page')
    feedback_page = paginator.get_page(page_number)
    
    context = {
        'feedback_list': feedback_page,
    }
    
    return render(request, 'custom_admin/feedback.html', context)