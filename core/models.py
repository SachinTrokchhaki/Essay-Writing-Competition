from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    admin_reply = models.TextField(
        blank=True, 
        null=True, 
        help_text="Admin's reply to the user (will be displayed on homepage)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    show_on_homepage = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Feedback from {self.name}"
    
    @property
    def has_reply(self):
        """Check if feedback has admin reply"""
        return bool(self.admin_reply and self.admin_reply.strip())
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Feedback'
        verbose_name_plural = 'User Feedback'