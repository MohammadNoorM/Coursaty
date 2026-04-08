from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(label=_('Email Address'), required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')