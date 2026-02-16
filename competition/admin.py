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
        return obj.essays.count()
    submission_count.short_description = 'Submissions'

@admin.register(Essay)
class EssayAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'competition', 'status_display', 
                   'total_score', 'evaluated_at_display', 'stored_word_count')
    list_filter = ('status', 'competition')
    search_fields = ('title', 'content', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'evaluated_at')
    actions = ['accept_and_evaluate', 'mark_as_rejected']
    
    fieldsets = (
        ('Essay Information', {
            'fields': ('competition', 'user', 'title', 'content', 'html_content', 'language', 'status')
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
        elif obj.status == 'accepted':
            # If accepted but no evaluated_at, show created_at
            return obj.created_at.strftime('%Y-%m-%d %H:%M') + " (auto)"
        return "-"
    evaluated_at_display.short_description = 'Evaluated'
    evaluated_at_display.admin_order_field = 'evaluated_at'
    
    def accept_and_evaluate(self, request, queryset):
        """Admin action to accept essays and run evaluation"""
        updated_count = 0
        
        for essay in queryset:
            if essay.status == 'submitted':
                try:
                    # Initialize evaluator
                    evaluator = EssayEvaluator(
                        min_words=essay.competition.min_words,
                        max_words=essay.competition.max_words
                    )
                    
                    # ALWAYS RUN EVALUATION, even if scores exist
                    # This ensures fresh evaluation and sets evaluated_at
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
                    
                    # Check if submitted_at needs to be set
                    needs_submitted_at = False
                    if not essay.submitted_at:
                        essay.submitted_at = timezone.now()
                        needs_submitted_at = True
                    
                    # SAVE WITHOUT TRIGGERING AUTO-EVALUATION
                    # Use update_fields to prevent save() from starting background thread
                    update_fields=[
                        'title_relevance_score', 'cohesion_score', 'grammar_score',
                        'structure_score', 'total_score', 'status',
                        'reviewed_by', 'evaluated_at'
                    ]
                    
                    # Add submitted_at to update_fields if we're setting it
                    if needs_submitted_at:
                        update_fields.append('submitted_at')
                    
                    essay.save(update_fields=update_fields) 
                    
                    updated_count += 1
                    
                except Exception as e:
                    self.message_user(
                        request, 
                        f"Error evaluating essay '{essay.title}': {str(e)}", 
                        level='error'
                    )
        
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
        for essay in queryset:
            essay.status = 'rejected'
            essay.reviewed_by = request.user
            # Save without triggering auto-evaluation
            essay.save(update_fields=['status', 'reviewed_by'])
        self.message_user(request, f"Marked {len(queryset)} essay(s) as rejected")
    
    mark_as_rejected.short_description = "Mark as rejected"

