"""Django signali za aplikacijo accounts.

Ob vsaki ustvaritvi novega uporabnika (User) samodejno ustvarimo
pripadajoč Profile. To zagotavlja, da ima vsak uporabnik svoj profil.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Samodejno ustvari Profile ob registraciji novega uporabnika."""
    if created:
        Profile.objects.create(user=instance)
