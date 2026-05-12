"""Admin plošča za messaging."""

from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant_a', 'participant_b', 'last_message_at', 'created_at')
    search_fields = ('participant_a__username', 'participant_b__username')
    raw_id_fields = ('participant_a', 'participant_b')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'kind', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')
    search_fields = ('content', 'sender__username')
    raw_id_fields = ('conversation', 'sender')
