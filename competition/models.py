# competition/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date 
from django.urls import reverse

class EssayCompetition(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateField()
    eligibility = models.CharField(max_length=100)
    prize = models.CharField(max_length=100)
    button_text = models.CharField(max_length=50, default="Start Writing")
    button_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    rules = models.TextField(blank=True)
    submission_guidelines = models.TextField(blank=True)
    evaluation_criteria = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    max_words = models.IntegerField(default=2000)
    min_words = models.IntegerField(default=500)
    
    class Meta:
        ordering = ['order', '-is_featured', '-created_at']
    
    def __str__(self):
        return self.title
    
    def is_open(self):
        today = date.today()
        return self.deadline >= today
    
    def days_left(self):
        today = date.today()
        if self.deadline >= today:
            days = (self.deadline - today).days
            return max(days, 0)
        else:
            return -1
    
    def get_absolute_url(self):
        return reverse('competition:detail', kwargs={'pk': self.pk})


class Essay(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),  # User is still writing
        ('submitted', 'Submitted'),  # User submitted for review
        ('pending_review', 'Pending Review'),  # Admin hasn't reviewed yet
        ('accepted', 'Accepted'),  # Admin accepted
        ('rejected', 'Rejected'),  # Admin rejected
    ]
    
    competition = models.ForeignKey(EssayCompetition, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    html_content = models.TextField()
    language = models.CharField(max_length=10, choices=[('en', 'English'), ('ne', 'Nepali')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    word_count = models.IntegerField(default=0)
    character_count = models.IntegerField(default=0)
    
    # STATUS FIELDS
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                    null=True, blank=True, related_name='reviewed_essays')
    admin_notes = models.TextField(blank=True)
    grammar_score = models.FloatField(null=True, blank=True)
    plagiarism_score = models.FloatField(null=True, blank=True)
    originality_score = models.FloatField(null=True, blank=True)
    total_score = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Essays"
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def can_edit(self):
        """Check if essay can be edited"""
        return self.status in ['draft', 'rejected']
    
    def is_final(self):
        """Check if essay is in final state"""
        return self.status == 'accepted'