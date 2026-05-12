"""Admin plošča za aplikacijo accounts."""

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'region', 'location', 'reliability_score',
                    'is_public', 'show_in_matches', 'created_at')
    list_filter = ('region', 'is_public', 'show_in_matches')
    search_fields = ('user__username', 'user__email', 'location')
    readonly_fields = ('created_at', 'updated_at', 'reliability_score',
                       'reliability_count', 'cluster_id')
