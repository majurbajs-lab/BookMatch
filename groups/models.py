"""Modeli aplikacije groups.

Posodobljeno za Fazo 5A: skupine imajo možno polje region.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from books.models import Genre
from core.regions import REGION_CHOICES_FOR_GROUP, REGION_ALL


class ReadingGroup(models.Model):
    """Skupina bralcev okoli določene teme (žanra, regije, avtorja)."""

    VISIBILITY_CHOICES = [
        ('public', 'Javna'),
        ('private', 'Zasebna'),
    ]

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Ime skupine',
    )
    slug = models.SlugField(
        max_length=170,
        unique=True,
        blank=True,
        verbose_name='URL oznaka',
    )
    description = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name='Opis skupine',
    )
    genres = models.ManyToManyField(
        Genre,
        related_name='groups',
        blank=True,
        verbose_name='Povezane zvrsti',
    )
    region = models.CharField(
        max_length=30,
        choices=REGION_CHOICES_FOR_GROUP,
        default=REGION_ALL,
        verbose_name='Regija',
        help_text='Izberi »Vse regije«, če skupina ni vezana na konkretno regijo.',
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='public',
        verbose_name='Vidnost',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_groups',
        verbose_name='Lastnik',
    )
    cover_image = models.ImageField(
        upload_to='group_covers/',
        blank=True,
        null=True,
        verbose_name='Naslovnica skupine',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Skupina'
        verbose_name_plural = 'Skupine'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.memberships.filter(is_approved=True).count()

    @property
    def genres_list(self):
        return ', '.join(g.name for g in self.genres.all())

    @property
    def region_label(self):
        from core.regions import region_label
        return region_label(self.region)

    @property
    def is_regional(self):
        return self.region and self.region != REGION_ALL

    def is_member(self, user):
        if not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, is_approved=True).exists()

    def has_pending_request(self, user):
        if not user.is_authenticated:
            return False
        return self.memberships.filter(user=user, is_approved=False).exists()


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('member', 'Član'),
        ('moderator', 'Moderator'),
        ('owner', 'Lastnik'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
    )
    group = models.ForeignKey(
        ReadingGroup,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_approved = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Članstvo'
        verbose_name_plural = 'Članstva'
        unique_together = ('user', 'group')
        ordering = ['-joined_at']

    def __str__(self):
        status = '' if self.is_approved else ' (čaka)'
        return f'{self.user.username} → {self.group.name}{status}'


class GroupMessage(models.Model):
    group = models.ForeignKey(
        ReadingGroup, on_delete=models.CASCADE, related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_messages',
    )
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sporočilo v skupini'
        verbose_name_plural = 'Sporočila v skupini'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.username} v {self.group.name}: {self.content[:50]}'
