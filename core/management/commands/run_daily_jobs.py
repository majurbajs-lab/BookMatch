"""Dnevni ML job – zažene se ob 12:00 prek Windows Task Schedulerja.

Uporaba:
    python manage.py run_daily_jobs

Naredi:
1. Izračuna top 10 knjig po povprečni oceni → shrani v TopBook
2. Zažene priporočilni model → shrani top 10 priporočil na uporabnika
3. Zažene K-Means matcher → shrani top 5 bralcev + top 5 skupin na uporabnika
4. Zapiše timestamp v DailyJobLog
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()

TOP_BOOKS_COUNT = 10
TOP_RECOMMENDATIONS_PER_USER = 10
TOP_MATCHES_PER_USER = 5
TOP_GROUPS_PER_USER = 5


class Command(BaseCommand):
    help = 'Dnevni ML job: top knjige, priporočila, ujemanja bralcev in skupin.'

    def handle(self, *args, **options):
        self.stdout.write(f'\n=== Dnevni ML job – {timezone.now():%d.%m.%Y %H:%M} ===\n')

        self._run_top_books()
        self._run_recommendations()
        self._run_matching()

        self.stdout.write(self.style.SUCCESS('\n=== Job uspešno zaključen ===\n'))

    # ------------------------------------------------------------------
    # 1. Top knjige
    # ------------------------------------------------------------------

    def _run_top_books(self):
        from books.models import Book, TopBook
        from core.models import DailyJobLog

        self.stdout.write('1. Izračunam top knjige ...')

        books = (
            Book.objects
            .filter(is_approved=True, ratings_count__gt=0)
            .order_by('-average_rating', '-ratings_count')[:TOP_BOOKS_COUNT]
        )

        with transaction.atomic():
            TopBook.objects.all().delete()
            for rank, book in enumerate(books, start=1):
                TopBook.objects.create(
                    rank=rank,
                    book=book,
                    average_rating=book.average_rating,
                    ratings_count=book.ratings_count,
                )

        DailyJobLog.objects.update_or_create(
            job_name=DailyJobLog.JOB_TOP_BOOKS,
            defaults={'last_run_at': timezone.now(), 'users_processed': len(books)},
        )
        self.stdout.write(self.style.SUCCESS(f'   OK – shranjenih {len(books)} top knjig.'))

    # ------------------------------------------------------------------
    # 2. Priporočila knjig
    # ------------------------------------------------------------------

    def _run_recommendations(self):
        from core.models import DailyJobLog
        from ml.recommender import ContentBasedRecommender
        from recommendations.models import Recommendation

        self.stdout.write('2. Treniram priporočilni model ...')

        recommender = ContentBasedRecommender()
        try:
            recommender.fit()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'   NAPAKA pri treniranju: {exc}'))
            return

        self.stdout.write('   Izračunam priporočila za vse uporabnike ...')
        stats = recommender.recommend_for_all_users()

        # Trimam na top 10 na uporabnika (model vrne do 20)
        users_processed = 0
        for user_id in stats:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                continue
            keep_ids = list(
                Recommendation.objects
                .filter(user=user)
                .order_by('-score')
                .values_list('id', flat=True)[:TOP_RECOMMENDATIONS_PER_USER]
            )
            Recommendation.objects.filter(user=user).exclude(id__in=keep_ids).delete()
            users_processed += 1

        DailyJobLog.objects.update_or_create(
            job_name=DailyJobLog.JOB_RECOMMENDATIONS,
            defaults={'last_run_at': timezone.now(), 'users_processed': users_processed},
        )
        self.stdout.write(self.style.SUCCESS(
            f'   OK – priporočila izračunana za {users_processed} uporabnikov '
            f'(max {TOP_RECOMMENDATIONS_PER_USER} na uporabnika).'
        ))

    # ------------------------------------------------------------------
    # 3. Ujemanja bralcev in skupin
    # ------------------------------------------------------------------

    def _run_matching(self):
        from core.models import DailyJobLog
        from matching.models import GroupSuggestion, UserMatch
        from ml.matcher import ReaderMatcher

        self.stdout.write('3. Treniram K-Means matcher ...')

        matcher = ReaderMatcher()
        try:
            matcher.fit()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'   NAPAKA pri treniranju: {exc}'))
            return

        if len(matcher.user_ids) == 0:
            self.stdout.write(self.style.WARNING('   Ni uporabnikov z dovolj ocenami – preskočim.'))
            return

        # Predlogi skupin
        self.stdout.write('   Izračunam predloge skupin ...')
        matcher.compute_group_suggestions()

        # Trimam na top 5 skupin na uporabnika
        for user_id in matcher.user_ids:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                continue
            keep_ids = list(
                GroupSuggestion.objects
                .filter(user=user)
                .order_by('-match_score')
                .values_list('id', flat=True)[:TOP_GROUPS_PER_USER]
            )
            GroupSuggestion.objects.filter(user=user).exclude(id__in=keep_ids).delete()

        # Ujemanja bralcev (zahteva vsaj 2 uporabnika)
        if len(matcher.user_ids) >= 2:
            self.stdout.write('   Izračunam ujemanja bralcev ...')
            matcher.compute_user_matches()

            # Trimam na top 5 ujemanj na uporabnika
            from django.db.models import Q
            for user_id in matcher.user_ids:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    continue
                keep_ids = list(
                    UserMatch.objects
                    .filter(Q(user_a=user) | Q(user_b=user))
                    .order_by('-similarity_score')
                    .values_list('id', flat=True)[:TOP_MATCHES_PER_USER]
                )
                UserMatch.objects.filter(
                    Q(user_a=user) | Q(user_b=user)
                ).exclude(id__in=keep_ids).delete()
        else:
            self.stdout.write(self.style.WARNING(
                f'   Samo {len(matcher.user_ids)} uporabnik – ujemanja bralcev preskočim.'
            ))

        DailyJobLog.objects.update_or_create(
            job_name=DailyJobLog.JOB_MATCHING,
            defaults={'last_run_at': timezone.now(), 'users_processed': len(matcher.user_ids)},
        )
        self.stdout.write(self.style.SUCCESS(
            f'   OK – ujemanja izračunana za {len(matcher.user_ids)} uporabnikov '
            f'(max {TOP_MATCHES_PER_USER} bralcev, {TOP_GROUPS_PER_USER} skupin na uporabnika).'
        ))
