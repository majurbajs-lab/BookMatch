"""Django signali za aplikacijo reading.

Ob vsakem dodajanju, spreminjanju ali brisanju ocene samodejno posodobimo
povprečno oceno in število ocen na povezani knjigi ter sprožimo ML trening,
ko se transakcija zaključi.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Rating


@receiver(post_save, sender=Rating)
def update_book_rating_on_save(sender, instance, **kwargs):
    instance.book.update_rating_stats()
    transaction.on_commit(_maybe_auto_train)


@receiver(post_delete, sender=Rating)
def update_book_rating_on_delete(sender, instance, **kwargs):
    instance.book.update_rating_stats()
    transaction.on_commit(_maybe_auto_train)


def _maybe_auto_train():
    try:
        from ml.auto_train import maybe_train_matcher, maybe_train_recommender
        maybe_train_recommender()
        maybe_train_matcher()
    except Exception:
        pass
