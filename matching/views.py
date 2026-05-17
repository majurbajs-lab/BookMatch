"""Pogledi za aplikacijo matching."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from reading.models import Rating

from .models import GroupSuggestion, UserMatch


@login_required
def readers_for_you(request):
    """Stran »Bralci zate« – prikaže predlagane skupine in uporabnike."""
    user = request.user

    # Preveri, ali uporabnik sodeluje v sistemu ujemanj
    if not user.profile.show_in_matches:
        return render(request, 'matching/opt_out.html')

    user_rating_count = Rating.objects.filter(user=user).count()
    needs_more_ratings = user_rating_count < 3

    if user_rating_count >= 3:
        try:
            from ml.auto_train import maybe_train_matcher, _MATCHER_STAMP
            # Če ta user nima predlogov, pobriši stamp in prisili ponovni trening
            has_suggestions = GroupSuggestion.objects.filter(user=user).exists()
            if not has_suggestions and _MATCHER_STAMP.exists():
                _MATCHER_STAMP.unlink(missing_ok=True)
            maybe_train_matcher()
        except Exception:
            pass

    # Predlagane skupine
    group_suggestions = (
        GroupSuggestion.objects
        .filter(user=user, is_dismissed=False)
        .select_related('group')
        .prefetch_related('group__genres', 'group__memberships')
        .order_by('-match_score')[:12]
    )

    # Izključi skupine, ki so že članove
    from groups.models import GroupMembership
    member_group_ids = set(
        GroupMembership.objects.filter(user=user, is_approved=True)
        .values_list('group_id', flat=True)
    )
    group_suggestions = [g for g in group_suggestions if g.group_id not in member_group_ids]

    # Ujemanja z drugimi bralci
    user_matches = (
        UserMatch.objects
        .filter(
            Q(user_a=user) | Q(user_b=user),
            is_dismissed=False,
        )
        .select_related('user_a__profile', 'user_b__profile')
        .order_by('-similarity_score')[:12]
    )

    # Pripravi podatke (druga oseba v paru)
    matches_for_display = []
    for m in user_matches:
        other = m.user_b if m.user_a == user else m.user_a
        # Preveri, ali je drug uporabnik dovolil ujemanja
        if not other.profile.show_in_matches:
            continue
        matches_for_display.append({
            'match': m,
            'other': other,
            'percent': int(float(m.similarity_score) * 100),
        })

    return render(request, 'matching/readers_for_you.html', {
        'group_suggestions': group_suggestions,
        'matches_for_display': matches_for_display,
        'needs_more_ratings': needs_more_ratings,
        'user_rating_count': user_rating_count,
    })


@login_required
@require_POST
def dismiss_group_suggestion(request, suggestion_id):
    """Uporabnik zavrne predlog skupine."""
    suggestion = get_object_or_404(GroupSuggestion, pk=suggestion_id, user=request.user)
    suggestion.is_dismissed = True
    suggestion.save(update_fields=['is_dismissed'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.info(request, f'»{suggestion.group.name}« odstranjeno iz predlogov.')
    return redirect('matching:readers_for_you')


@login_required
@require_POST
def dismiss_user_match(request, match_id):
    """Uporabnik zavrne ujemanje z drugim bralcem."""
    match = get_object_or_404(
        UserMatch.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)),
        pk=match_id,
    )
    match.is_dismissed = True
    match.save(update_fields=['is_dismissed'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('matching:readers_for_you')
