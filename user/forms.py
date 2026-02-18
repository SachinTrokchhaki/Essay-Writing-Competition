# user/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re
from datetime import date

User = get_user_model()


# ---------------- LOGIN FORM ----------------
class UserLoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)


# ---------------- REGISTER FORM ----------------
class UserRegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'id': 'password1'
        }),
        min_length=8,
        label="Password"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'id': 'password2'
        }),
        label="Confirm Password"
    )
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'terms'})
    )
    
    # Document field
    identity_doc = forms.FileField(
        required=True,
        label="Identity Document (Citizenship/NIN)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'identity_doc',
            'accept': '.pdf,.jpg,.jpeg,.png',
            'data-max-size': '5242880'
        }),
        help_text="Upload your citizenship or NIN (PDF, JPG, PNG - max 5MB)"
    )
    
    # Date of birth
    dob = forms.DateField(
        required=True,
        label="Date of Birth",
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'id': 'dob',
            'type': 'date',
            'max': '2008-12-31'
        }),
        help_text="You must be at least 16 years old"
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'username', 
            'country', 'dob', 'identity_doc'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'first_name',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'last_name',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'email',
                'placeholder': 'your.email@example.com'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'username',
                'placeholder': 'Choose a username'
            }),
            'country': forms.Select(attrs={
                'class': 'form-select',
                'id': 'country'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        
        # Check length
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        
        if len(username) > 20:
            raise ValidationError("Username must be less than 20 characters")
            
        # Check characters
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Only letters, numbers, and underscores allowed")
        
        # Check if exists
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already taken")

        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        
        # Basic email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Enter a valid email address")
        
        # Check if exists
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already registered")
        
        return email
    
    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if not first_name or len(first_name.strip()) < 2:
            raise ValidationError("First name must be at least 2 characters")
        if not re.match(r'^[a-zA-Z\s]+$', first_name):
            raise ValidationError("First name can only contain letters and spaces")
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        if not last_name or len(last_name.strip()) < 2:
            raise ValidationError("Last name must be at least 2 characters")
        if not re.match(r'^[a-zA-Z\s]+$', last_name):
            raise ValidationError("Last name can only contain letters and spaces")
        return last_name
    
    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 16:
                raise ValidationError(f"You must be at least 16 years old (you are {age})")
            if age > 100:
                raise ValidationError("Please enter a valid date of birth")
        return dob
    
    def clean_identity_doc(self):
        doc = self.cleaned_data.get('identity_doc')
        if doc:
            # Check file size (max 5MB)
            if doc.size > 5 * 1024 * 1024:
                raise ValidationError(f"File too large ({doc.size / (1024*1024):.1f}MB). Max 5MB allowed")
            
            # Check file extension
            ext = doc.name.split('.')[-1].lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                raise ValidationError(f"Invalid file type '.{ext}'. Only PDF, JPG, JPEG, PNG allowed")
            
            # Check filename
            if len(doc.name) > 100:
                raise ValidationError("Filename too long")
        return doc

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        
        # Check length
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        # Check for uppercase
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        # Check for lowercase
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        # Check for number
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one number")
        
        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = ['password123', '12345678', 'qwerty123', 'admin123']
        if password.lower() in common_passwords:
            raise ValidationError("This password is too common. Choose a stronger one")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
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
            'country': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Email already in use")
        return email