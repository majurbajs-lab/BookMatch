"""Django signali za aplikacijo reading.

Ob vsakem dodajanju, spreminjanju ali brisanju ocene samodejno posodobimo
povprečno oceno in število ocen na povezani knjigi.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Rating


@receiver(post_save, sender=Rating)
def update_book_rating_on_save(sender, instance, **kwargs):
    """Posodobi statistike knjige, ko se ocena doda/spremeni."""
    instance.book.update_rating_stats()


@receiver(post_delete, sender=Rating)
def update_book_rating_on_delete(sender, instance, **kwargs):
    """Posodobi statistike knjige, ko se ocena izbriše."""
    instance.book.update_rating_stats()
