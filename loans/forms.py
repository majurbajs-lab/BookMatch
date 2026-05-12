"""Obrazci za aplikacijo loans."""

from django import forms

from .models import LoanOffer, LoanRequest, LoanReview


class LoanOfferForm(forms.ModelForm):
    class Meta:
        model = LoanOffer
        fields = ('condition', 'max_loan_days', 'notes')
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Npr. dobavim v središče Ljubljane, imam podpis avtorja ...',
            }),
        }
        labels = {
            'condition': 'Stanje izvoda',
            'max_loan_days': 'Največja doba izposoje (dni)',
            'notes': 'Opombe (neobvezno)',
        }


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = LoanRequest
        fields = ('message',)
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Zakaj te knjiga zanima? (neobvezno)',
            }),
        }
        labels = {
            'message': 'Spremno sporočilo',
        }


class LoanReviewForm(forms.ModelForm):
    class Meta:
        model = LoanReview
        fields = ('score', 'comment')
        widgets = {
            'score': forms.Select(choices=[(i, f'{i} zvezdic' if i != 1 else '1 zvezdica') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Kratka ocena izkušnje (neobvezno)',
            }),
        }
        labels = {
            'score': 'Ocena',
            'comment': 'Komentar',
        }
