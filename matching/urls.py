"""URL poti za aplikacijo matching."""

from django.urls import path

from . import views

app_name = 'matching'

urlpatterns = [
    path('bralci-zate/', views.readers_for_you, name='readers_for_you'),
    path('skupina/<int:suggestion_id>/skrij/', views.dismiss_group_suggestion, name='dismiss_group'),
    path('ujemanje/<int:match_id>/skrij/', views.dismiss_user_match, name='dismiss_match'),
]
