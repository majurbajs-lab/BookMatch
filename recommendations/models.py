"""Modeli aplikacije recommendations.

Shranjujemo rezultate priporočilnega modela v bazo, da so prikazi v vmesniku
hitri (brez vsakokratnega preračuna). Priporočila se osvežijo z ukazom
`python manage.py train_recommender`.
"""

from django.conf import settings
from django.db import models

from books.models import Book


class Recommendation(models.Model):
    """Shranjeno priporočilo knjige za uporabnika, ki ga je izračunal UI model."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name='Uporabnik',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name='Priporočena knjiga',
    )
    score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        verbose_name='Ocena relevantnosti',
        help_text='Kosinusna podobnost (0–1).',
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Razlog priporočila',
    )
    is_dismissed = models.BooleanField(
        default=False,
        verbose_name='Uporabnik zavrnil',
        help_text='Če je True, predloga ne prikažemo več.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Priporočilo'
        verbose_name_plural = 'Priporočila'
        unique_together = ('user', 'book')
        ordering = ['-score']

    def __str__(self):
        return f'{self.user.username} → {self.book.title} ({self.score})'
