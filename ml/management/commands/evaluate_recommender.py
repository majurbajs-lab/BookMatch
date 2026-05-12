"""Vrednoti priporočilni model s precision@K in recall@K.

Uporaba:
    python manage.py evaluate_recommender              # K=10
    python manage.py evaluate_recommender --k 5
"""

from django.core.management.base import BaseCommand

from ml.evaluation import RecommenderEvaluator
from ml.recommender import ContentBasedRecommender


class Command(BaseCommand):
    help = 'Vrednoti priporočilni model (precision@K, recall@K).'

    def add_arguments(self, parser):
        parser.add_argument('--k', type=int, default=10, help='Vrednost K (privzeto 10).')

    def handle(self, *args, **options):
        k = options['k']

        self.stdout.write('📊 Vrednotenje priporočilnega modela ...')
        self.stdout.write(f'   K = {k}\n')

        recommender = ContentBasedRecommender()
        recommender.fit()

        evaluator = RecommenderEvaluator(recommender)

        # Statistika kataloga
        stats = evaluator.get_catalog_stats()
        self.stdout.write(self.style.HTTP_INFO('📚 Statistika podatkov:'))
        self.stdout.write(f'   Knjig v katalogu: {stats["n_books"]}')
        self.stdout.write(f'   Skupno ocen: {stats["n_ratings"]}')
        self.stdout.write(f'   Uporabnikov z ocenami: {stats["n_users_with_ratings"]}')
        self.stdout.write(f'   Povprečno ocen na uporabnika: {stats["avg_ratings_per_user"]}\n')

        # Vrednotenje
        results = evaluator.evaluate_all_users(k=k)

        if 'error' in results and not results.get('n_users_evaluated'):
            self.stderr.write(self.style.ERROR(f'\n❌ {results["error"]}'))
            self.stderr.write(self.style.WARNING(
                '\nNasvet: oceni vsaj 4 knjige z oceno 4 ali 5 zvezdic,\n'
                'nato ponovno poženi vrednotenje.'
            ))
            return

        self.stdout.write(self.style.HTTP_INFO(f'\n📈 Rezultati (K={k}):'))
        self.stdout.write(f'   Uporabnikov vrednotenih: {results["n_users_evaluated"]}')
        self.stdout.write(
            f'   Povprečni precision@{k}: '
            f'{self.style.SUCCESS(str(results["avg_precision_at_k"]))}'
        )
        self.stdout.write(
            f'   Povprečni recall@{k}:    '
            f'{self.style.SUCCESS(str(results["avg_recall_at_k"]))}'
        )
        self.stdout.write(f'   Skupno zadetkov: {results["total_hits"]}\n')

        # Podrobnosti po uporabnikih
        self.stdout.write(self.style.HTTP_INFO('👥 Po uporabnikih:'))
        for r in results['per_user']:
            if r.get('error'):
                self.stdout.write(f'   {r["user"]}: {r["error"]}')
            else:
                self.stdout.write(
                    f'   {r["user"]}: train={r["train_size"]}, test={r["test_size"]}, '
                    f'hits={r["hits"]}, P@{k}={r["precision_at_k"]}, R@{k}={r["recall_at_k"]}'
                )

        self.stdout.write(self.style.SUCCESS('\n✓ Vrednotenje končano.'))
        self.stdout.write(
            'Te rezultate lahko uporabiš v razdelku "5.5 Vrednotenje" projektnega zvezka UUI.'
        )
