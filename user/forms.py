# user/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re

User = get_user_model()


# ---------------- LOGIN FORM ----------------
class UserLoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)


# ---------------- REGISTER FORM ----------------
class UserRegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        min_length=8,
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )
    terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'username',
            'country',
        ]

    def clean_username(self):
        username = self.cleaned_data['username']

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Only letters, numbers, and underscores allowed")

        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists")

        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already registered")
        return email

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', "Passwords do not match")

        return cleaned_data


# ---------------- PROFILE UPDATE FORM ----------------
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'country']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }
