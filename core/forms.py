# core/forms.py
from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'message']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to form fields
        self.fields['name'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Your name'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-input',
            'placeholder': 'Your email'
        })
        self.fields['message'].widget.attrs.update({
            'class': 'form-input',
            'rows': 5,
            'placeholder': 'Your message...'
        })
        
        # Auto-fill for logged-in users
        if self.user and self.user.is_authenticated:
            if self.user.first_name or self.user.last_name:
                self.fields['name'].initial = f"{self.user.first_name} {self.user.last_name}"
            else:
                self.fields['name'].initial = self.user.username
            self.fields['email'].initial = self.user.email