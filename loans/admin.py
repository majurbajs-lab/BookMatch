"""Admin plošča za aplikacijo loans."""

from django.contrib import admin

from .models import LoanOffer, LoanRequest, LoanReview


@admin.register(LoanOffer)
class LoanOfferAdmin(admin.ModelAdmin):
    list_display = ('book', 'owner', 'condition', 'status', 'created_at')
    list_filter = ('status', 'condition')
    search_fields = ('book__title', 'owner__username')
    raw_id_fields = ('book', 'owner')


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ('offer', 'borrower', 'status', 'loan_start', 'loan_end')
    list_filter = ('status',)
    search_fields = ('offer__book__title', 'borrower__username')
    raw_id_fields = ('offer', 'borrower')


@admin.register(LoanReview)
class LoanReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'reviewee', 'score', 'created_at')
    search_fields = ('reviewer__username', 'reviewee__username')
    raw_id_fields = ('loan_request', 'reviewer', 'reviewee')
