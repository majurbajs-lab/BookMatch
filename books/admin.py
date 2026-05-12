"""Admin plošča za aplikacijo books."""

from django.contrib import admin

from .models import Author, Book, Genre


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_year')
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'authors_list', 'publication_year',
        'language', 'average_rating', 'ratings_count', 'is_approved'
    )
    list_filter = ('language', 'is_approved', 'genres', 'publication_year')
    search_fields = ('title', 'isbn', 'authors__name')
    filter_horizontal = ('authors', 'genres')
    readonly_fields = ('average_rating', 'ratings_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Osnovni podatki', {
            'fields': ('title', 'authors', 'isbn', 'publication_year', 'publisher', 'language', 'page_count')
        }),
        ('Vsebina', {
            'fields': ('genres', 'description', 'cover_image')
        }),
        ('Status', {
            'fields': ('is_approved',)
        }),
        ('Statistika (samodejno)', {
            'fields': ('average_rating', 'ratings_count', 'created_at', 'updated_at')
        }),
    )
