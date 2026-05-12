"""Ustvari začetne skupine, eno za vsako zvrst v katalogu.

Uporaba: python manage.py create_starter_groups
"""

from django.core.management.base import BaseCommand

from books.models import Genre
from groups.models import ReadingGroup


# Predlogi opisa za vsako zvrst (v slovenščini, za lepši prikaz)
GROUP_DESCRIPTIONS = {
    'Fantazija': 'Prostor za ljubitelje fantazijskih svetov, zmajev, čarovnikov in epskih pustolovščin. Od Tolkiena do Martina – vse je dobrodošlo.',
    'Znanstvena fantastika': 'Skupina za navdušence nad prihodnostjo, vesoljem, umetno inteligenco in alternativnimi realnostmi. Debatiramo o Asimovu, Herbertu in vsem vmes.',
    'Krimi': 'Detektivi, sledi, nepričakovani zasuki. Tu izmenjujemo mnenja o najboljših krimi romanih – od Agathe Christie do skandinavskih noir mojstrov.',
    'Triler': 'Napeti romani, psihološke drame in zgodbe, ki te držijo buden pozno v noč. Za vse, ki obožujejo adrenalin na straneh.',
    'Romanca': 'Ljubezenske zgodbe vseh vrst, od klasike do sodobnih hitov. Deli najljubše romantične knjige in pari.',
    'Zgodovinski roman': 'Potovanja skozi čas – od srednjega veka do 20. stoletja. Za vse, ki radi združujejo branje z zgodovino.',
    'Klasika': 'Dostojevski, Tolstoj, Austen, Dickens. Skupina za ljubitelje večnih knjig, ki ostajajo relevantne skozi stoletja.',
    'Literarna proza': 'Sodobna proza, literarni slog, jezikovno bogastvo. Za tiste, ki v branju iščejo več kot le zgodbo.',
    'Biografija': 'Življenjske zgodbe zanimivih ljudi, avtobiografije, spomini. Od Steva Jobsa do Anne Frank.',
    'Esejistika': 'Knjige, ki te navdušijo in dajo misliti. Sapiens, Misliti hitro in počasi – in vse ostale.',
    'Mladinska': 'Za vse, ki še vedno uživamo v mladinskih knjigah – in za starše, ki iščejo priporočila za svoje otroke.',
    'Grozljivka': 'Stephen King, gotski romani, sodobne psihološke grozljivke. Če ti je všeč strah na varni razdalji, si tukaj doma.',
    'Distopija': '1984, Krasni novi svet, Igre lakote. Skupina za raziskovalce alternativnih (in pogosto zloveščih) svetov.',
    'Pustolovščina': 'Avanture, raziskovanja, potovanja. Knjige, ki te odpeljejo daleč od vsakdanjika.',
    'Filozofija': 'Od Nietzscheja do Frankla. Za bralce, ki v knjigah iščejo odgovore na velika vprašanja.',
    'Poezija': 'Prešeren, Kosovel, Zajc – in tudi sodobni pesniki. Prostor za ljubitelje poetike in ritma.',
}


class Command(BaseCommand):
    help = 'Ustvari začetne skupine – eno za vsako zvrst v katalogu.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Izbriši obstoječe sistemske skupine (brez lastnika) in jih ustvari na novo.',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Brisanje obstoječih sistemskih skupin ...')
            ReadingGroup.objects.filter(owner__isnull=True).delete()

        created = 0
        skipped = 0

        for genre in Genre.objects.all():
            group_name = f'{genre.name} – bralci'

            if ReadingGroup.objects.filter(name=group_name).exists():
                skipped += 1
                continue

            description = GROUP_DESCRIPTIONS.get(
                genre.name,
                f'Skupina za bralce zvrsti {genre.name}. Deli priporočila, mnenja in odkritja.'
            )

            group = ReadingGroup.objects.create(
                name=group_name,
                description=description,
                visibility='public',
                owner=None,  # sistemska skupina
            )
            group.genres.add(genre)
            created += 1
            self.stdout.write(f'  + {group_name}')

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Končano!\n'
            f'  Ustvarjenih novih skupin: {created}\n'
            f'  Preskočenih (že obstajajo): {skipped}\n'
            f'  Skupaj skupin v sistemu: {ReadingGroup.objects.count()}'
        ))
