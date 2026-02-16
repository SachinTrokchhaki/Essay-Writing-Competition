# competition/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.conf import settings
import json
from datetime import date, datetime, timedelta  # ADD THIS LINE
from django.db import models 
from django.http import HttpResponse
from .reports import generate_essay_pdf, generate_competition_report

from .models import EssayCompetition, Essay
from .evaluator import EssayEvaluator
from .utils import (
    check_essay_submission, 
    get_user_draft,
    can_user_submit,
    validate_essay_content
)

def competition_detail(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk, is_active=True)
    
    if request.user.is_authenticated:
        can_submit, message = can_user_submit(request.user, competition)
    else:
        can_submit, message = False, "Please login to submit"
    
    # Check if user is admin/staff
    is_admin = request.user.is_staff or request.user.is_superuser
    
    # Get current time
    now = timezone.now()
    
    # Convert competition.deadline (date) to datetime for comparison
    deadline_datetime = timezone.make_aware(
        datetime.combine(competition.deadline, datetime.min.time())
    )
    
    # Calculate when results should be visible (deadline + 5 minutes)
    publish_time = deadline_datetime + timedelta(minutes=settings.RESULT_PUBLISH_DELAY_MINUTES)
    
    # Determine if results should be visible
    if is_admin:
        # Admin can always see results
        results_visible = True
    else:
        # Regular users: only see results after deadline + delay
        results_visible = now >= publish_time
    
    # Get leaderboard for this competition (with delay check)
    if results_visible:
        leaderboard = Essay.objects.filter(
            competition=competition,
            status='accepted'
        ).order_by('-total_score')[:10]
        
        # Get top 5 for preview
        top_essays = leaderboard[:5]
    else:
        leaderboard = Essay.objects.none()
        top_essays = []
    
    context = {
        'competition': competition,
        'can_submit': can_submit,
        'submit_message': message,
        'leaderboard': leaderboard,
        'top_essays': top_essays,
        'results_visible': results_visible,
        'deadline': competition.deadline,
        'deadline_datetime': deadline_datetime,
        'publish_time': publish_time,
        'is_admin': is_admin,
    }
    return render(request, 'competition/detail.html', context)


@login_required
def submit_essay(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk, is_active=True)
    
    can_submit, message = can_user_submit(request.user, competition)
    if not can_submit:
        messages.warning(request, message)
        return redirect('competition:detail', pk=pk)
    
    draft_id = request.GET.get('draft')
    existing_draft = get_user_draft(request.user, competition, draft_id)
    
    context = {
        'competition': competition,
        'existing_draft': existing_draft,
        'draft_id': draft_id,
    }
    return render(request, 'competition/submit_essay.html', context)


@login_required
@require_POST
def save_draft(request):
    try:
        data = json.loads(request.body)
        competition_id = data.get('competition_id')
        title = data.get('title')
        content = data.get('content')
        html_content = data.get('html_content')
        language = data.get('language')
        draft_id = data.get('draft_id')
        
        if not all([competition_id, title, content]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        competition = get_object_or_404(EssayCompetition, id=competition_id, is_active=True)
        
        # Validate word count using utility
        is_valid, message = validate_essay_content(content, competition)
        if not is_valid:
            return JsonResponse({'success': False, 'error': message})
        
        # Check if user already has a non-draft submission
        existing_submission = check_essay_submission(request.user, competition)
        if existing_submission:
            return JsonResponse({
                'success': False,
                'error': f'Cannot save draft. You already submitted an essay. Status: {existing_submission.get_status_display()}'
            })
        
        # Get or create draft
        if draft_id:
            draft = Essay.objects.filter(
                id=draft_id,
                competition=competition,
                user=request.user
            ).first()
        else:
            draft = Essay.objects.filter(
                competition=competition,
                user=request.user,
                status='draft'
            ).first()
        
        if draft:
            # Check if there are actual changes
            if (draft.title == title and 
                draft.content == content and 
                draft.language == language):
                return JsonResponse({
                    'success': True,
                    'message': 'No changes detected. Draft already saved.',
                    'essay_id': draft.id,
                    'already_saved': True
                })
            
            # Update existing draft
            draft.title = title
            draft.content = content
            draft.html_content = html_content
            draft.language = language
            draft.updated_at = timezone.now()
            draft.save()  # Word count will be auto-updated in save() method
        else:
            # Create new draft
            draft = Essay.objects.create(
                competition=competition,
                user=request.user,
                title=title,
                content=content,
                html_content=html_content,
                language=language,
                status='draft'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Draft saved successfully',
            'essay_id': draft.id,
            'already_saved': False
        })
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def submit_final_essay(request):
    try:
        data = json.loads(request.body)
        competition_id = data.get('competition_id')
        title = data.get('title')
        content = data.get('content')
        html_content = data.get('html_content')
        language = data.get('language')
        draft_id = data.get('draft_id')
        
        if not all([competition_id, title, content]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        competition = get_object_or_404(EssayCompetition, id=competition_id, is_active=True)

        # Check if competition is open
        if not competition.is_open():
            return JsonResponse({'success': False, 'error': 'Competition deadline has passed'})

        # Validate word count
        is_valid, message = validate_essay_content(content, competition)
        if not is_valid:
            return JsonResponse({'success': False, 'error': message})

        # Check if user already submitted
        existing_submission = check_essay_submission(request.user, competition)
        if existing_submission:
            return JsonResponse({
                'success': False, 
                'error': f'You already submitted an essay. Status: {existing_submission.get_status_display()}'
            })

        # Handle draft or create new
        if draft_id:
            essay = Essay.objects.filter(
                id=draft_id,
                competition=competition,
                user=request.user
            ).first()
        else:
            essay = Essay.objects.filter(
                competition=competition,
                user=request.user,
                status='draft'
            ).first()

        if essay:
            # Update existing essay
            if essay.status != 'draft':
                return JsonResponse({
                    'success': False,
                    'error': f'This essay has already been submitted. Status: {essay.get_status_display()}'
                })
            
            essay.title = title
            essay.content = content
            essay.html_content = html_content
            essay.language = language
            essay.status = 'submitted'
            essay.submitted_at = timezone.now()
            essay.updated_at = timezone.now()
            essay.save()  # Word count will be auto-updated
            
            # Delete other drafts
            Essay.objects.filter(
                competition=competition,
                user=request.user,
                status='draft'
            ).exclude(id=essay.id).delete()
        else:
            # Create new submission
            essay = Essay.objects.create(
                competition=competition,
                user=request.user,
                title=title,
                content=content,
                html_content=html_content,
                language=language,
                status='submitted',
                submitted_at=timezone.now()
            )

        return JsonResponse({
            'success': True, 
            'message': 'Essay submitted successfully! It is now waiting for review.',
            'essay_id': essay.id
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_GET
def get_draft(request, pk):
    essay = get_object_or_404(Essay, pk=pk, user=request.user)
    
    if essay.status != 'draft':
        return JsonResponse({
            'success': True,
            'data': {
                'title': essay.title,
                'content': essay.content,
                'html_content': essay.html_content,
                'language': essay.language,
                'word_count': essay.word_count,  # Uses property
                'created_at': essay.created_at.isoformat(),
                'updated_at': essay.updated_at.isoformat(),
                'status': essay.status,
                'status_display': essay.get_status_display(),
                'is_draft': False
            }
        })
    
    return JsonResponse({
        'success': True,
        'data': {
            'title': essay.title,
            'content': essay.content,
            'html_content': essay.html_content,
            'language': essay.language,
            'word_count': essay.word_count,  # Uses property
            'created_at': essay.created_at.isoformat(),
            'updated_at': essay.updated_at.isoformat(),
            'status': essay.status,
            'status_display': essay.get_status_display(),
            'is_draft': True
        }
    })


@login_required
@require_GET
def get_draft_content(request, pk):
    """Get draft content with proper HTML formatting"""
    essay = get_object_or_404(Essay, pk=pk, user=request.user)
    
    # Prepare the content
    if essay.html_content and essay.html_content.strip():
        content = essay.html_content
    else:
        content = essay.content
    
    # Ensure basic HTML structure if it's plain text
    if content and not content.strip().startswith('<'):
        # Convert plain text to HTML paragraphs
        paragraphs = content.strip().split('\n\n')
        html_content = ''
        for i, para in enumerate(paragraphs):
            if para.strip():
                html_content += f'<p style="text-indent: 2em; margin-bottom: 1.5rem;">{para.strip()}</p>'
        
        if not html_content:
            html_content = '<p style="text-indent: 2em;">&nbsp;</p>'
        
        content = html_content
    
    return JsonResponse({
        'success': True,
        'data': {
            'title': essay.title,
            'content': content,
            'language': essay.language,
            'word_count': essay.word_count,  # Uses property
            'status': essay.status,
            'is_draft': essay.status == 'draft'
        }
    })


@staff_member_required
def evaluate_essay(request, pk):
    """Admin view to manually trigger evaluation"""
    essay = get_object_or_404(Essay, pk=pk)
    
    if request.method == 'POST' and essay.status == 'submitted':
        # Initialize evaluator
        evaluator = EssayEvaluator(
            min_words=essay.competition.min_words,
            max_words=essay.competition.max_words
        )
        
        # Run evaluation
        scores = evaluator.evaluate(essay.title, essay.content)
        
        # Update essay
        essay.title_relevance_score = scores['title_relevance_score']
        essay.cohesion_score = scores['cohesion_score']
        essay.grammar_score = scores['grammar_score']
        essay.structure_score = scores['structure_score']
        essay.total_score = scores['total_score']
        essay.status = 'accepted'
        essay.reviewed_by = request.user
        essay.evaluated_at = timezone.now()
        essay.save()
        
        messages.success(request, f"Essay evaluated! Total score: {scores['total_score']}")
        return redirect('admin:competition_essay_changelist')
    
    context = {
        'essay': essay,
        'page_title': f'Evaluate: {essay.title}'
    }
    return render(request, 'competition/admin/evaluate_essay.html', context)


def leaderboard(request, pk=None):
    """Competition-specific leaderboard with delayed results"""
    if pk:
        # Specific competition leaderboard
        competition = get_object_or_404(EssayCompetition, pk=pk, is_active=True)
        
        # Check if user is admin/staff
        is_admin = request.user.is_staff or request.user.is_superuser
        
        # Get current time
        now = timezone.now()
        
        # Convert competition.deadline (date) to datetime for comparison
        deadline_datetime = timezone.make_aware(
            datetime.combine(competition.deadline, datetime.min.time())
        )
        
        # Calculate when results should be visible (deadline + 5 minutes)
        publish_time = deadline_datetime + timedelta(minutes=settings.RESULT_PUBLISH_DELAY_MINUTES)
        
        # Determine if results should be visible
        if is_admin:
            # Admin can always see results
            results_visible = True
            essays = Essay.objects.filter(
                competition=competition,
                status='accepted'
            ).select_related('user').order_by('-total_score')
        else:
            # Regular users: only see results after deadline + delay
            if now >= publish_time:
                results_visible = True
                essays = Essay.objects.filter(
                    competition=competition,
                    status='accepted'
                ).select_related('user').order_by('-total_score')
            else:
                results_visible = False
                essays = Essay.objects.none()  # Empty queryset
        
        # Add rank to each essay (handling ties correctly)
        rank = 1
        prev_score = None
        same_score_count = 1
        
        for i, essay in enumerate(essays, 1):
            if prev_score is None:
                essay.rank = 1
                prev_score = essay.total_score
                same_score_count = 1
            elif essay.total_score == prev_score:
                # Same score as previous, same rank
                essay.rank = rank
                same_score_count += 1
            else:
                # Different score, increment rank
                rank = i
                essay.rank = rank
                prev_score = essay.total_score
                same_score_count = 1
        
        # Get user's essay if authenticated
        user_essay = None
        if request.user.is_authenticated:
            user_essay = Essay.objects.filter(
                competition=competition,
                user=request.user
            ).first()
        
        page_title = f'Leaderboard: {competition.title}'
        
        context = {
            'competition': competition,
            'essays': essays,
            'page_title': page_title,
            'user_essay': user_essay,
            'results_visible': results_visible,
            'deadline': competition.deadline,
            'deadline_datetime': deadline_datetime,
            'publish_time': publish_time,
            'now': now,
            'is_admin': is_admin,
        }
        return render(request, 'competition/leaderboard.html', context)
        
    else:
        # Global view - show list of competitions with leaderboards
        competitions = EssayCompetition.objects.filter(
            is_active=True
        ).annotate(
            accepted_count=models.Count('essays', filter=models.Q(essays__status='accepted'))
        ).filter(accepted_count__gt=0).order_by('-created_at')
        
        return render(request, 'competition/competition_list.html', {
            'competitions': competitions,
            'page_title': 'Competition Leaderboards'
        })


@login_required
def my_results(request):
    """User's own results page - grouped by competition"""
    # Get all competitions where user has accepted essays
    competitions = EssayCompetition.objects.filter(
        essay__user=request.user,
        essay__status='accepted'
    ).distinct().order_by('-created_at')
    
    # Get essays for each competition
    competition_results = []
    for competition in competitions:
        essays = Essay.objects.filter(
            competition=competition,
            user=request.user,
            status='accepted'
        ).order_by('-total_score')
        
        # Calculate rank for each essay
        for essay in essays:
            # Calculate rank within competition
            rank = Essay.objects.filter(
                competition=competition,
                status='accepted',
                total_score__gt=essay.total_score
            ).count() + 1
            essay.competition_rank = rank
        
        competition_results.append({
            'competition': competition,
            'essays': essays
        })
    
    context = {
        'competition_results': competition_results,
        'page_title': 'My Results'
    }
    return render(request, 'competition/my_results.html', context)


@login_required
def essay_result_detail(request, pk):
    """Detailed view of a single essay result"""
    essay = get_object_or_404(Essay, pk=pk, user=request.user)
    
    # Check if essay has been evaluated
    if essay.status != 'accepted':
        messages.warning(request, "Essay hasn't been evaluated yet")
        return redirect('competition:my_results')
    
    # Calculate rank within this competition
    rank = Essay.objects.filter(
        competition=essay.competition,
        status='accepted',
        total_score__gt=essay.total_score
    ).count() + 1
    
    # Get total participants in this competition
    total_participants = Essay.objects.filter(
        competition=essay.competition,
        status='accepted'
    ).count()
    
    context = {
        'essay': essay,
        'rank': rank,
        'total_participants': total_participants,
        'page_title': f'Results: {essay.title}'
    }
    return render(request, 'competition/essay_result_detail.html', context)


@staff_member_required
def download_essay_pdf(request, pk):
    """Download PDF report for a single essay"""
    try:
        pdf_content = generate_essay_pdf(pk)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="essay_report_{pk}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('admin:competition_essay_changelist')


@staff_member_required  
def download_competition_pdf(request, pk):
    """Download PDF report for entire competition"""
    try:
        pdf_content = generate_competition_report(pk)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="competition_report_{pk}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('admin:competition_essaycompetition_changelist')


@staff_member_required
def view_essay_report(request, pk):
    """View essay report in browser"""
    try:
        pdf_content = generate_essay_pdf(pk)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="essay_report_{pk}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('admin:competition_essay_changelist')
    
