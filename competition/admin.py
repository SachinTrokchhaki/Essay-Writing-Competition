# competition/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import EssayCompetition, Essay
from .evaluator import EssayEvaluator

@admin.register(EssayCompetition)
class EssayCompetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'deadline', 'is_active', 'submission_count')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    
    def submission_count(self, obj):
        return obj.essay_set.count()
    submission_count.short_description = 'Submissions'

@admin.register(Essay)
class EssayAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'competition', 'status_display', 
                   'total_score', 'evaluated_at_display', 'stored_word_count')  # Changed to stored_word_count
    list_filter = ('status', 'competition')
    search_fields = ('title', 'content', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'evaluated_at')
    actions = ['accept_and_evaluate', 'mark_as_rejected']
    
    fieldsets = (
        ('Essay Information', {
            'fields': ('competition', 'user', 'title', 'content', 'status')
        }),
        ('Evaluation Scores', {
            'fields': ('title_relevance_score', 'cohesion_score', 'grammar_score', 
                      'structure_score', 'total_score', 'evaluated_at')
        }),
        ('Administration', {
            'fields': ('reviewed_by', 'admin_notes', 'submitted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'accepted': 'success',
            'rejected': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def evaluated_at_display(self, obj):
        if obj.evaluated_at:
            return obj.evaluated_at.strftime('%Y-%m-%d %H:%M')
        return "-"
    evaluated_at_display.short_description = 'Evaluated'
    
    def accept_and_evaluate(self, request, queryset):
        """Admin action to accept essays and run evaluation"""
        updated_count = 0
        
        for essay in queryset:
            if essay.status == 'submitted':
                # Initialize evaluator
                evaluator = EssayEvaluator(
                    min_words=essay.competition.min_words,
                    max_words=essay.competition.max_words
                )
                
                # Run evaluation
                scores = evaluator.evaluate(essay.title, essay.content)
                
                # Update essay with scores
                essay.title_relevance_score = scores['title_relevance_score']
                essay.cohesion_score = scores['cohesion_score']
                essay.grammar_score = scores['grammar_score']
                essay.structure_score = scores['structure_score']
                essay.total_score = scores['total_score']
                
                # Update status
                essay.status = 'accepted'
                essay.reviewed_by = request.user
                essay.evaluated_at = timezone.now()
                essay.save()
                
                updated_count += 1
        
        if updated_count:
            self.message_user(
                request, 
                f"Successfully accepted and evaluated {updated_count} essay(s)"
            )
        else:
            self.message_user(request, "No essays were in 'submitted' status")
    
    accept_and_evaluate.short_description = "Accept and evaluate selected essays"
    
    def mark_as_rejected(self, request, queryset):
        """Simple rejection action"""
        updated = queryset.update(
            status='rejected',
            reviewed_by=request.user
        )
        self.message_user(request, f"Marked {updated} essay(s) as rejected")
    
    mark_as_rejected.short_description = "Mark as rejected"