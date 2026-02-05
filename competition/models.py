# competition/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from datetime import date

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
    
    # Use string reference since EssayCompetition is now defined above
    competition = models.ForeignKey('EssayCompetition', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    html_content = models.TextField(blank=True)  # For rich text content
    language = models.CharField(max_length=10, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Database fields for querying
    stored_word_count = models.IntegerField(default=0)
    stored_character_count = models.IntegerField(default=0)
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='reviewed_essays')
    admin_notes = models.TextField(blank=True)
    
    # EVALUATION FIELDS
    title_relevance_score = models.FloatField(default=0.0)
    cohesion_score = models.FloatField(default=0.0)
    grammar_score = models.FloatField(default=0.0)
    structure_score = models.FloatField(default=0.0)
    total_score = models.FloatField(default=0.0)
    
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-total_score']
        indexes = [
            models.Index(fields=['status', 'total_score']),
            models.Index(fields=['stored_word_count']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
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
            
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """Get URL for this essay"""
        return reverse('competition:essay_result', kwargs={'pk': self.pk})