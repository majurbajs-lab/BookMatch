"""Management command za uvoz začetnega nabora knjig.

Uporaba: python manage.py load_books

Iz seed_books.json uvozi zvrsti, avtorje in knjige v bazo.
Če knjige/avtor/zvrst že obstaja (glede na ime), jih ne podvoji.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Author, Book, Genre


class Command(BaseCommand):
    help = 'Uvozi začetni nabor knjig iz seed_books.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Pred uvozom izbriši vse obstoječe knjige, avtorje in zvrsti.',
        )

    def handle(self, *args, **options):
        # Najdi seed datoteko
        seed_path = Path(__file__).resolve().parent.parent.parent / 'seed_books.json'
        if not seed_path.exists():
            self.stderr.write(self.style.ERROR(f'Datoteka ne obstaja: {seed_path}'))
            return

        with open(seed_path, encoding='utf-8') as f:
            data = json.load(f)

        if options['reset']:
            self.stdout.write('Brisanje obstoječih podatkov ...')
            Book.objects.all().delete()
            Author.objects.all().delete()
            Genre.objects.all().delete()

        with transaction.atomic():
            # Zvrsti
            genres = {}
            for name in data['genres']:
                genre, created = Genre.objects.get_or_create(name=name)
                genres[name] = genre
                if created:
                    self.stdout.write(f'  + Zvrst: {name}')

            # Knjige (avtorji se ustvarijo sproti)
            added_books = 0
            skipped_books = 0

            for book_data in data['books']:
                # Preveri, ali knjiga že obstaja (po naslovu)
                if Book.objects.filter(title=book_data['title']).exists():
                    skipped_books += 1
                    continue

                # Ustvari ali pridobi avtorje
                authors = []
                for author_name in book_data['authors']:
                    author, _ = Author.objects.get_or_create(name=author_name)
                    authors.append(author)

                # Ustvari knjigo
                book = Book.objects.create(
                    title=book_data['title'],
                    publication_year=book_data.get('publication_year'),
                    language=book_data.get('language', 'sl'),
                    publisher=book_data.get('publisher', ''),
                    page_count=book_data.get('page_count'),
                    description=book_data.get('description', ''),
                    is_approved=True,
                )
                book.authors.set(authors)

                # Poveži z zvrstmi
                book_genres = [genres[g] for g in book_data.get('genres', []) if g in genres]
                book.genres.set(book_genres)

                added_books += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Uvoz končan!\n'
            f'  Zvrsti: {Genre.objects.count()}\n'
            f'  Avtorji: {Author.objects.count()}\n'
            f'  Knjige dodane: {added_books}\n'
            f'  Knjige preskočene (že obstajajo): {skipped_books}\n'
            f'  Skupaj knjig v bazi: {Book.objects.count()}'
        ))
