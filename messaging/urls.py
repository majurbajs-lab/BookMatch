"""URL poti za aplikacijo messaging."""

from django.urls import path

from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('pogovor/<int:conversation_id>/', views.conversation_detail, name='detail'),
    path('zacni/<str:username>/', views.start_conversation, name='start'),
]
