"""Pogledi za aplikacijo loans."""

from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from books.models import Book
from core.regions import REGION_CHOICES

from .forms import LoanOfferForm, LoanRequestForm, LoanReviewForm
from .models import LoanOffer, LoanRequest, LoanReview


def loan_browse(request):
    """Stran Izposoja – pregled vseh aktivnih ponudb."""
    qs = (
        LoanOffer.objects
        .filter(status='available')
        .select_related('owner', 'owner__profile', 'book')
        .prefetch_related('book__authors')
    )

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(book__title__icontains=query) |
            Q(book__authors__name__icontains=query)
        ).distinct()

    region = request.GET.get('region', '').strip()
    if region:
        qs = qs.filter(owner__profile__region=region)

    condition = request.GET.get('condition', '').strip()
    if condition:
        qs = qs.filter(condition=condition)

    sort = request.GET.get('sort', 'newest')
    if sort == 'newest':
        qs = qs.order_by('-created_at')
    elif sort == 'title':
        qs = qs.order_by('book__title')

    paginator = Paginator(qs, 18)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'loans/loan_browse.html', {
        'page_obj': page_obj,
        'query': query,
        'regions': REGION_CHOICES,
        'selected_region': region,
        'conditions': LoanOffer.CONDITION_CHOICES,
        'selected_condition': condition,
        'selected_sort': sort,
    })


@login_required
def my_loans(request):
    """Moje izposoje – kot lastnik in kot izposojevalec."""
    user = request.user

    # Moje ponudbe
    my_offers = (
        LoanOffer.objects
        .filter(owner=user)
        .select_related('book')
        .prefetch_related('book__authors')
        .order_by('-created_at')
    )

    # Aktivne prošnje, ki sem jih poslal
    sent_requests = (
        LoanRequest.objects
        .filter(borrower=user)
        .exclude(status__in=['rejected', 'cancelled'])
        .select_related('offer__book', 'offer__owner')
        .prefetch_related('offer__book__authors')
        .order_by('-created_at')
    )

    # Prošnje, ki sem jih prejel kot lastnik
    received_requests = (
        LoanRequest.objects
        .filter(offer__owner=user)
        .exclude(status__in=['rejected', 'cancelled'])
        .select_related('offer__book', 'borrower')
        .prefetch_related('offer__book__authors')
        .order_by('-created_at')
    )

    # Zaključene izposoje (za pregled in ocenjevanje)
    completed = (
        LoanRequest.objects
        .filter(Q(borrower=user) | Q(offer__owner=user), status='returned')
        .select_related('offer__book', 'borrower', 'offer__owner')
        .prefetch_related('offer__book__authors', 'reviews')
        .order_by('-updated_at')[:20]
    )

    return render(request, 'loans/my_loans.html', {
        'my_offers': my_offers,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
        'completed': completed,
    })


@login_required
def offer_create(request, book_id):
    """Lastnik ponudi knjigo za izposojo."""
    book = get_object_or_404(Book, pk=book_id, is_approved=True)

    # Preveri, če že obstaja aktivna ponudba
    existing = LoanOffer.objects.filter(
        owner=request.user, book=book,
        status__in=['available', 'reserved', 'borrowed']
    ).first()
    if existing:
        messages.info(request, f'Že imaš aktivno ponudbo za to knjigo.')
        return redirect('loans:offer_detail', offer_id=existing.id)

    if request.method == 'POST':
        form = LoanOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.owner = request.user
            offer.book = book
            offer.save()
            messages.success(request, f'Knjiga »{book.title}« je zdaj ponujena za izposojo.')
            return redirect('loans:offer_detail', offer_id=offer.id)
    else:
        form = LoanOfferForm()

    return render(request, 'loans/offer_form.html', {
        'form': form,
        'book': book,
    })


@login_required
def offer_edit(request, offer_id):
    """Lastnik ureja obstoječo ponudbo."""
    offer = get_object_or_404(LoanOffer, pk=offer_id, owner=request.user)

    if request.method == 'POST':
        form = LoanOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ponudba je posodobljena.')
            return redirect('loans:offer_detail', offer_id=offer.id)
    else:
        form = LoanOfferForm(instance=offer)

    return render(request, 'loans/offer_form.html', {
        'form': form,
        'book': offer.book,
        'is_edit': True,
        'offer': offer,
    })


@login_required
@require_POST
def offer_toggle_status(request, offer_id):
    """Lastnik aktivira ali deaktivira ponudbo."""
    offer = get_object_or_404(LoanOffer, pk=offer_id, owner=request.user)

    if offer.status == 'available':
        offer.status = 'inactive'
        msg = 'Ponudba je deaktivirana.'
    elif offer.status == 'inactive':
        offer.status = 'available'
        msg = 'Ponudba je ponovno na voljo.'
    else:
        messages.warning(request, 'Statusa trenutne izposoje ne moreš ročno spremeniti.')
        return redirect('loans:offer_detail', offer_id=offer.id)

    offer.save()
    messages.success(request, msg)
    return redirect('loans:offer_detail', offer_id=offer.id)


def offer_detail(request, offer_id):
    """Podrobnosti ponudbe."""
    offer = get_object_or_404(
        LoanOffer.objects.select_related('owner', 'owner__profile', 'book').prefetch_related('book__authors', 'book__genres'),
        pk=offer_id,
    )

    is_owner = request.user == offer.owner
    existing_request = None
    if request.user.is_authenticated and not is_owner:
        existing_request = LoanRequest.objects.filter(
            offer=offer, borrower=request.user,
        ).exclude(status__in=['rejected', 'cancelled']).first()

    return render(request, 'loans/offer_detail.html', {
        'offer': offer,
        'is_owner': is_owner,
        'existing_request': existing_request,
    })


@login_required
def request_create(request, offer_id):
    """Izposojevalec zaprosi za izposojo."""
    offer = get_object_or_404(LoanOffer, pk=offer_id, status='available')

    if offer.owner == request.user:
        messages.error(request, 'Ne moreš zaprositi za izposojo svoje knjige.')
        return redirect('loans:offer_detail', offer_id=offer.id)

    # Preveri, če že obstaja aktivna prošnja
    existing = LoanRequest.objects.filter(
        offer=offer, borrower=request.user,
    ).exclude(status__in=['rejected', 'cancelled']).first()
    if existing:
        messages.info(request, 'Že si poslal prošnjo za to knjigo.')
        return redirect('loans:my_loans')

    if request.method == 'POST':
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            loan_request = form.save(commit=False)
            loan_request.offer = offer
            loan_request.borrower = request.user
            loan_request.save()
            messages.success(
                request,
                f'Prošnja je bila poslana lastniku {offer.owner.username}. '
                'Ko jo bo potrdil, se boste dogovorili za prevzem.'
            )
            return redirect('loans:my_loans')
    else:
        form = LoanRequestForm()

    return render(request, 'loans/request_form.html', {
        'form': form,
        'offer': offer,
    })


@login_required
@require_POST
def request_accept(request, request_id):
    """Lastnik sprejme prošnjo."""
    loan_request = get_object_or_404(LoanRequest, pk=request_id, offer__owner=request.user)

    if loan_request.status != 'pending':
        messages.warning(request, 'Ta prošnja ni več v čakanju.')
        return redirect('loans:my_loans')

    loan_request.status = 'accepted'
    loan_request.loan_start = date.today()
    loan_request.loan_end = date.today() + timedelta(days=loan_request.offer.max_loan_days)
    loan_request.save()

    # Ponudba postane "borrowed"
    loan_request.offer.status = 'borrowed'
    loan_request.offer.save()

    # Ostale prošnje za isto ponudbo samodejno zavrnemo
    LoanRequest.objects.filter(
        offer=loan_request.offer, status='pending',
    ).exclude(pk=loan_request.pk).update(status='rejected')

    messages.success(request, f'Prošnja sprejeta. Knjiga je izposojena uporabniku {loan_request.borrower.username}.')
    return redirect('loans:my_loans')


@login_required
@require_POST
def request_reject(request, request_id):
    """Lastnik zavrne prošnjo."""
    loan_request = get_object_or_404(LoanRequest, pk=request_id, offer__owner=request.user)

    if loan_request.status != 'pending':
        messages.warning(request, 'Ta prošnja ni več v čakanju.')
        return redirect('loans:my_loans')

    loan_request.status = 'rejected'
    loan_request.save()
    messages.info(request, 'Prošnja je zavrnjena.')
    return redirect('loans:my_loans')


@login_required
@require_POST
def request_cancel(request, request_id):
    """Izposojevalec prekliče svojo prošnjo."""
    loan_request = get_object_or_404(LoanRequest, pk=request_id, borrower=request.user)

    if loan_request.status not in ['pending', 'accepted']:
        messages.warning(request, 'Te prošnje ni mogoče preklicati.')
        return redirect('loans:my_loans')

    loan_request.status = 'cancelled'
    loan_request.save()

    # Če je bila ponudba že rezervirana zaradi te prošnje, jo sprosti
    if loan_request.offer.status == 'borrowed':
        loan_request.offer.status = 'available'
        loan_request.offer.save()

    messages.info(request, 'Prošnja je preklicana.')
    return redirect('loans:my_loans')


@login_required
@require_POST
def request_return(request, request_id):
    """Lastnik označi, da je knjiga vrnjena."""
    loan_request = get_object_or_404(LoanRequest, pk=request_id, offer__owner=request.user)

    if loan_request.status != 'accepted':
        messages.warning(request, 'Ta izposoja ni aktivna.')
        return redirect('loans:my_loans')

    loan_request.status = 'returned'
    loan_request.save()

    loan_request.offer.status = 'available'
    loan_request.offer.save()

    messages.success(request, 'Vračilo zabeleženo. Zdaj lahko oba oddasta medsebojno oceno.')
    return redirect('loans:review', request_id=loan_request.id)


@login_required
def review(request, request_id):
    """Oceni izposojo (medsebojna ocena)."""
    loan_request = get_object_or_404(
        LoanRequest.objects.select_related('offer__owner', 'borrower', 'offer__book'),
        pk=request_id,
    )

    # Samo lastnik ali izposojevalec lahko ocenita
    if request.user != loan_request.offer.owner and request.user != loan_request.borrower:
        messages.error(request, 'Te izposoje ne moreš ocenjevati.')
        return redirect('loans:my_loans')

    if loan_request.status != 'returned':
        messages.warning(request, 'Ocena je možna šele po vračilu.')
        return redirect('loans:my_loans')

    # Ugotovimo, koga ocenjujemo
    if request.user == loan_request.offer.owner:
        reviewee = loan_request.borrower
    else:
        reviewee = loan_request.offer.owner

    existing = LoanReview.objects.filter(loan_request=loan_request, reviewer=request.user).first()
    if existing:
        messages.info(request, 'Za to izposojo si že oddal oceno.')
        return redirect('loans:my_loans')

    if request.method == 'POST':
        form = LoanReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.loan_request = loan_request
            review.reviewer = request.user
            review.reviewee = reviewee
            review.save()
            messages.success(request, f'Hvala za oceno uporabnika {reviewee.username}.')
            return redirect('loans:my_loans')
    else:
        form = LoanReviewForm()

    return render(request, 'loans/review_form.html', {
        'form': form,
        'loan_request': loan_request,
        'reviewee': reviewee,
    })
