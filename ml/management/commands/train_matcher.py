"""Treniraj K-Means model in izračunaj ujemanja + predloge skupin.

Uporaba:
    python manage.py train_matcher
    python manage.py train_matcher --save
"""

from django.core.management.base import BaseCommand

from ml.matcher import ReaderMatcher


class Command(BaseCommand):
    help = 'Natreniraj K-Means model za ujemanje bralcev in izračunaj predloge skupin.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--save', action='store_true',
            help='Shrani naučeni model v datoteko.',
        )

    def handle(self, *args, **options):
        self.stdout.write('Treniram K-Means model za ujemanje bralcev ...')

        matcher = ReaderMatcher()
        matcher.fit()

        if len(matcher.user_ids) < 2:
            self.stdout.write(self.style.WARNING(
                f'\nSamo {len(matcher.user_ids)} uporabnik(ov) ima dovolj ocen.\n'
                'Za ujemanja potrebujemo vsaj 2 uporabnika.'
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\nOK Model naučen:\n'
            f'  Uporabnikov: {len(matcher.user_ids)}\n'
            f'  Zvrsti: {len(matcher.genre_ids)}\n'
            f'  Število gruč (K): {matcher.k_used}\n'
            f'  Silhouette score: {matcher.silhouette:.3f}' if matcher.silhouette is not None
            else f'  Silhouette score: N/A (premalo podatkov)'
        ))

        # Pokaži opise gruč
        clusters = matcher.describe_clusters()
        if clusters:
            self.stdout.write(self.style.HTTP_INFO('\nOpis gruc:'))
            for cluster_id, info in clusters.items():
                top_str = ', '.join(f'{name} ({score:.0%})' for name, score in info['top_genres'])
                self.stdout.write(f'  Gruča {cluster_id}: {info["n_users"]} uporabnikov, prevladujejo: {top_str}')

        # Izračun ujemanj uporabnikov
        self.stdout.write('\nRacunam ujemanja bralcev ...')
        match_stats = matcher.compute_user_matches()
        total_matches = sum(match_stats.values())
        self.stdout.write(self.style.SUCCESS(
            f'OK Shranjenih ujemanj: {total_matches}'
        ))

        # Izračun predlogov skupin
        self.stdout.write('\nRacunam predloge skupin ...')
        group_stats = matcher.compute_group_suggestions()
        total_suggestions = sum(group_stats.values())
        self.stdout.write(self.style.SUCCESS(
            f'OK Shranjenih predlogov skupin: {total_suggestions}'
        ))

        if options['save']:
            matcher.save()
            self.stdout.write(self.style.SUCCESS('\nOK Model shranjen v ml/saved/matcher.joblib'))
