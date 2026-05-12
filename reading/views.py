"""Pogledi za aplikacijo reading."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

User = get_user_model()

from books.models import Book

from .forms import RatingForm, ReviewForm
from .models import HomeBook, Rating, ReadingEntry, Review


@login_required
def my_library(request):
    """Moja knjižnica – bralna evidenca razdeljena po statusih."""
    entries = ReadingEntry.objects.filter(user=request.user).select_related('book').prefetch_related('book__authors')

    # Razdeli po statusih
    by_status = {
        'reading': entries.filter(status='reading'),
        'want': entries.filter(status='want'),
        'read': entries.filter(status='read'),
        'dropped': entries.filter(status='dropped'),
    }

    # Statistika
    stats = {
        'total_read': by_status['read'].count(),
        'total_reading': by_status['reading'].count(),
        'total_want': by_status['want'].count(),
        'total_rated': Rating.objects.filter(user=request.user).count(),
    }

    return render(request, 'reading/my_library.html', {
        'by_status': by_status,
        'stats': stats,
    })


@login_required
@require_POST
def set_status(request, book_id):
    """Nastavi ali spremeni status knjige v uporabnikovi evidenci."""
    book = get_object_or_404(Book, pk=book_id, is_approved=True)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = dict(ReadingEntry.STATUS_CHOICES).keys()

    if new_status == 'remove':
        # Odstrani iz evidence
        ReadingEntry.objects.filter(user=request.user, book=book).delete()
        messages.success(request, f'»{book.title}« je odstranjena iz tvoje evidence.')
    elif new_status in valid_statuses:
        entry, created = ReadingEntry.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={'status': new_status},
        )
        if not created:
            entry.status = new_status
            entry.save()

        status_label = dict(ReadingEntry.STATUS_CHOICES)[new_status]
        messages.success(request, f'»{book.title}«: {status_label}.')
    else:
        messages.error(request, 'Neveljaven status.')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('books:detail', args=[book.id])))


@login_required
def home_library(request):
    """Moja domača knjižnica – fizične knjige doma."""
    home_books = (
        HomeBook.objects
        .filter(user=request.user)
        .select_related('book')
        .prefetch_related('book__authors', 'book__genres')
    )
    return render(request, 'reading/home_library.html', {
        'home_books': home_books,
        'is_own': True,
    })


def user_home_library(request, username):
    """Domača knjižnica drugega uporabnika – javno dostopno."""
    profile_user = get_object_or_404(User, username=username)
    home_books = (
        HomeBook.objects
        .filter(user=profile_user)
        .select_related('book')
        .prefetch_related('book__authors', 'book__genres')
    )
    return render(request, 'reading/home_library.html', {
        'home_books': home_books,
        'profile_user': profile_user,
        'is_own': request.user == profile_user,
    })


@login_required
@require_POST
def add_home_book(request, book_id):
    """Dodaj knjigo v domačo knjižnico."""
    book = get_object_or_404(Book, pk=book_id, is_approved=True)
    HomeBook.objects.get_or_create(user=request.user, book=book)
    messages.success(request, f'»{book.title}« dodana v domačo knjižnico.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('books:detail', args=[book.id])))


@login_required
@require_POST
def remove_home_book(request, book_id):
    """Odstrani knjigo iz domače knjižnice."""
    book = get_object_or_404(Book, pk=book_id)
    HomeBook.objects.filter(user=request.user, book=book).delete()
    messages.success(request, f'»{book.title}« odstranjena iz domače knjižnice.')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('reading:home_library')
    return redirect(next_url)


@login_required
def rate_book(request, book_id):
    """Oceni knjigo ali spremeni obstoječo oceno."""
    book = get_object_or_404(Book, pk=book_id, is_approved=True)
    existing = Rating.objects.filter(user=request.user, book=book).first()

    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.book = book
            rating.save()
            messages.success(request, f'Ocena za »{book.title}« je shranjena ({rating.score}).')
            return redirect('books:detail', book_id=book.id)
    else:
        form = RatingForm(instance=existing)

    return render(request, 'reading/rate_book.html', {
        'form': form,
        'book': book,
        'existing': existing,
    })


@login_required
@require_POST
def delete_rating(request, book_id):
    """Izbriši svojo oceno za knjigo."""
    book = get_object_or_404(Book, pk=book_id)
    deleted, _ = Rating.objects.filter(user=request.user, book=book).delete()
    if deleted:
        messages.success(request, f'Ocena za »{book.title}« je odstranjena.')
    return redirect('books:detail', book_id=book.id)


@login_required
def write_review(request, book_id):
    """Napiši ali uredi recenzijo za knjigo."""
    book = get_object_or_404(Book, pk=book_id, is_approved=True)
    existing = Review.objects.filter(user=request.user, book=book).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.book = book
            review.save()
            messages.success(request, 'Recenzija je shranjena.')
            return redirect('books:detail', book_id=book.id)
    else:
        form = ReviewForm(instance=existing)

    return render(request, 'reading/write_review.html', {
        'form': form,
        'book': book,
        'existing': existing,
    })


@login_required
@require_POST
def delete_review(request, book_id):
    """Izbriši svojo recenzijo za knjigo."""
    book = get_object_or_404(Book, pk=book_id)
    deleted, _ = Review.objects.filter(user=request.user, book=book).delete()
    if deleted:
        messages.success(request, 'Recenzija je odstranjena.')
    return redirect('books:detail', book_id=book.id)
