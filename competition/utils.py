# competition/utils.py
from django.utils import timezone
from .models import Essay, EssayCompetition

def check_essay_submission(user, competition):
    """Check if user already submitted (non-draft) for this competition"""
    return Essay.objects.filter(
        competition=competition,
        user=user
    ).exclude(status='draft').first()


def get_user_draft(user, competition, draft_id=None):
    """Get user's draft for a competition"""
    if draft_id:
        try:
            return Essay.objects.get(
                id=draft_id,
                competition=competition,
                user=user
            )
        except Essay.DoesNotExist:
            return None
    
    # If no draft_id, get the latest draft
    return Essay.objects.filter(
        competition=competition,
        user=user,
        status='draft'
    ).first()


def can_user_submit(user, competition):
    """Check if user can submit to this competition"""
    if not competition.is_open():
        return False, "Competition deadline has passed"
    
    existing = check_essay_submission(user, competition)
    if existing:
        if existing.status == 'accepted':
            return False, "Your essay has already been accepted!"
        elif existing.status == 'submitted':
            return False, "You have already submitted an essay"
        elif existing.status == 'pending_review':
            return False, "Your essay is currently being reviewed"
        elif existing.status == 'rejected':
            return True, "You can resubmit (previous essay was rejected)"
    
    return True, "You can submit"


def validate_essay_content(content, competition):
    """Validate essay content against competition requirements"""
    if not content or not content.strip():
        return False, "Essay content cannot be empty"
    
    # Calculate word count from content
    words = content.strip().split()
    word_count = len(words)
    
    # Check minimum words
    if word_count < competition.min_words:
        return False, f"Essay must be at least {competition.min_words} words. Current: {word_count}"
    
    # Check maximum words
    if word_count > competition.max_words:
        return False, f"Essay must not exceed {competition.max_words} words. Current: {word_count}"
    
    return True, "Valid"
