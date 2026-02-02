# competition/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from datetime import date

from .models import EssayCompetition, Essay
from .utils import (
    check_essay_submission, 
    get_user_draft,
    can_user_submit,
    validate_essay_content
)

def competition_detail(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk, is_active=True)
    
    # Check if user can submit
    if request.user.is_authenticated:
        can_submit, message = can_user_submit(request.user, competition)
    else:
        can_submit, message = False, "Please login to submit"
    
    context = {
        'competition': competition,
        'today': timezone.now().date(),
        'can_submit': can_submit,
        'submit_message': message,
    }
    return render(request, 'competition/detail.html', context)


@login_required
def submit_essay(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk, is_active=True)
    
    # Check if user can submit
    can_submit, message = can_user_submit(request.user, competition)
    if not can_submit:
        messages.warning(request, message)
        return redirect('competition:detail', pk=pk)
    
    # Get draft (using utility function)
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
        
        word_count = len(content.strip().split())
        
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
            draft.word_count = word_count
            draft.character_count = len(content)
            draft.updated_at = timezone.now()
            draft.save()
        else:
            # Create new draft
            draft = Essay.objects.create(
                competition=competition,
                user=request.user,
                title=title,
                content=content,
                html_content=html_content,
                language=language,
                word_count=word_count,
                character_count=len(content),
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
        
        word_count = len(content.strip().split())

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
            essay.word_count = word_count
            essay.character_count = len(content)
            essay.status = 'submitted'
            essay.submitted_at = timezone.now()
            essay.updated_at = timezone.now()
            essay.save()
            
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
                word_count=word_count,
                character_count=len(content),
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
                'word_count': essay.word_count,
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
            'word_count': essay.word_count,
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
            'word_count': essay.word_count,
            'status': essay.status,
            'is_draft': essay.status == 'draft'
        }
    })


