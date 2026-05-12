"""Obrazci za aplikacijo reading."""

from decimal import Decimal

from django import forms

from .models import Rating, Review


class RatingForm(forms.ModelForm):
    """Obrazec za oceno knjige (0.5 razmik, 1.0-5.0)."""

    score = forms.TypedChoiceField(
        choices=[(str(Decimal(v) / 2), str(Decimal(v) / 2)) for v in range(2, 11)],
        coerce=lambda x: Decimal(x),
        label='Tvoja ocena',
        help_text='Od 1.0 do 5.0.',
    )

    class Meta:
        model = Rating
        fields = ('score',)


class ReviewForm(forms.ModelForm):
    """Obrazec za recenzijo knjige."""

    class Meta:
        model = Review
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 6,
                'maxlength': 5000,
                'placeholder': 'Deli svoje misli o tej knjigi ...',
            }),
        }
        labels = {
            'content': 'Tvoja recenzija',
        }
