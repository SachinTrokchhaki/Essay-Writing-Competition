# competition/templatetags/competition_tags.py
from django import template
from competition.models import Essay

register = template.Library()

@register.filter
def get_user_draft(user, competition_id):
    """Get user's draft for a specific competition"""
    if not user.is_authenticated:
        return None
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
        'accepted': 'success',
        'rejected': 'danger',
    }
    return colors.get(status, 'light')


@register.filter
def get_user_submission(user, competition_id):
    """Get user's submission (non-draft) for a competition"""
    if not user.is_authenticated:
        return None
    try:
        return Essay.objects.filter(
            user=user,
            competition_id=competition_id
        ).exclude(status='draft').first()
    except Exception:
        return None


@register.filter
def days_left(competition):
    """Calculate days left for competition"""
    from datetime import date
    today = date.today()
    if competition.deadline >= today:
        days = (competition.deadline - today).days
        return max(days, 0)
    else:
        return -1


@register.filter
def has_accepted_essays(competition):
    """Check if competition has any accepted essays"""
    return competition.essays.filter(status='accepted').exists()


@register.filter
def get_top_essays(competition, count=5):
    """Get top N essays for a competition"""
    return competition.essays.filter(
        status='accepted'
    ).order_by('-total_score')[:count]


@register.filter
def filter_user_essays(essays, user):
    """Filter essays to show only user's essays"""
    # If essays is a QuerySet, use filter() for database efficiency
    if hasattr(essays, 'filter'):
        return essays.filter(user=user)
    # If it's a list, use list comprehension
    return [essay for essay in essays if essay.user == user]

