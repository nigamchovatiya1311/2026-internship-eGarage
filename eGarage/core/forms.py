from django.contrib.auth.forms import UserCreationForm  
from django import forms
from .models import User


class UserSignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email', 'role', 'password1', 'password2']
        
        widgets = {
            'password1': forms.PasswordInput(), # Use PasswordInput widget for password fields
            'password2': forms.PasswordInput(),
        }


class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

