"""Pogledi za aplikacijo recommendations."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from books.models import TopBook
from core.models import DailyJobLog
from reading.models import Rating

from .models import Recommendation


@login_required
def for_you(request):
    """Stran »Za vas« – prikaže personalizirana priporočila iz dnevnega joba."""
    user_rating_count = Rating.objects.filter(user=request.user).count()
    needs_more_ratings = user_rating_count < 3

    # Timestamp zadnjega zagona
    try:
        job_log = DailyJobLog.objects.get(job_name=DailyJobLog.JOB_RECOMMENDATIONS)
        last_updated = job_log.last_run_at
    except DailyJobLog.DoesNotExist:
        last_updated = None

    top_books = (
        TopBook.objects
        .select_related('book')
        .prefetch_related('book__authors', 'book__genres')
        .order_by('rank')
    )

    if needs_more_ratings:
        return render(request, 'recommendations/for_you.html', {
            'needs_more_ratings': True,
            'user_rating_count': user_rating_count,
            'top_books': top_books,
            'last_updated': last_updated,
        })

    recommendations = (
        Recommendation.objects
        .filter(user=request.user, is_dismissed=False)
        .select_related('book')
        .prefetch_related('book__authors', 'book__genres')
        .order_by('-score')[:10]
    )

    return render(request, 'recommendations/for_you.html', {
        'recommendations': recommendations,
        'user_rating_count': user_rating_count,
        'needs_more_ratings': False,
        'top_books': top_books,
        'last_updated': last_updated,
    })


@login_required
@require_POST
def dismiss(request, recommendation_id):
    """Uporabnik zavrne priporočilo (»Ne zanima me«)."""
    rec = get_object_or_404(Recommendation, pk=recommendation_id, user=request.user)
    rec.is_dismissed = True
    rec.save(update_fields=['is_dismissed'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.info(request, f'»{rec.book.title}« odstranjeno iz priporočil.')
    return redirect('recommendations:for_you')
