"""URL poti za aplikacijo accounts."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Registracija
    path('register/', views.register, name='register'),

    # Prijava / odjava (uporabimo vgrajene Django poglede)
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Profil
    path('profile/', views.profile_view, name='profile_view_me'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/<str:username>/', views.profile_view, name='profile_view'),
]
