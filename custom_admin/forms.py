# custom_admin/forms.py
from django import forms
from competition.models import EssayCompetition, Essay
from core.models import Feedback
from user.models import CustomUser

class EssayCompetitionForm(forms.ModelForm):
    class Meta:
        model = EssayCompetition
        fields = ['title', 'description', 'deadline', 'min_words', 'max_words', 'is_active']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'min_words': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_words': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class EssayForm(forms.ModelForm):
    class Meta:
        model = Essay
        fields = ['title', 'content', 'language', 'status', 'admin_notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'admin_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'message', 'admin_reply', 'status', 'show_on_homepage']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'admin_reply': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'show_on_homepage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CustomUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        required=False,
        help_text="Leave empty to keep current password"
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'dob', 'identity_doc', 
                  'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'dob': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'identity_doc': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        # Handle file upload
        if self.cleaned_data.get('identity_doc'):
            # If there's an existing file and we're uploading a new one,
            # the old file will be automatically deleted by Django
            user.identity_doc = self.cleaned_data['identity_doc']
        
        if commit:
            user.save()
        return user


