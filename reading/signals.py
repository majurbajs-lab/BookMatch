"""Django signali za aplikacijo reading.

Ob vsakem dodajanju, spreminjanju ali brisanju ocene samodejno posodobimo
povprečno oceno in število ocen na povezani knjigi ter sprožimo ML trening
v ozadju, če so pogoji izpolnjeni.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Rating


@receiver(post_save, sender=Rating)
def update_book_rating_on_save(sender, instance, **kwargs):
    """Posodobi statistike knjige, ko se ocena doda/spremeni."""
    instance.book.update_rating_stats()
    _maybe_auto_train()


@receiver(post_delete, sender=Rating)
def update_book_rating_on_delete(sender, instance, **kwargs):
    """Posodobi statistike knjige, ko se ocena izbriše."""
    instance.book.update_rating_stats()
    _maybe_auto_train()


def _maybe_auto_train():
    try:
        from ml.auto_train import maybe_train_matcher, maybe_train_recommender
        maybe_train_recommender()
        maybe_train_matcher()
    except Exception:
        pass  # trening ne sme prekiniti normalne obdelave zahteve
