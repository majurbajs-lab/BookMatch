"""Pogledi za aplikacijo messaging."""

from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Conversation, Message

User = get_user_model()


@login_required
def inbox(request):
    """Prejeta pošta – seznam vseh pogovorov uporabnika."""
    user = request.user

    conversations = (
        Conversation.objects
        .filter(Q(participant_a=user) | Q(participant_b=user))
        .select_related('participant_a', 'participant_a__profile',
                        'participant_b', 'participant_b__profile')
        .prefetch_related('messages')
        .order_by('-last_message_at', '-created_at')
    )

    # Pripravi podatke za prikaz
    conversation_data = []
    for conv in conversations:
        other = conv.other_participant(user)
        last_msg = conv.messages.order_by('-created_at').first()
        unread = conv.unread_count_for(user)

        conversation_data.append({
            'conversation': conv,
            'other': other,
            'last_message': last_msg,
            'unread_count': unread,
        })

    # Iskanje uporabnikov za nov pogovor
    search_query = request.GET.get('user_search', '').strip()
    search_results = []
    if search_query:
        search_results = (
            User.objects
            .filter(username__icontains=search_query, is_active=True)
            .exclude(id=user.id)
            .select_related('profile')[:10]
        )

    return render(request, 'messaging/inbox.html', {
        'conversation_data': conversation_data,
        'search_query': search_query,
        'search_results': search_results,
    })


@login_required
def conversation_detail(request, conversation_id):
    """Podrobnost pogovora s prikazom vseh sporočil."""
    user = request.user

    conversation = get_object_or_404(
        Conversation.objects.select_related(
            'participant_a', 'participant_a__profile',
            'participant_b', 'participant_b__profile',
        ),
        pk=conversation_id,
    )

    # Preveri, da je uporabnik udeleženec
    if user not in [conversation.participant_a, conversation.participant_b]:
        django_messages.error(request, 'Tega pogovora ne smeš videti.')
        return redirect('messaging:inbox')

    other = conversation.other_participant(user)

    # Obdelaj novo sporočilo
    if request.method == 'POST':
        content = (request.POST.get('content') or '').strip()
        if content:
            Message.objects.create(
                conversation=conversation,
                sender=user,
                kind='user',
                content=content[:2000],
                is_read=False,
            )
            return redirect('messaging:detail', conversation_id=conversation.id)

    # Označi sporočila drugega kot prebrana
    Message.objects.filter(
        conversation=conversation,
    ).exclude(sender=user).filter(is_read=False).update(is_read=True)

    messages_list = conversation.messages.all().select_related('sender')

    return render(request, 'messaging/conversation.html', {
        'conversation': conversation,
        'other': other,
        'messages_list': messages_list,
    })


@login_required
def start_conversation(request, username):
    """Začne (ali nadaljuje) pogovor z drugim uporabnikom po uporabniškem imenu."""
    other = get_object_or_404(User, username=username, is_active=True)

    if other == request.user:
        django_messages.warning(request, 'Pogovor s samim seboj ni mogoč.')
        return redirect('messaging:inbox')

    conversation, created = Conversation.get_or_create_between(request.user, other)

    return redirect('messaging:detail', conversation_id=conversation.id)


def unread_count(user):
    """Pomožna funkcija – skupno število neprebranih sporočil za uporabnika.

    Uporabljamo v context_processor za prikaz značke v navigaciji.
    """
    if not user.is_authenticated:
        return 0
    return Message.objects.filter(
        conversation__in=Conversation.objects.filter(
            Q(participant_a=user) | Q(participant_b=user)
        ),
        is_read=False,
    ).exclude(sender=user).count()
