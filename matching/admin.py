"""Admin plošča za aplikacijo matching."""

from django.contrib import admin

from .models import GroupSuggestion, UserMatch


@admin.register(UserMatch)
class UserMatchAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'similarity_score', 'cluster_id', 'is_dismissed')
    list_filter = ('is_dismissed', 'cluster_id')
    search_fields = ('user_a__username', 'user_b__username')
    raw_id_fields = ('user_a', 'user_b')


@admin.register(GroupSuggestion)
class GroupSuggestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'match_score', 'is_dismissed')
    list_filter = ('is_dismissed',)
    search_fields = ('user__username', 'group__name')
    raw_id_fields = ('user', 'group')
