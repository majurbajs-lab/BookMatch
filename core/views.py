"""Pogledi za aplikacijo core.

Domača stran ima dve različici:
- Neprijavljenim: klasična predstavitvena stran s hero-jem in seznamom funkcionalnosti
- Prijavljenim: dashboard s pregledom aktivnosti, priporočil in izposoj
"""

from django.db.models import Q
from django.shortcuts import render


def home(request):
    """Domača stran – dashboard za prijavljene, hero za neprijavljene."""
    if not request.user.is_authenticated:
        from books.models import Book
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            from groups.models import ReadingGroup
            group_count = ReadingGroup.objects.count()
        except Exception:
            group_count = 0
        return render(request, 'core/home.html', {
            'book_count': Book.objects.filter(is_approved=True).count(),
            'user_count': User.objects.count(),
            'group_count': group_count,
        })

    return dashboard_view(request)


def dashboard_view(request):
    """Dashboard za prijavljenega uporabnika."""
    from groups.models import GroupMembership
    from loans.models import LoanOffer, LoanRequest
    from reading.models import Rating, ReadingEntry

    user = request.user

    # Moje skupine (do 6 + skupno število)
    all_memberships = (
        GroupMembership.objects
        .filter(user=user, is_approved=True)
        .select_related('group')
        .prefetch_related('group__genres')
        .order_by('-joined_at')
    )
    my_groups = all_memberships[:6]
    total_groups = all_memberships.count()

    # Aktivni klepeti 1-na-1 (do 5 + skupno)
    try:
        from messaging.models import Conversation
        all_convs = (
            Conversation.objects
            .filter(Q(participant_a=user) | Q(participant_b=user))
            .exclude(last_message_at__isnull=True)
            .select_related('participant_a', 'participant_a__profile',
                            'participant_b', 'participant_b__profile')
            .prefetch_related('messages')
            .order_by('-last_message_at')
        )
        active_chats = []
        for conv in all_convs[:5]:
            other = conv.other_participant(user)
            last_msg = conv.messages.order_by('-created_at').first()
            unread = conv.unread_count_for(user)
            active_chats.append({
                'conversation': conv,
                'other': other,
                'last_message': last_msg,
                'unread_count': unread,
            })
        total_chats = all_convs.count()
    except ImportError:
        active_chats = []
        total_chats = 0

    # Statistika branja
    stats = {
        'read_count': ReadingEntry.objects.filter(user=user, status='read').count(),
        'reading_count': ReadingEntry.objects.filter(user=user, status='reading').count(),
        'rating_count': Rating.objects.filter(user=user).count(),
        'active_loans_count': LoanRequest.objects.filter(
            Q(borrower=user) | Q(offer__owner=user),
            status='accepted',
        ).count(),
    }

    # Top 3 priporočene knjige
    try:
        from recommendations.models import Recommendation
        top_recommendations = (
            Recommendation.objects
            .filter(user=user, is_dismissed=False)
            .select_related('book')
            .prefetch_related('book__authors', 'book__genres')
            .order_by('-score')[:3]
        )
    except ImportError:
        top_recommendations = []

    # Top 3 predlagane skupine
    try:
        from matching.models import GroupSuggestion
        member_group_ids = set(
            GroupMembership.objects.filter(user=user, is_approved=True)
            .values_list('group_id', flat=True)
        )
        top_group_suggestions = [
            s for s in GroupSuggestion.objects
                .filter(user=user, is_dismissed=False)
                .select_related('group')
                .prefetch_related('group__genres')
                .order_by('-match_score')[:10]
            if s.group_id not in member_group_ids
        ][:3]
    except ImportError:
        top_group_suggestions = []

    # Aktivne izposoje (knjige, ki jih trenutno imam ali sem posodil)
    active_loans = (
        LoanRequest.objects
        .filter(
            Q(borrower=user) | Q(offer__owner=user),
            status='accepted',
        )
        .select_related('offer__book', 'offer__owner', 'borrower')
        .prefetch_related('offer__book__authors', 'offer__book__genres')
        .order_by('loan_end')[:5]
    )

    # Čakajoče prošnje kot lastnik (to sem dodal kot opozorilo na dashboardu)
    pending_requests = (
        LoanRequest.objects
        .filter(offer__owner=user, status='pending')
        .select_related('offer__book', 'borrower')
        .order_by('-created_at')
    )

    return render(request, 'core/dashboard.html', {
        'my_groups': my_groups,
        'total_groups': total_groups,
        'active_chats': active_chats,
        'total_chats': total_chats,
        'stats': stats,
        'top_recommendations': top_recommendations,
        'top_group_suggestions': top_group_suggestions,
        'active_loans': active_loans,
        'pending_requests': pending_requests,
    })


def about(request):
    return render(request, 'core/about.html')
