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
    """Validate essay word count"""
    word_count = len(content.strip().split())
    
    if word_count < competition.min_words:
        return False, f"Minimum {competition.min_words} words required. Currently: {word_count} words"
    
    if word_count > competition.max_words:
        return False, f"Maximum {competition.max_words} words allowed. Currently: {word_count} words"
    
    return True, f"Word count: {word_count} (Valid)"