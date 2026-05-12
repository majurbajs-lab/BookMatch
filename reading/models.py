"""Modeli aplikacije reading.

Vsebuje bralno evidenco, ocene, recenzije in uporabniške sezname.
Podatki iz teh modelov so ključni vhod za UI modela (priporočila, ujemanje).
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from books.models import Book


class ReadingEntry(models.Model):
    """Uporabnikova bralna evidenca – katere knjige je v katerem statusu."""

    STATUS_CHOICES = [
        ('want', 'Želim brati'),
        ('reading', 'Trenutno berem'),
        ('read', 'Prebrano'),
        ('dropped', 'Opustil'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_entries',
        verbose_name='Uporabnik',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reading_entries',
        verbose_name='Knjiga',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='want',
        verbose_name='Status',
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum začetka branja',
    )
    finish_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Datum zaključka',
    )
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Napredek (%)',
        help_text='Odstotek prebranega (0-100).',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Zapis v evidenci'
        verbose_name_plural = 'Zapisi v evidenci'
        unique_together = ('user', 'book')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username}: {self.book.title} ({self.get_status_display()})'


class Rating(models.Model):
    """Ocena knjige (1.0 - 5.0, polovične ocene dovoljene)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='Uporabnik',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name='Knjiga',
    )
    score = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        verbose_name='Ocena',
        help_text='Od 1.0 do 5.0 (polovične ocene dovoljene).',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ocena'
        verbose_name_plural = 'Ocene'
        unique_together = ('user', 'book')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} → {self.book.title}: {self.score}'


class Review(models.Model):
    """Besedilna recenzija knjige."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Avtor recenzije',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Knjiga',
    )
    content = models.TextField(
        max_length=5000,
        verbose_name='Vsebina recenzije',
    )
    likes_count = models.IntegerField(
        default=0,
        verbose_name='Število všečkov',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recenzija'
        verbose_name_plural = 'Recenzije'
        ordering = ['-created_at']
        # Uporabnik ima lahko samo eno recenzijo na knjigo
        unique_together = ('user', 'book')

    def __str__(self):
        return f'Recenzija: {self.book.title} (avtor: {self.user.username})'


class HomeBook(models.Model):
    """Knjiga, ki jo ima uporabnik fizično doma – vidno vsem."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='home_books',
        verbose_name='Lastnik',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='home_books',
        verbose_name='Knjiga',
    )
    notes = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Opomba',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Knjiga v domači knjižnici'
        verbose_name_plural = 'Knjige v domači knjižnici'
        unique_together = ('user', 'book')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.user.username}: {self.book.title}'


class ReadingList(models.Model):
    """Uporabnikov lastni seznam knjig (npr. "Poletno branje 2026")."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_lists',
        verbose_name='Lastnik',
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Ime seznama',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Opis',
    )
    books = models.ManyToManyField(
        Book,
        related_name='in_reading_lists',
        blank=True,
        verbose_name='Knjige',
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name='Javni seznam',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Seznam branja'
        verbose_name_plural = 'Seznami branja'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.user.username})'
