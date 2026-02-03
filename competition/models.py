from django.db import models
from django.conf import settings
from django.urls import reverse
from datetime import date

class EssayCompetition(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    topic = models.TextField(help_text="Main topic/theme for relevance evaluation")
    deadline = models.DateField()
    eligibility = models.CharField(max_length=100)
    prize = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For evaluation criteria
    min_words = models.IntegerField(default=250)
    max_words = models.IntegerField(default=500)
    
    class Meta:
        ordering = ['-created_at']  # REMOVED: 'order', '-is_featured'
    
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
    
    competition = models.ForeignKey(EssayCompetition, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='reviewed_essays')
    admin_notes = models.TextField(blank=True)
    
    # EVALUATION FIELDS
    topic_score = models.FloatField(default=0.0)
    cohesion_score = models.FloatField(default=0.0)
    grammar_score = models.FloatField(default=0.0)
    structure_score = models.FloatField(default=0.0)
    total_score = models.FloatField(default=0.0)
    
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-total_score']
        indexes = [
            models.Index(fields=['status', 'total_score']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @property
    def word_count(self):
        return len(self.content.strip().split())