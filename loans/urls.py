"""URL poti za aplikacijo loans."""

from django.urls import path

from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_browse, name='browse'),
    path('moje/', views.my_loans, name='my_loans'),
    path('knjiga/<int:book_id>/ponudi/', views.offer_create, name='offer_create'),
    path('ponudba/<int:offer_id>/', views.offer_detail, name='offer_detail'),
    path('ponudba/<int:offer_id>/uredi/', views.offer_edit, name='offer_edit'),
    path('ponudba/<int:offer_id>/toggle/', views.offer_toggle_status, name='offer_toggle'),
    path('ponudba/<int:offer_id>/zaprosi/', views.request_create, name='request_create'),
    path('prosnja/<int:request_id>/sprejmi/', views.request_accept, name='request_accept'),
    path('prosnja/<int:request_id>/zavrni/', views.request_reject, name='request_reject'),
    path('prosnja/<int:request_id>/preklici/', views.request_cancel, name='request_cancel'),
    path('prosnja/<int:request_id>/vrnjeno/', views.request_return, name='request_return'),
    path('prosnja/<int:request_id>/oceni/', views.review, name='review'),
]
