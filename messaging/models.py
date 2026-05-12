"""Modeli za zasebne pogovore 1-na-1.

Conversation: vsebuje točno dva udeleženca in zaporedje sporočil.
Message: posamezno sporočilo. Lahko je običajno (od uporabnika) ali sistemsko
(samodejno generirano ob dogodkih, kot je npr. prošnja za izposojo).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Conversation(models.Model):
    """Zasebni pogovor med dvema uporabnikoma.

    Med dvema uporabnikoma je vedno samo en pogovor (brez podvajanja).
    """

    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_a',
    )
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_b',
    )

    # Zadnja aktivnost (za razvrstitev seznama pogovorov)
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Zadnje sporočilo',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pogovor'
        verbose_name_plural = 'Pogovori'
        ordering = ['-last_message_at', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=~Q(participant_a=models.F('participant_b')),
                name='messaging_conversation_different_participants',
            ),
        ]

    def __str__(self):
        return f'{self.participant_a.username} ↔ {self.participant_b.username}'

    @classmethod
    def get_or_create_between(cls, user_a, user_b):
        """Vrne obstoječi pogovor ali ustvari novega med dvema uporabnikoma."""
        if user_a.id == user_b.id:
            raise ValueError('Pogovor s samim seboj ni mogoč.')

        # Normaliziramo vrstni red za doslednost
        first, second = sorted([user_a, user_b], key=lambda u: u.id)

        conversation = cls.objects.filter(
            (Q(participant_a=first) & Q(participant_b=second))
            | (Q(participant_a=second) & Q(participant_b=first))
        ).first()

        if conversation:
            return conversation, False

        conversation = cls.objects.create(participant_a=first, participant_b=second)
        return conversation, True

    def other_participant(self, user):
        """Vrne drugega udeleženca pogovora glede na danega uporabnika."""
        if user == self.participant_a:
            return self.participant_b
        return self.participant_a

    def unread_count_for(self, user):
        """Vrne število neprebranih sporočil za tega uporabnika."""
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    """Posamezno sporočilo v pogovoru."""

    KIND_CHOICES = [
        ('user', 'Uporabniško'),
        ('system', 'Sistemsko'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='private_messages_sent',
        null=True,
        blank=True,
        help_text='Null pri sistemskih sporočilih.',
    )
    kind = models.CharField(
        max_length=10,
        choices=KIND_CHOICES,
        default='user',
        verbose_name='Vrsta',
    )
    content = models.TextField(
        max_length=2000,
        verbose_name='Vsebina',
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Prebrano',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sporočilo'
        verbose_name_plural = 'Sporočila'
        ordering = ['created_at']

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'SISTEM'
        return f'{sender_name}: {self.content[:50]}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Posodobi zadnjo aktivnost pogovora
        self.conversation.last_message_at = self.created_at
        self.conversation.save(update_fields=['last_message_at'])


def send_system_message(conversation: Conversation, content: str) -> Message:
    """Priročna funkcija za pošiljanje sistemskega sporočila.

    Uporabljajo jo drugi moduli (npr. loans) za obveščanje uporabnikov
    o dogodkih, ki se zgodijo v sistemu.
    """
    return Message.objects.create(
        conversation=conversation,
        sender=None,
        kind='system',
        content=content,
        is_read=False,
    )
