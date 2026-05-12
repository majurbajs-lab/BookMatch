"""Obrazci za aplikacijo groups.

Posodobljeno za Fazo 5A: regija pri ustvarjanju skupine.
"""

from django import forms

from .models import GroupMessage, ReadingGroup


class GroupForm(forms.ModelForm):
    """Obrazec za ustvarjanje ali urejanje skupine."""

    class Meta:
        model = ReadingGroup
        fields = ('name', 'description', 'region', 'genres', 'visibility', 'cover_image')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'genres': forms.CheckboxSelectMultiple,
        }
        labels = {
            'name': 'Ime skupine',
            'description': 'Opis',
            'region': 'Regija',
            'genres': 'Zvrsti (za ujemanje z bralci)',
            'visibility': 'Vidnost',
            'cover_image': 'Naslovnica (neobvezno)',
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = GroupMessage
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Napiši sporočilo ...',
                'maxlength': 2000,
            }),
        }
        labels = {
            'content': '',
        }