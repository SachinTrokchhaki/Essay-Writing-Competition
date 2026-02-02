# competition/admin.py
from django.contrib import admin
from .models import EssayCompetition, Essay
from django.utils import timezone
from django.utils.html import format_html

@admin.register(EssayCompetition)
class EssayCompetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'deadline', 'is_active', 'is_featured', 'days_left_display')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
    
    def days_left_display(self, obj):
        days = obj.days_left()
        if days > 0:
            return f"{days} days left"
        elif days == 0:
            return "Ends today"
        else:
            return "Closed"
    days_left_display.short_description = 'Status'

@admin.register(Essay)
class EssayAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'competition', 'status_display', 'submitted_at_display', 'reviewed_by_display', 'word_count')
    list_filter = ('status', 'competition', 'language', 'submitted_at')
    search_fields = ('title', 'content', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at')
    list_per_page = 20
    actions = ['mark_as_accepted', 'mark_as_rejected']
    
    def status_display(self, obj):
        status_colors = {
            'pending_review': 'warning',
            'accepted': 'success',
            'rejected': 'danger',
        }
        
        color = status_colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def submitted_at_display(self, obj):
        if obj.submitted_at:
            return obj.submitted_at.strftime('%Y-%m-%d %H:%M')
        return "-"
    submitted_at_display.short_description = 'Submitted'
    
    def reviewed_by_display(self, obj):
        if obj.reviewed_by:
            # Use get_full_name() if it exists, otherwise use get_username()
            try:
                # Try to get full name
                full_name = obj.reviewed_by.get_full_name()
                if full_name and full_name.strip():
                    return full_name
            except (AttributeError, TypeError):
                pass
            
            # Fall back to username
            return obj.reviewed_by.get_username()
        return "-"
    reviewed_by_display.short_description = 'Reviewed By'
    
    def mark_as_accepted(self, request, queryset):
        updated = queryset.filter(status='pending_review').update(
            status='accepted',
            reviewed_by=request.user
        )
        self.message_user(request, f"{updated} essays accepted.")
    mark_as_accepted.short_description = "Mark selected as Accepted"
    
    def mark_as_rejected(self, request, queryset):
        updated = queryset.filter(status='pending_review').update(
            status='rejected',
            reviewed_by=request.user
        )
        self.message_user(request, f"{updated} essays rejected.")
    mark_as_rejected.short_description = "Mark selected as Rejected"
    
    fieldsets = (
        ('Essay Information', {
            'fields': ('competition', 'user', 'title', 'content', 'html_content', 'language')
        }),
        ('Status Information', {
            'fields': ('status', 'submitted_at', 'reviewed_by', 'admin_notes')
        }),
        ('Scoring Information', {
            'fields': ('word_count', 'character_count', 'grammar_score', 'plagiarism_score', 
                      'originality_score', 'total_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )