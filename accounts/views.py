"""Pogledi za aplikacijo accounts.
Posodobljeno za Fazo 2 – profil kaže prebrane knjige in recenzije.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, RegistrationForm, UserForm
from .models import Profile


def register(request):
    """Registracija novega uporabnika."""
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Dobrodošel/-a v BookMatch, {user.username}! Tvoj račun je ustvarjen.'
            )
            return redirect('accounts:profile_edit')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_view(request, username=None):
    """Prikaz profila uporabnika.

    Za Fazo 2: prikaže zadnje prebrane knjige in zadnje recenzije.
    """
    if username:
        profile = get_object_or_404(Profile, user__username=username)
        if not profile.is_public and profile.user != request.user:
            messages.warning(request, 'Ta profil ni javen.')
            return redirect('core:home')
    else:
        profile = request.user.profile

    is_owner = profile.user == request.user

    # Bralna evidenca in recenzije (Faza 2)
    from reading.models import ReadingEntry, Rating, Review

    recent_read = (
        ReadingEntry.objects
        .filter(user=profile.user, status='read')
        .select_related('book')
        .prefetch_related('book__authors')
        .order_by('-updated_at')[:8]
    )

    recent_reviews = (
        Review.objects
        .filter(user=profile.user)
        .select_related('book')
        .order_by('-created_at')[:5]
    )

    read_count = ReadingEntry.objects.filter(user=profile.user, status='read').count()
    rating_count = Rating.objects.filter(user=profile.user).count()

    return render(request, 'accounts/profile_view.html', {
        'profile': profile,
        'is_owner': is_owner,
        'recent_read': recent_read,
        'recent_reviews': recent_reviews,
        'read_count': read_count,
        'rating_count': rating_count,
    })


@login_required
def profile_edit(request):
    """Urejanje lastnega profila."""
    profile = request.user.profile

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil je uspešno posodobljen.')
            return redirect('accounts:profile_view_me')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })
