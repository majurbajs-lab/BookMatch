"""Modeli aplikacije loans.

Vsebuje:
- LoanOffer: lastnikova ponudba knjige za izposojo
- LoanRequest: prošnja drugega uporabnika za izposojo
- LoanReview: medsebojne ocene po vrnitvi knjige
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from books.models import Book


class LoanOffer(models.Model):
    """Ponudba izvoda knjige za izposojo."""

    CONDITION_CHOICES = [
        ('new', 'Novo'),
        ('very_good', 'Zelo dobro'),
        ('good', 'Dobro'),
        ('poor', 'Slabo (opazna uporaba)'),
    ]

    STATUS_CHOICES = [
        ('available', 'Na voljo'),
        ('reserved', 'Rezervirano'),
        ('borrowed', 'Izposojeno'),
        ('inactive', 'Neaktivno'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_offers',
        verbose_name='Lastnik',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='loan_offers',
        verbose_name='Knjiga',
    )
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='good',
        verbose_name='Stanje izvoda',
    )
    max_loan_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        verbose_name='Največja doba izposoje (dni)',
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Dodatne opombe',
        help_text='Npr. podpis avtorja, zapiski v knjigi, posebni pogoji prevzema.',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='Status',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ponudba izposoje'
        verbose_name_plural = 'Ponudbe izposoje'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.book.title} – {self.owner.username} ({self.get_status_display()})'


class LoanRequest(models.Model):
    """Prošnja za izposojo konkretnega izvoda."""

    STATUS_CHOICES = [
        ('pending', 'Čaka na odgovor'),
        ('accepted', 'Sprejeto'),
        ('rejected', 'Zavrnjeno'),
        ('returned', 'Vrnjeno'),
        ('cancelled', 'Preklicano'),
    ]

    offer = models.ForeignKey(
        LoanOffer,
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name='Ponudba',
    )
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_requests',
        verbose_name='Prosilec',
    )
    message = models.TextField(
        blank=True,
        verbose_name='Spremno sporočilo',
        help_text='Zakaj te knjiga zanima?',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status',
    )
    loan_start = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum izposoje',
    )
    loan_end = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum vračila',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prošnja za izposojo'
        verbose_name_plural = 'Prošnje za izposojo'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.borrower.username} → {self.offer.book.title} ({self.get_status_display()})'

    @property
    def owner(self):
        return self.offer.owner

    @property
    def book(self):
        return self.offer.book

    def can_review(self, user):
        """Ali uporabnik lahko pusti oceno za to izposojo?"""
        if self.status != 'returned':
            return False
        if user != self.borrower and user != self.owner:
            return False
        # Je že ocenil?
        return not LoanReview.objects.filter(loan_request=self, reviewer=user).exists()


class LoanReview(models.Model):
    """Medsebojna ocena po zaključeni izposoji."""

    loan_request = models.ForeignKey(
        LoanRequest,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Izposoja',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_reviews_given',
        verbose_name='Ocenjevalec',
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loan_reviews_received',
        verbose_name='Ocenjeni',
    )
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Ocena (1–5)',
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Komentar (neobvezno)',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ocena izposoje'
        verbose_name_plural = 'Ocene izposoje'
        unique_together = ('loan_request', 'reviewer')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reviewer.username} → {self.reviewee.username}: {self.score}/5'
