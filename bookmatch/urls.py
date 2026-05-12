"""Glavne URL poti projekta BookMatch.
Posodobljeno za Fazo 5B – dodane poti za messaging.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('books/', include('books.urls')),
    path('reading/', include('reading.urls')),
    path('recommendations/', include('recommendations.urls')),
    path('groups/', include('groups.urls')),
    path('matching/', include('matching.urls')),
    path('loans/', include('loans.urls')),
    path('sporocila/', include('messaging.urls')),  # NOVO v Fazi 5B
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
