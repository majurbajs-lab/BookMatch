"""Context processor za prikaz števca neprebranih sporočil v navigaciji."""

from .views import unread_count


def unread_messages(request):
    """Dodaja spremenljivko 'unread_messages_count' vsem predlogam."""
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0, 'unread_messages_display': ''}

    count = unread_count(request.user)
    display = '9+' if count > 9 else str(count) if count > 0 else ''

    return {
        'unread_messages_count': count,
        'unread_messages_display': display,
    }
