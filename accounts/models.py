"""Modeli aplikacije accounts.

Posodobljeno za Fazo 5A: dodano polje region v profil.
"""

from django.conf import settings
from django.db import models

from core.regions import REGION_CHOICES


class Profile(models.Model):
    """Razširitev Django uporabnika z dodatnimi profilnimi podatki."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Uporabnik',
    )
    bio = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Kratka biografija',
        help_text='Do 300 znakov.',
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Profilna slika',
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Kraj (neobvezno)',
        help_text='Npr. konkreten kraj, če želiš to povedati drugim bralcem.',
    )
    region = models.CharField(
        max_length=30,
        choices=REGION_CHOICES,
        blank=True,
        default='',
        verbose_name='Regija',
        help_text='Tvoja statistična regija (uporablja se za izposojo in predlaganje regijskih skupin).',
    )

    # Za Fazo 5 – izposoja
    reliability_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        verbose_name='Ocena zanesljivosti',
        help_text='Povprečje ocen po izposojah.',
    )
    reliability_count = models.IntegerField(
        default=0,
        verbose_name='Število ocen zanesljivosti',
    )

    # Za Fazo 4
    cluster_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Gruča (UI model)',
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name='Javni profil',
    )
    show_in_matches = models.BooleanField(
        default=True,
        verbose_name='Sodeluj v sistemu ujemanj',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profili'

    def __str__(self):
        return f'Profil: {self.user.username}'

    def update_reliability(self):
        """Preračuna povprečno oceno zanesljivosti na osnovi prejetih ocen po izposojah."""
        from loans.models import LoanReview
        reviews = LoanReview.objects.filter(reviewee=self.user)
        count = reviews.count()
        if count > 0:
            from django.db.models import Avg
            avg = reviews.aggregate(a=Avg('score'))['a'] or 0
            self.reliability_score = round(float(avg), 2)
            self.reliability_count = count
        else:
            self.reliability_score = 0
            self.reliability_count = 0
        self.save(update_fields=['reliability_score', 'reliability_count'])