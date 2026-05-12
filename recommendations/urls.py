"""URL poti za aplikacijo recommendations."""

from django.urls import path

from . import views

app_name = 'recommendations'

urlpatterns = [
    path('for-you/', views.for_you, name='for_you'),
    path('<int:recommendation_id>/dismiss/', views.dismiss, name='dismiss'),
]
