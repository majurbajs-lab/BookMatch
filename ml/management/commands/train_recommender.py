"""Treniraj priporočilni model in izračunaj priporočila za vse uporabnike.

Uporaba:
    python manage.py train_recommender                    # natreniraj in izračunaj
    python manage.py train_recommender --save             # dodatno shrani model
    python manage.py train_recommender --user-id 1        # samo za enega uporabnika
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ml.recommender import ContentBasedRecommender

User = get_user_model()


class Command(BaseCommand):
    help = 'Natreniraj priporočilni model in izračunaj priporočila.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--save', action='store_true',
            help='Shrani naučeni model v datoteko (za hitrejše naslednje nalaganje).',
        )
        parser.add_argument(
            '--user-id', type=int, default=None,
            help='Izračunaj priporočila samo za enega uporabnika (ID).',
        )

    def handle(self, *args, **options):
        self.stdout.write('Treniram priporocilni model ...')

        recommender = ContentBasedRecommender()
        recommender.fit()

        self.stdout.write(self.style.SUCCESS(
            f'OK Model naucen: {recommender.tfidf_matrix.shape[0]} knjig, '
            f'{recommender.tfidf_matrix.shape[1]} znacilk.'
        ))

        if options['save']:
            recommender.save()
            self.stdout.write(self.style.SUCCESS('OK Model shranjen v ml/saved/recommender.joblib'))

        if options['user_id']:
            try:
                user = User.objects.get(pk=options['user_id'])
            except User.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Uporabnik z ID {options["user_id"]} ne obstaja.'))
                return

            recs = recommender.recommend_for_user(user)
            self.stdout.write(f'\nPriporocila za {user.username}:')
            if not recs:
                self.stdout.write(self.style.WARNING(
                    '  Ni priporocil - verjetno premalo ocen (potrebne so vsaj 3).'
                ))
            else:
                for i, rec in enumerate(recs[:10], 1):
                    self.stdout.write(f'  {i}. {rec["book"].title} (score: {rec["score"]})')
                    self.stdout.write(f'     Razlog: {rec["reason"]}')
        else:
            self.stdout.write('\nRacunam priporocila za vse uporabnike ...')
            stats = recommender.recommend_for_all_users()

            if not stats:
                self.stdout.write(self.style.WARNING(
                    '\nNobeden uporabnik nima dovolj ocen. '
                    'Potrebne so vsaj 3 ocene, ki niso enake 3.0 (nevtralna).'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'\nOK Izracunana priporocila za {len(stats)} uporabnikov.'
                ))
                for user_id, count in stats.items():
                    user = User.objects.get(pk=user_id)
                    self.stdout.write(f'  {user.username}: {count} priporocil')
