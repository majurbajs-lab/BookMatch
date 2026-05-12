"""Modeli aplikacije books.

Vsebuje katalog knjig: Author, Genre in Book.
Ti podatki so vhod za oba UI modela v kasnejših fazah.
"""

from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    """Zvrst knjige (npr. znanstvena fantastika, krimi, biografija)."""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Ime zvrsti',
    )
    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        verbose_name='URL oznaka',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Zvrst'
        verbose_name_plural = 'Zvrsti'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Author(models.Model):
    """Avtor knjige."""

    name = models.CharField(
        max_length=200,
        verbose_name='Ime in priimek',
    )
    bio = models.TextField(
        blank=True,
        verbose_name='Biografija',
    )
    birth_year = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Leto rojstva',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Avtor'
        verbose_name_plural = 'Avtorji'
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    """Knjiga v katalogu."""

    LANGUAGE_CHOICES = [
        ('sl', 'Slovenščina'),
        ('en', 'Angleščina'),
        ('de', 'Nemščina'),
        ('fr', 'Francoščina'),
        ('it', 'Italijanščina'),
        ('es', 'Španščina'),
        ('hr', 'Hrvaščina'),
        ('sr', 'Srbščina'),
        ('other', 'Drugo'),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name='Naslov',
    )
    authors = models.ManyToManyField(
        Author,
        related_name='books',
        verbose_name='Avtorji',
    )
    isbn = models.CharField(
        max_length=13,
        blank=True,
        verbose_name='ISBN',
        help_text='13-mestna številka ISBN (neobvezno).',
    )
    publication_year = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Leto izdaje',
    )
    publisher = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Založba',
    )
    genres = models.ManyToManyField(
        Genre,
        related_name='books',
        blank=True,
        verbose_name='Zvrsti',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Opis',
        help_text='Kratek opis vsebine knjige.',
    )
    cover_image = models.ImageField(
        upload_to='book_covers/',
        blank=True,
        null=True,
        verbose_name='Naslovnica',
    )
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='sl',
        verbose_name='Jezik',
    )
    page_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Število strani',
    )

    # Izračunano polje – se posodobi ob vsakem dodajanju/spreminjanju ocene
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        verbose_name='Povprečna ocena',
    )
    ratings_count = models.IntegerField(
        default=0,
        verbose_name='Število ocen',
    )

    is_approved = models.BooleanField(
        default=True,
        verbose_name='Potrjeno',
        help_text='Knjige, ki jih dodajo uporabniki, mora potrditi administrator.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Knjiga'
        verbose_name_plural = 'Knjige'
        ordering = ['title']

    def __str__(self):
        return self.title

    def authors_list(self):
        """Vrne avtorje kot niz, ločen z vejicami."""
        return ', '.join([a.name for a in self.authors.all()])

    def genres_list(self):
        """Vrne zvrsti kot niz, ločen z vejicami."""
        return ', '.join([g.name for g in self.genres.all()])

    def update_rating_stats(self):
        """Preračuna povprečno oceno in število ocen.

        Kliče se po vsakem dodajanju, spreminjanju ali brisanju ocene.
        """
        from reading.models import Rating
        from django.db.models import Avg, Count

        stats = Rating.objects.filter(book=self).aggregate(
            avg=Avg('score'),
            count=Count('id')
        )
        self.average_rating = stats['avg'] or 0.0
        self.ratings_count = stats['count'] or 0
        self.save(update_fields=['average_rating', 'ratings_count'])
