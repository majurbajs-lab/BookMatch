"""Admin plošča za aplikacijo recommendations."""

from django.contrib import admin

from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'score', 'reason', 'is_dismissed', 'updated_at')
    list_filter = ('is_dismissed',)
    search_fields = ('user__username', 'book__title')
    raw_id_fields = ('user', 'book')
    readonly_fields = ('created_at', 'updated_at')
