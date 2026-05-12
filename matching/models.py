"""Modeli aplikacije matching.

Shranjujemo rezultate UI modela gručenja bralcev:
- UserMatch: ujemanje med dvema uporabnikoma (kot "Tinder za knjige")
- GroupSuggestion: predlog skupine za uporabnika na podlagi žanrov
"""

from django.conf import settings
from django.db import models

from groups.models import ReadingGroup


class UserMatch(models.Model):
    """Ujemanje med dvema uporabnikoma na osnovi bralnega okusa (K-Means)."""

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_a',
        verbose_name='Uporabnik A',
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_b',
        verbose_name='Uporabnik B',
    )
    similarity_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        verbose_name='Podobnost',
        help_text='Kosinusna podobnost bralnih profilov (0–1).',
    )
    shared_genres = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Skupni žanri',
        help_text='Besedilni opis skupnih najljubših žanrov (za razlago).',
    )
    cluster_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID gruče',
        help_text='V kateri gruči se nahajata oba uporabnika.',
    )
    is_dismissed = models.BooleanField(
        default=False,
        verbose_name='Uporabnik skril',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ujemanje bralcev'
        verbose_name_plural = 'Ujemanja bralcev'
        unique_together = ('user_a', 'user_b')
        ordering = ['-similarity_score']

    def __str__(self):
        return f'{self.user_a.username} ↔ {self.user_b.username}: {self.similarity_score}'


class GroupSuggestion(models.Model):
    """Predlagana skupina za uporabnika (na osnovi žanrskega ujemanja)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_suggestions',
        verbose_name='Uporabnik',
    )
    group = models.ForeignKey(
        ReadingGroup,
        on_delete=models.CASCADE,
        related_name='suggestions',
        verbose_name='Predlagana skupina',
    )
    match_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        verbose_name='Stopnja ujemanja',
        help_text='0–1, koliko žanri skupine ustrezajo uporabnikovemu okusu.',
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Razlog predloga',
    )
    is_dismissed = models.BooleanField(
        default=False,
        verbose_name='Uporabnik skril',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Predlagana skupina'
        verbose_name_plural = 'Predlagane skupine'
        unique_together = ('user', 'group')
        ordering = ['-match_score']

    def __str__(self):
        return f'{self.user.username} → {self.group.name} ({self.match_score})'
