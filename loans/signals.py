"""Signali za aplikacijo loans.

Ob dogodkih:
- Samodejno preračunamo zanesljivost uporabnika po oceni.
- Pošljemo sistemska sporočila v zasebne pogovore ob ključnih dogodkih:
  prošnja, sprejem/zavrnitev, preklic, vračilo.
"""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import LoanRequest, LoanReview


# ============================================================
# ZANESLJIVOST UPORABNIKA
# ============================================================

@receiver(post_save, sender=LoanReview)
def update_reliability_on_save(sender, instance, **kwargs):
    if hasattr(instance.reviewee, 'profile'):
        instance.reviewee.profile.update_reliability()


@receiver(post_delete, sender=LoanReview)
def update_reliability_on_delete(sender, instance, **kwargs):
    if hasattr(instance.reviewee, 'profile'):
        instance.reviewee.profile.update_reliability()


# ============================================================
# SISTEMSKA SPOROČILA OB DOGODKIH IZPOSOJE
# ============================================================

@receiver(pre_save, sender=LoanRequest)
def remember_old_status(sender, instance, **kwargs):
    """Pred shranjevanjem si zapomnimo, kakšen je bil status prej."""
    if instance.pk:
        try:
            previous = sender.objects.get(pk=instance.pk)
            instance._old_status = previous.status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=LoanRequest)
def notify_on_loan_event(sender, instance, created, **kwargs):
    """Pošlje sistemska sporočila v zasebni pogovor ob dogodkih izposoje."""
    try:
        from messaging.models import Conversation, send_system_message
    except ImportError:
        return  # aplikacija messaging ni naložena (npr. v testih)

    owner = instance.offer.owner
    borrower = instance.borrower
    book_title = instance.offer.book.title

    # Ustvari ali pridobi pogovor med lastnikom in izposojevalcem
    conversation, _ = Conversation.get_or_create_between(owner, borrower)

    # 1. Nova prošnja
    if created:
        send_system_message(
            conversation,
            f'📬 {borrower.username} je zaprosil/-a za izposojo knjige »{book_title}«.'
            + (f' Spremno sporočilo: "{instance.message}"' if instance.message else '')
            + ' Lastnik lahko prošnjo sprejme ali zavrne v razdelku »Moje izposoje«.'
        )
        return

    # 2. Sprememba statusa (sprejem/zavrnitev/preklic/vračilo)
    old_status = getattr(instance, '_old_status', None)
    if old_status == instance.status:
        return  # ni spremembe

    if instance.status == 'accepted':
        send_system_message(
            conversation,
            f'✅ Prošnja za »{book_title}« je SPREJETA. Dogovorita se za prevzem '
            f'v tem pogovoru. Rok vračila: {instance.loan_end.strftime("%d. %m. %Y") if instance.loan_end else "—"}.'
        )
    elif instance.status == 'rejected':
        send_system_message(
            conversation,
            f'❌ Prošnja za »{book_title}« je zavrnjena.'
        )
    elif instance.status == 'cancelled':
        send_system_message(
            conversation,
            f'⚠️ Prošnja za »{book_title}« je preklicana.'
        )
    elif instance.status == 'returned':
        send_system_message(
            conversation,
            f'📚 Knjiga »{book_title}« je vrnjena. Oba lahko zdaj oddata medsebojno oceno '
            f'zanesljivosti v razdelku »Moje izposoje«.'
        )


@receiver(post_save, sender=LoanReview)
def notify_on_review(sender, instance, created, **kwargs):
    """Obvesti udeleženca v zasebnem pogovoru, da je dobil oceno."""
    if not created:
        return

    try:
        from messaging.models import Conversation, send_system_message
    except ImportError:
        return

    conversation, _ = Conversation.get_or_create_between(instance.reviewer, instance.reviewee)

    send_system_message(
        conversation,
        f'⭐ {instance.reviewer.username} je oddal/-a oceno {instance.score}/5 '
        f'za izposojo knjige »{instance.loan_request.offer.book.title}«.'
    )