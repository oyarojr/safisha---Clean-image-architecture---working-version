from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from .models import Profile

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Email address"
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "First name"
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'password1', 'password2')

        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Username"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = None
        self.fields["password2"].help_text = None

        self.fields["password1"].widget.attrs.update({
            "placeholder": "Password"
        })

        self.fields["password2"].widget.attrs.update({
            "placeholder": "Confirm password"
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'form-control'
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'New password',
            'class': 'form-control'
        }),
        label="New password"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'class': 'form-control'
        }),
        label="Confirm new password"
    )


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "placeholder": "Email (optional)"
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "First name"
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Last name"
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Username"
            }),
        }


class ProfileUpdateForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "placeholder": "Date of Birth"
        })
    )

    class Meta:
        model = Profile
        fields = ['profile_picture', 'bio', 'phone_number', 'location', 'date_of_birth']
        widgets = {
            "bio": forms.Textarea(attrs={
                "placeholder": "Tell us about yourself...",
                "rows": 4
            }),
            "phone_number": forms.TextInput(attrs={
                "placeholder": "Phone number"
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "Location"
            }),
        }