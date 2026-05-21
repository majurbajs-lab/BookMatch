"""Django signali za aplikacijo reading."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Rating


@receiver(post_save, sender=Rating)
def update_book_rating_on_save(sender, instance, **kwargs):
    instance.book.update_rating_stats()


@receiver(post_delete, sender=Rating)
def update_book_rating_on_delete(sender, instance, **kwargs):
    instance.book.update_rating_stats()
