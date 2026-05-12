"""Pogledi za aplikacijo groups.

Posodobljeno za Fazo 5A: seznam skupin ima filter po regiji.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from books.models import Genre
from core.regions import REGION_CHOICES_FOR_GROUP

from .forms import GroupForm, MessageForm
from .models import GroupMembership, GroupMessage, ReadingGroup


def group_list(request):
    """Seznam vseh skupin z iskanjem in filtri (žanr, regija)."""
    qs = ReadingGroup.objects.annotate(
        members_count=Count('memberships', filter=Q(memberships__is_approved=True))
    ).prefetch_related('genres')

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))

    genre_slug = request.GET.get('genre', '').strip()
    if genre_slug:
        qs = qs.filter(genres__slug=genre_slug)

    region = request.GET.get('region', '').strip()
    if region:
        qs = qs.filter(region=region)

    sort = request.GET.get('sort', 'popular')
    if sort == 'popular':
        qs = qs.order_by('-members_count', 'name')
    elif sort == 'newest':
        qs = qs.order_by('-created_at')
    else:
        qs = qs.order_by('name')

    paginator = Paginator(qs, 18)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'groups/group_list.html', {
        'page_obj': page_obj,
        'query': query,
        'genres': Genre.objects.all(),
        'regions': REGION_CHOICES_FOR_GROUP,
        'selected_genre': genre_slug,
        'selected_region': region,
        'selected_sort': sort,
    })


def group_detail(request, slug):
    group = get_object_or_404(
        ReadingGroup.objects.prefetch_related('genres', 'memberships__user'),
        slug=slug,
    )

    is_member = group.is_member(request.user)
    has_pending = group.has_pending_request(request.user) if request.user.is_authenticated else False
    is_owner = request.user.is_authenticated and group.owner == request.user

    messages_qs = None
    if is_member:
        messages_qs = group.messages.select_related('sender').order_by('-created_at')[:50]
        messages_qs = list(reversed(messages_qs))

    message_form = None
    if is_member and request.method == 'POST' and 'send_message' in request.POST:
        message_form = MessageForm(request.POST)
        if message_form.is_valid():
            msg = message_form.save(commit=False)
            msg.group = group
            msg.sender = request.user
            msg.save()
            return redirect('groups:detail', slug=group.slug)
    elif is_member:
        message_form = MessageForm()

    pending_requests = []
    if is_owner:
        pending_requests = group.memberships.filter(is_approved=False).select_related('user')

    active_members = group.memberships.filter(is_approved=True).select_related('user', 'user__profile')[:20]

    return render(request, 'groups/group_detail.html', {
        'group': group,
        'is_member': is_member,
        'has_pending': has_pending,
        'is_owner': is_owner,
        'messages_list': messages_qs,
        'message_form': message_form,
        'pending_requests': pending_requests,
        'active_members': active_members,
    })


@login_required
@require_POST
def join_group(request, slug):
    group = get_object_or_404(ReadingGroup, slug=slug)

    if group.is_member(request.user):
        messages.info(request, 'Že si član te skupine.')
        return redirect('groups:detail', slug=slug)

    if group.has_pending_request(request.user):
        messages.info(request, 'Prošnja je že oddana.')
        return redirect('groups:detail', slug=slug)

    is_approved = (group.visibility == 'public')

    GroupMembership.objects.create(
        user=request.user,
        group=group,
        role='member',
        is_approved=is_approved,
    )

    if is_approved:
        messages.success(request, f'Pridružil si se skupini »{group.name}«.')
    else:
        messages.info(request, f'Prošnja za skupino »{group.name}« je oddana.')

    return redirect('groups:detail', slug=slug)


@login_required
@require_POST
def leave_group(request, slug):
    group = get_object_or_404(ReadingGroup, slug=slug)
    if group.owner == request.user:
        messages.warning(request, 'Lastnik ne more zapustiti skupine.')
        return redirect('groups:detail', slug=slug)

    GroupMembership.objects.filter(user=request.user, group=group).delete()
    messages.success(request, f'Zapustil si skupino »{group.name}«.')
    return redirect('groups:list')


@login_required
@require_POST
def approve_member(request, slug, user_id):
    group = get_object_or_404(ReadingGroup, slug=slug)
    if group.owner != request.user:
        messages.error(request, 'Samo lastnik lahko odobri prošnje.')
        return redirect('groups:detail', slug=slug)

    membership = GroupMembership.objects.filter(group=group, user_id=user_id, is_approved=False).first()
    if membership:
        membership.is_approved = True
        membership.save()
        messages.success(request, f'Odobrena prošnja: {membership.user.username}.')
    return redirect('groups:detail', slug=slug)


@login_required
@require_POST
def reject_member(request, slug, user_id):
    group = get_object_or_404(ReadingGroup, slug=slug)
    if group.owner != request.user:
        messages.error(request, 'Samo lastnik lahko zavrne prošnje.')
        return redirect('groups:detail', slug=slug)

    GroupMembership.objects.filter(group=group, user_id=user_id, is_approved=False).delete()
    messages.info(request, 'Prošnja zavrnjena.')
    return redirect('groups:detail', slug=slug)


@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()
            form.save_m2m()

            GroupMembership.objects.create(
                user=request.user,
                group=group,
                role='owner',
                is_approved=True,
            )
            messages.success(request, f'Skupina »{group.name}« je ustvarjena.')
            return redirect('groups:detail', slug=group.slug)
    else:
        form = GroupForm()

    return render(request, 'groups/group_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
def edit_group(request, slug):
    group = get_object_or_404(ReadingGroup, slug=slug)
    if group.owner != request.user:
        messages.error(request, 'Samo lastnik lahko ureja skupino.')
        return redirect('groups:detail', slug=slug)

    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Skupina je posodobljena.')
            return redirect('groups:detail', slug=group.slug)
    else:
        form = GroupForm(instance=group)

    return render(request, 'groups/group_form.html', {
        'form': form,
        'is_edit': True,
        'group': group,
    })


@login_required
def my_groups(request):
    memberships = (
        GroupMembership.objects
        .filter(user=request.user, is_approved=True)
        .select_related('group')
        .prefetch_related('group__genres')
        .order_by('-joined_at')
    )
    pending = (
        GroupMembership.objects
        .filter(user=request.user, is_approved=False)
        .select_related('group')
    )
    return render(request, 'groups/my_groups.html', {
        'memberships': memberships,
        'pending': pending,
    })

