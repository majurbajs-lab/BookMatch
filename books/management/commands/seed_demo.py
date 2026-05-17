"""Ustvari demo uporabnike z ocenami za testiranje ML modelov.

Uporaba:
    python manage.py seed_demo
    python manage.py seed_demo --clear   # najprej pobriše stare demo uporabnike
"""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from books.models import Book, Genre
from reading.models import Rating, ReadingEntry

User = get_user_model()

DEMO_PASSWORD = 'geslo123'

# Vsak profil: (username, ime, prezime, prefereni zanri s tezami)
PROFILES = [
    ('ana_k',      'Ana',     'Kos',      {'Fantazija': 0.5, 'Pustolovščina': 0.3, 'Mladinska': 0.2}),
    ('bor_n',      'Bor',     'Novak',    {'Krimi': 0.5, 'Triler': 0.35, 'Grozljivka': 0.15}),
    ('cvetka_m',   'Cvetka',  'Možič',    {'Klasika': 0.45, 'Literarna proza': 0.35, 'Romanca': 0.2}),
    ('david_p',    'David',   'Pirnat',   {'Znanstvena fantastika': 0.5, 'Distopija': 0.35, 'Fantazija': 0.15}),
    ('eva_z',      'Eva',     'Zorko',    {'Romanca': 0.5, 'Biografija': 0.3, 'Klasika': 0.2}),
    ('filip_h',    'Filip',   'Hren',     {'Filozofija': 0.45, 'Esejistika': 0.35, 'Klasika': 0.2}),
    ('gaja_s',     'Gaja',    'Sitar',    {'Mladinska': 0.4, 'Fantazija': 0.35, 'Pustolovščina': 0.25}),
    ('hugo_b',     'Hugo',    'Bernik',   {'Zgodovinski roman': 0.5, 'Biografija': 0.3, 'Klasika': 0.2}),
    ('iris_v',     'Iris',    'Vidmar',   {'Literarna proza': 0.45, 'Romanca': 0.3, 'Poezija': 0.25}),
    ('jan_k',      'Jan',     'Kralj',    {'Krimi': 0.4, 'Triler': 0.4, 'Distopija': 0.2}),
    ('katja_m',    'Katja',   'Mlakar',   {'Fantazija': 0.4, 'Znanstvena fantastika': 0.4, 'Distopija': 0.2}),
    ('luka_c',     'Luka',    'Černe',    {'Filozofija': 0.4, 'Esejistika': 0.3, 'Biografija': 0.3}),
    ('maja_r',     'Maja',    'Remic',    {'Romanca': 0.45, 'Klasika': 0.3, 'Literarna proza': 0.25}),
    ('nik_o',      'Nik',     'Oblak',    {'Pustolovščina': 0.4, 'Mladinska': 0.3, 'Fantazija': 0.3}),
    ('petra_g',    'Petra',   'Gaspari',  {'Grozljivka': 0.45, 'Triler': 0.35, 'Krimi': 0.2}),
]


def _genre_map():
    return {g.name: g for g in Genre.objects.all()}


def _books_by_genre(genre_map):
    result = {}
    for name, genre in genre_map.items():
        result[name] = list(Book.objects.filter(genres=genre))
    return result


def _pick_books(preferences, books_by_genre, n=20):
    """Izberi n knjig glede na težo preferenc žanrov."""
    genres = list(preferences.keys())
    weights = [preferences[g] for g in genres]
    chosen = []
    seen = set()
    attempts = 0
    while len(chosen) < n and attempts < n * 10:
        attempts += 1
        genre = random.choices(genres, weights=weights, k=1)[0]
        pool = books_by_genre.get(genre, [])
        if not pool:
            continue
        book = random.choice(pool)
        if book.id not in seen:
            seen.add(book.id)
            chosen.append((book, genre))
    return chosen


def _score_for(genre_name, preferences):
    """Visoka ocena za priljubljen žanr, nižja za ostale."""
    weight = preferences.get(genre_name, 0)
    if weight >= 0.4:
        return round(random.uniform(4.0, 5.0), 1)
    elif weight >= 0.15:
        return round(random.uniform(3.0, 4.5), 1)
    else:
        return round(random.uniform(2.0, 3.5), 1)


class Command(BaseCommand):
    help = 'Ustvari demo uporabnike z ocenami za testiranje ML modelov.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Najprej pobriši obstoječe demo uporabnike.')

    def handle(self, *args, **options):
        if options['clear']:
            usernames = [p[0] for p in PROFILES]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(self.style.WARNING(f'Izbrisanih {deleted} demo uporabnikov.'))

        genre_map = _genre_map()
        if not genre_map:
            self.stdout.write(self.style.ERROR('Ni žanrov – najprej zaženi load_books.'))
            return

        books_by_genre = _books_by_genre(genre_map)
        total_books = Book.objects.count()
        if total_books < 20:
            self.stdout.write(self.style.ERROR(f'Premalo knjig ({total_books}) – najprej zaženi load_books.'))
            return

        created_users = 0
        created_ratings = 0

        for username, first, last, preferences in PROFILES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'email': f'{username}@bookmatch.si',
                    'is_active': True,
                }
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                created_users += 1
                self.stdout.write(f'  Ustvarjen: {username}')
            else:
                self.stdout.write(f'  Že obstaja: {username}')

            # Dodaj ocene (preskoči, če jih ima že dovolj)
            existing = Rating.objects.filter(user=user).count()
            if existing >= 15:
                self.stdout.write(f'    → Že ima {existing} ocen, preskok.')
                continue

            picks = _pick_books(preferences, books_by_genre, n=22)
            for book, genre_name in picks:
                score = _score_for(genre_name, preferences)
                Rating.objects.get_or_create(
                    user=user,
                    book=book,
                    defaults={'score': score},
                )
                # Dodaj v bralno evidenco kot "prebrano"
                try:
                    ReadingEntry.objects.get_or_create(
                        user=user,
                        book=book,
                        defaults={'status': 'read'},
                    )
                except Exception:
                    pass
                created_ratings += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nOK: {created_users} novih uporabnikov, {created_ratings} novih ocen.'
        ))
        self.stdout.write(
            f'Geslo za vse demo uporabnike: {DEMO_PASSWORD}'
        )
        self.stdout.write(
            '\nSedaj zaženi: python manage.py train_recommender && python manage.py train_matcher'
        )
