"""Pogledi za aplikacijo recommendations."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from reading.models import Rating

from .models import Recommendation


@login_required
def for_you(request):
    """Stran »Za vas« – prikaže personalizirana priporočila."""
    user_rating_count = Rating.objects.filter(user=request.user).count()

    if user_rating_count >= 3:
        try:
            from ml.auto_train import maybe_train_recommender
            maybe_train_recommender()
        except Exception:
            pass

    recommendations = (
        Recommendation.objects
        .filter(user=request.user, is_dismissed=False)
        .select_related('book')
        .prefetch_related('book__authors', 'book__genres')
        .order_by('-score')[:30]
    )

    # Ali uporabnik potrebuje več ocen?
    needs_more_ratings = user_rating_count < 3

    # Ali so priporočila zastarela? (ocenjeno po tem, da je zadnja ocena novejša od najnovejše
    # posodobitve priporočil)
    last_rec_update = recommendations.first().updated_at if recommendations.exists() else None
    last_rating_update = (
        Rating.objects.filter(user=request.user).order_by('-updated_at').first()
    )
    recommendations_outdated = (
        last_rec_update and last_rating_update
        and last_rating_update.updated_at > last_rec_update
    )

    context = {
        'recommendations': recommendations,
        'user_rating_count': user_rating_count,
        'needs_more_ratings': needs_more_ratings,
        'recommendations_outdated': recommendations_outdated,
    }
    return render(request, 'recommendations/for_you.html', context)


@login_required
@require_POST
def dismiss(request, recommendation_id):
    """Uporabnik zavrne priporočilo (»Ne zanima me«)."""
    rec = get_object_or_404(Recommendation, pk=recommendation_id, user=request.user)
    rec.is_dismissed = True
    rec.save(update_fields=['is_dismissed'])

    # AJAX odziv
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.info(request, f'»{rec.book.title}« odstranjeno iz priporočil.')
    return redirect('recommendations:for_you')
