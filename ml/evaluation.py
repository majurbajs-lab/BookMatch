"""Vrednotenje priporočilnega modela.

Metrike:
- precision@K: delež priporočenih knjig v top-K, ki so uporabniku dejansko všeč
- recall@K: delež vseh všečnih knjig, ki jih najdemo v top-K

Način validacije: train/test split na pozitivnih ocenah uporabnika. Del pozitivnih ocen
skrijemo, treniramo model na ostalih in preverimo, ali model v priporočilih najde knjige,
ki smo jih skrili. Pri tem model pri vrednotenju NE izključuje knjig iz test seta iz
svojih priporočil (sicer bi bile metrike vedno 0).
"""

import logging
import random

import numpy as np
from django.contrib.auth import get_user_model

from books.models import Book
from reading.models import Rating, ReadingEntry
from sklearn.metrics.pairwise import cosine_similarity

from .recommender import ContentBasedRecommender

User = get_user_model()
logger = logging.getLogger(__name__)


class RecommenderEvaluator:
    """Oceni kakovost priporočilnega modela."""

    MIN_RATING_FOR_POSITIVE = 4.0  # ocene >= 4.0 štejemo kot "všeč"

    def __init__(self, recommender: ContentBasedRecommender = None):
        self.recommender = recommender or ContentBasedRecommender()

    def _build_profile_excluding(self, user, excluded_book_ids: set):
        """Zgradi uporabnikov profil, pri čemer izključi določene knjige.

        Uporabljamo pri vrednotenju: knjige iz test seta ne smejo vplivati
        na profil (drugače bi model 'goljufal').
        """
        ratings = Rating.objects.filter(user=user).exclude(book_id__in=excluded_book_ids)

        if ratings.count() < self.recommender.MIN_USER_RATINGS:
            return None

        profile = np.zeros(self.recommender.tfidf_matrix.shape[1])
        total_weight = 0

        for r in ratings:
            idx = self.recommender._book_id_to_idx.get(r.book_id)
            if idx is None:
                continue
            weight = float(r.score) - 3.0
            if weight == 0:
                continue
            book_vector = self.recommender.tfidf_matrix[idx].toarray().flatten()
            profile += weight * book_vector
            total_weight += abs(weight)

        if total_weight == 0:
            return None

        profile = profile / total_weight
        norm = np.linalg.norm(profile)
        if norm > 0:
            profile = profile / norm

        return profile

    def _recommend_for_evaluation(self, user, profile, test_book_ids: set, top_n: int):
        """Pripravi priporočila za vrednotenje.

        KLJUČNA RAZLIKA od običajnega recommend_for_user:
        - Knjig iz test_book_ids NE izključimo (sicer ne bi mogli meriti zadetkov).
        - Izključimo pa knjige, ki jih je uporabnik ocenil in NISO v test setu,
          ter prebrane/opuščene knjige, ki niso v test setu.
        """
        # Izračunaj podobnost z vsemi knjigami
        similarities = cosine_similarity(
            profile.reshape(1, -1),
            self.recommender.tfidf_matrix
        ).flatten()

        # Knjige, ki jih uporabnik je ocenil, RAZEN test seta
        rated_not_in_test = set(
            Rating.objects.filter(user=user)
            .exclude(book_id__in=test_book_ids)
            .values_list('book_id', flat=True)
        )
        # Prebrane/opuščene knjige, RAZEN test seta
        read_not_in_test = set(
            ReadingEntry.objects.filter(user=user, status__in=['read', 'dropped'])
            .exclude(book_id__in=test_book_ids)
            .values_list('book_id', flat=True)
        )
        excluded_ids = rated_not_in_test | read_not_in_test

        # Razvrsti po podobnosti
        ranked_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in ranked_indices:
            book_id = self.recommender.book_ids[idx]
            if book_id in excluded_ids:
                continue
            score = float(similarities[idx])
            if score <= 0:
                continue
            results.append({'book_id': book_id, 'score': score})
            if len(results) >= top_n:
                break

        return results

    def evaluate_user(self, user, k: int = 10, test_size: float = 0.3) -> dict:
        """Vrednoti model za enega uporabnika s train/test splitom."""
        positive_ratings = list(
            Rating.objects.filter(user=user, score__gte=self.MIN_RATING_FOR_POSITIVE)
            .values_list('book_id', flat=True)
        )

        if len(positive_ratings) < 4:
            return {
                'user': user.username,
                'error': f'Premalo pozitivnih ocen (<4): imaš {len(positive_ratings)}',
                'precision_at_k': None,
                'recall_at_k': None,
            }

        random.seed(42)  # ponovljivost
        n_test = max(1, int(len(positive_ratings) * test_size))
        test_book_ids = set(random.sample(positive_ratings, n_test))
        train_book_ids = set(positive_ratings) - test_book_ids

        # Zgradi profil brez test seta
        profile = self._build_profile_excluding(user, test_book_ids)
        if profile is None:
            return {
                'user': user.username,
                'error': 'Profil ni bil zgrajen (premalo netriviajnih ocen).',
                'precision_at_k': None,
                'recall_at_k': None,
            }

        # Pridobi top-K priporočil (brez izločanja test seta!)
        recs = self._recommend_for_evaluation(user, profile, test_book_ids, top_n=k)
        top_k_ids = {r['book_id'] for r in recs}

        # Zadetki = knjige iz test seta, ki so v top-K
        hits = top_k_ids & test_book_ids

        precision = len(hits) / k if k > 0 else 0
        recall = len(hits) / len(test_book_ids) if test_book_ids else 0

        return {
            'user': user.username,
            'train_size': len(train_book_ids),
            'test_size': len(test_book_ids),
            'top_k': k,
            'hits': len(hits),
            'precision_at_k': round(precision, 3),
            'recall_at_k': round(recall, 3),
        }

    def evaluate_all_users(self, k: int = 10, test_size: float = 0.3) -> dict:
        """Vrednoti model na vseh primernih uporabnikih."""
        if self.recommender.tfidf_matrix is None:
            self.recommender.fit()

        eligible_users = User.objects.filter(
            is_active=True,
            ratings__score__gte=self.MIN_RATING_FOR_POSITIVE,
        ).distinct()

        per_user_results = []
        for user in eligible_users:
            result = self.evaluate_user(user, k=k, test_size=test_size)
            per_user_results.append(result)

        valid_results = [r for r in per_user_results if r.get('precision_at_k') is not None]

        if not valid_results:
            return {
                'error': 'Noben uporabnik nima dovolj pozitivnih ocen za vrednotenje.',
                'per_user': per_user_results,
            }

        avg_precision = float(np.mean([r['precision_at_k'] for r in valid_results]))
        avg_recall = float(np.mean([r['recall_at_k'] for r in valid_results]))
        total_hits = sum(r['hits'] for r in valid_results)

        return {
            'n_users_evaluated': len(valid_results),
            'top_k': k,
            'avg_precision_at_k': round(avg_precision, 3),
            'avg_recall_at_k': round(avg_recall, 3),
            'total_hits': total_hits,
            'per_user': per_user_results,
        }

    def get_catalog_stats(self) -> dict:
        """Statistika kataloga (za Model Card)."""
        return {
            'n_books': Book.objects.filter(is_approved=True).count(),
            'n_ratings': Rating.objects.count(),
            'n_users_with_ratings': Rating.objects.values('user').distinct().count(),
            'avg_ratings_per_user': round(
                Rating.objects.count() / max(1, Rating.objects.values('user').distinct().count()),
                2,
            ),
        }

