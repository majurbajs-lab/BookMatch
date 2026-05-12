"""Admin plošča za aplikacijo reading."""

from django.contrib import admin

from .models import Rating, ReadingEntry, ReadingList, Review


@admin.register(ReadingEntry)
class ReadingEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'status', 'progress', 'updated_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'book__title')
    raw_id_fields = ('user', 'book')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'score', 'updated_at')
    list_filter = ('score',)
    search_fields = ('user__username', 'book__title')
    raw_id_fields = ('user', 'book')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'likes_count', 'created_at')
    search_fields = ('user__username', 'book__title', 'content')
    raw_id_fields = ('user', 'book')


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_public', 'created_at')
    list_filter = ('is_public',)
    search_fields = ('name', 'user__username')
    filter_horizontal = ('books',)
