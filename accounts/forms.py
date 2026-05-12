"""Obrazci za aplikacijo accounts.

Posodobljeno za Fazo 5A: regija se zbira že pri registraciji.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from core.regions import REGION_CHOICES
from .models import Profile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """Obrazec za registracijo z e-naslovom in izbiro regije."""

    email = forms.EmailField(
        required=True,
        label='E-naslov',
        help_text='Na ta naslov lahko prejmeš obvestila.',
    )
    region = forms.ChoiceField(
        choices=REGION_CHOICES,
        required=True,
        label='Regija',
        help_text='Pomembno za izposojo in predlaganje regijskih skupin.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Uporabniško ime',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ta e-naslov je že v uporabi.')
        return email

    def clean_region(self):
        region = self.cleaned_data.get('region')
        if not region:
            raise forms.ValidationError('Izberi regijo.')
        return region

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Profil je ustvarjen prek signalov – posodobimo regijo
            if hasattr(user, 'profile'):
                user.profile.region = self.cleaned_data['region']
                user.profile.save(update_fields=['region'])
        return user


class ProfileForm(forms.ModelForm):
    """Obrazec za urejanje profila."""

    class Meta:
        model = Profile
        fields = ('bio', 'avatar', 'region', 'location', 'is_public', 'show_in_matches')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 300}),
        }
        labels = {
            'bio': 'O meni',
            'avatar': 'Profilna slika',
            'region': 'Regija',
            'location': 'Konkreten kraj (neobvezno)',
            'is_public': 'Javni profil',
            'show_in_matches': 'Sodeluj v sistemu ujemanj',
        }


class UserForm(forms.ModelForm):
    """Obrazec za urejanje osnovnih podatkov uporabnika."""

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Uporabniško ime',
            'first_name': 'Ime',
            'last_name': 'Priimek',
            'email': 'E-naslov',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ta e-naslov je že v uporabi.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('To uporabniško ime je že zasedeno.')
        return username
