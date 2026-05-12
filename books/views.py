"""Pogledi za aplikacijo books."""

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Book, Genre


def catalog(request):
    """Katalog vseh knjig z iskanjem, filtri in razvrščanjem."""
    qs = Book.objects.filter(is_approved=True).prefetch_related('authors', 'genres')

    # Iskanje
    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(authors__name__icontains=query)
            | Q(isbn__icontains=query)
        ).distinct()

    # Filter po zvrsti
    genre_slug = request.GET.get('genre', '').strip()
    if genre_slug:
        qs = qs.filter(genres__slug=genre_slug)

    # Filter po jeziku
    language = request.GET.get('language', '').strip()
    if language:
        qs = qs.filter(language=language)

    # Razvrščanje
    sort = request.GET.get('sort', 'title')
    valid_sorts = {
        'title': 'title',
        '-title': '-title',
        'rating': '-average_rating',
        'popular': '-ratings_count',
        'newest': '-created_at',
        'year': '-publication_year',
    }
    qs = qs.order_by(valid_sorts.get(sort, 'title'))

    # Stranjenje
    paginator = Paginator(qs, 24)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'genres': Genre.objects.all(),
        'selected_genre': genre_slug,
        'selected_language': language,
        'selected_sort': sort,
        'languages': Book.LANGUAGE_CHOICES,
    }
    return render(request, 'books/catalog.html', context)


def book_detail(request, book_id):
    """Stran posamezne knjige."""
    book = get_object_or_404(
        Book.objects.prefetch_related('authors', 'genres', 'reviews__user'),
        pk=book_id,
        is_approved=True,
    )

    # Uporabnikov status, ocena in recenzija za to knjigo
    user_entry = None
    user_rating = None
    user_review = None
    user_home_book = None
    if request.user.is_authenticated:
        from reading.models import HomeBook, Rating, ReadingEntry, Review
        user_entry = ReadingEntry.objects.filter(user=request.user, book=book).first()
        user_rating = Rating.objects.filter(user=request.user, book=book).first()
        user_review = Review.objects.filter(user=request.user, book=book).first()
        user_home_book = HomeBook.objects.filter(user=request.user, book=book).first()

    context = {
        'book': book,
        'user_entry': user_entry,
        'user_rating': user_rating,
        'user_review': user_review,
        'user_home_book': user_home_book,
    }
    return render(request, 'books/book_detail.html', context)
