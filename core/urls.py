"""URL poti za aplikacijo core."""

from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('o-nas/', views.about, name='about'),
]
