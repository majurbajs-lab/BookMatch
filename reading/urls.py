"""URL poti za aplikacijo reading."""

from django.urls import path

from . import views

app_name = 'reading'

urlpatterns = [
    path('library/', views.my_library, name='library'),
    path('home-library/', views.home_library, name='home_library'),
    path('home-library/<str:username>/', views.user_home_library, name='user_home_library'),
    path('book/<int:book_id>/home-library/add/', views.add_home_book, name='add_home_book'),
    path('book/<int:book_id>/home-library/remove/', views.remove_home_book, name='remove_home_book'),
    path('book/<int:book_id>/status/', views.set_status, name='set_status'),
    path('book/<int:book_id>/rate/', views.rate_book, name='rate'),
    path('book/<int:book_id>/rate/delete/', views.delete_rating, name='delete_rating'),
    path('book/<int:book_id>/review/', views.write_review, name='review'),
    path('book/<int:book_id>/review/delete/', views.delete_review, name='delete_review'),
]
