# competition/templatetags/competition_tags.py
from django import template
from competition.models import Essay

register = template.Library()

@register.filter
def get_user_draft(user, competition_id):
    """Get user's draft for a specific competition"""
    try:
        return Essay.objects.filter(
            user=user,
            competition_id=competition_id,
            status='draft'
        ).first()
    except Exception:
        return None


@register.filter
def status_color(status):
    """Get Bootstrap color for status"""
    colors = {
        'draft': 'secondary',
        'submitted': 'info',
        'pending_review': 'warning',
        'accepted': 'success',
        'rejected': 'danger',
    }
    return colors.get(status, 'light')


@register.filter
def get_user_submission(user, competition_id):
    """Get user's submission (non-draft) for a competition"""
    try:
        return Essay.objects.filter(
            user=user,
            competition_id=competition_id
        ).exclude(status='draft').first()
    except Exception:
        return None