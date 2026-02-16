# competition/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from datetime import date
import threading

class EssayCompetition(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateField()
    eligibility = models.CharField(max_length=100)
    prize = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For evaluation criteria
    min_words = models.IntegerField(default=250)
    max_words = models.IntegerField(default=500)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Competition"
        verbose_name_plural = "Competitions"
    
    def __str__(self):
        return self.title
    
    def is_open(self):
        return self.deadline >= date.today()
    
    def get_absolute_url(self):
        return reverse('competition:detail', kwargs={'pk': self.pk})


class Essay(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ne', 'Nepali'),
    ]
    
    # Foreign keys
    competition = models.ForeignKey('EssayCompetition', on_delete=models.CASCADE, related_name='essays')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='essays')
    
    # Essay content
    title = models.CharField(max_length=200)
    content = models.TextField()
    html_content = models.TextField(blank=True)  # For rich text content
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Database fields for querying (auto-calculated)
    stored_word_count = models.IntegerField(default=0)
    stored_character_count = models.IntegerField(default=0)
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_essays'
    )
    admin_notes = models.TextField(blank=True)
    
    # EVALUATION FIELDS
    title_relevance_score = models.FloatField(default=0.0)
    cohesion_score = models.FloatField(default=0.0)
    grammar_score = models.FloatField(default=0.0)
    structure_score = models.FloatField(default=0.0)
    total_score = models.FloatField(default=0.0)
    
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-total_score', '-created_at']
        indexes = [
            models.Index(fields=['status', 'total_score']),
            models.Index(fields=['stored_word_count']),
            models.Index(fields=['competition', 'status']),
            models.Index(fields=['user', 'competition']),
        ]
        verbose_name = "Essay"
        verbose_name_plural = "Essays"
    
    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.get_status_display()})"
    
    @property
    def word_count(self):
        """Calculate word count from content"""
        if self.content and self.content.strip():
            return len(self.content.strip().split())
        return 0
    
    @property
    def character_count(self):
        """Calculate character count from content"""
        return len(self.content) if self.content else 0
    
    def save(self, *args, **kwargs):
        """Auto-update stored counts when saving"""
        # Update stored counts from content
        self.stored_word_count = self.word_count
        self.stored_character_count = self.character_count
        
        # If this is a final submission, set submitted_at
        if self.status in ['submitted', 'accepted', 'rejected'] and not self.submitted_at:
            from django.utils import timezone
            self.submitted_at = timezone.now()
        
        # Call parent save first to ensure instance is saved
        super().save(*args, **kwargs)
        
        # Auto-evaluate if status changed to accepted and not evaluated yet
        # Run in background thread to avoid blocking
        if (self.status == 'accepted' and 
            self.total_score == 0.0 and 
            self.content and 
            self.title):
            threading.Thread(target=self.auto_evaluate, daemon=True).start()
    
    def auto_evaluate(self):
        """Auto-evaluate essay in background"""
        try:
            from .evaluator import EssayEvaluator
            
            evaluator = EssayEvaluator(
                min_words=self.competition.min_words,
                max_words=self.competition.max_words
            )
            
            scores = evaluator.evaluate(self.title, self.content)
            
            # Update fields
            self.title_relevance_score = scores['title_relevance_score']
            self.cohesion_score = scores['cohesion_score']
            self.grammar_score = scores['grammar_score']
            self.structure_score = scores['structure_score']
            self.total_score = scores['total_score']
            
            # Save without triggering save() again to avoid loop
            super(Essay, self).save(update_fields=[
                'title_relevance_score', 'cohesion_score', 'grammar_score',
                'structure_score', 'total_score', 'evaluated_at'
            ])
            
            print(f"✓ Auto-evaluated essay {self.id}: {self.total_score:.1f} points")
            
        except ImportError as e:
            print(f"⚠️ Evaluator not available: {e}")
        except Exception as e:
            print(f"✗ Auto-evaluation failed for essay {self.id}: {e}")
    
    def get_absolute_url(self):
        """Get URL for this essay"""
        if self.status == 'accepted':
            return reverse('competition:essay_result', kwargs={'pk': self.pk})
        elif self.status == 'draft':
            return reverse('competition:submit_essay', kwargs={'pk': self.competition.pk}) + f'?draft={self.pk}'
        else:
            return reverse('competition:detail', kwargs={'pk': self.competition.pk})
    
    def get_score_breakdown(self):
        """Get score breakdown as dictionary"""
        return {
            'title_relevance': {
                'score': self.title_relevance_score,
                'weight': 0.30,
                'weighted': self.title_relevance_score * 0.30
            },
            'cohesion': {
                'score': self.cohesion_score,
                'weight': 0.30,
                'weighted': self.cohesion_score * 0.30
            },
            'grammar': {
                'score': self.grammar_score,
                'weight': 0.25,
                'weighted': self.grammar_score * 0.25
            },
            'structure': {
                'score': self.structure_score,
                'weight': 0.15,
                'weighted': self.structure_score * 0.15
            },
            'total': self.total_score
        }
    
    def get_grade(self):
        """Get letter grade based on total score"""
        if self.total_score >= 90:
            return 'A+', 'Excellent'
        elif self.total_score >= 80:
            return 'A', 'Very Good'
        elif self.total_score >= 70:
            return 'B+', 'Good'
        elif self.total_score >= 60:
            return 'B', 'Above Average'
        elif self.total_score >= 50:
            return 'C', 'Average'
        elif self.total_score >= 40:
            return 'D', 'Below Average'
        else:
            return 'F', 'Needs Improvement'
    
    @classmethod
    def get_user_rank(cls, competition_id, user, essay_id=None):
        """Get user's rank in a competition"""
        from django.db.models import Count
        
        # Get all accepted essays for this competition
        accepted_essays = cls.objects.filter(
            competition_id=competition_id,
            status='accepted'
        )
        
        if essay_id:
            # Get specific essay's score
            try:
                target_essay = cls.objects.get(id=essay_id)
                target_score = target_essay.total_score
            except cls.DoesNotExist:
                return None
        else:
            # Get user's highest score in this competition
            user_essays = accepted_essays.filter(user=user)
            if not user_essays.exists():
                return None
            target_score = user_essays.order_by('-total_score').first().total_score
        
        # Count essays with higher scores
        rank = accepted_essays.filter(total_score__gt=target_score).count() + 1
        
        return rank
    
    @classmethod
    def get_competition_stats(cls, competition_id):
        """Get statistics for a competition"""
        from django.db.models import Avg, Max, Min, Count
        
        stats = cls.objects.filter(
            competition_id=competition_id,
            status='accepted'
        ).aggregate(
            total_count=Count('id'),
            avg_score=Avg('total_score'),
            max_score=Max('total_score'),
            min_score=Min('total_score'),
            avg_words=Avg('stored_word_count')
        )
        
        return {
            'total_participants': stats['total_count'] or 0,
            'average_score': round(stats['avg_score'] or 0, 2),
            'highest_score': round(stats['max_score'] or 0, 2),
            'lowest_score': round(stats['min_score'] or 0, 2),
            'average_word_count': round(stats['avg_words'] or 0, 0),
        }

