"""Content-based priporočilni model za BookMatch.

== Opis modela ==

Model priporoča knjige na podlagi podobnosti vsebine:
- Vsako knjigo predstavimo kot TF-IDF vektor, zgrajen iz njenih metapodatkov
  (žanri, avtorji, opis).
- Uporabnikov profil izračunamo kot tehtano povprečje vektorjev knjig,
  ki jih je ocenil – višja ocena pomeni večjo utež.
- Priporočamo knjige z najvišjo kosinusno podobnostjo do uporabnikovega profila
  (izključimo knjige, ki jih je že ocenil).

== Zakaj ta pristop ==

Content-based (vsebinsko) filtriranje je primerno za majhne količine podatkov,
kjer kolaborativno filtriranje ne bi delovalo (malo uporabnikov, malo ocen).
Deluje takoj – ne potrebuje ocen drugih uporabnikov. Glavna omejitev je, da se
model "zapre v mehurček" (priporoča samo podobne vsebine) – to v kasnejših
fazah omilimo z raznolikostjo (glej `diversify_recommendations`).

== Uporaba ==

    from ml.recommender import ContentBasedRecommender

    # Enkratni izračun za vse uporabnike:
    recommender = ContentBasedRecommender()
    recommender.fit()                      # pripravi TF-IDF matriko vseh knjig
    recommender.recommend_for_all_users()  # izračuna priporočila

    # Ali za enega uporabnika:
    recs = recommender.recommend_for_user(user, top_n=20)
    # -> seznam slovarjev: [{'book': Book, 'score': 0.82, 'reason': '...'}, ...]
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Max
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from books.models import Book
from reading.models import Rating

User = get_user_model()
logger = logging.getLogger(__name__)

# Mapa, kamor se shrani naučeni model (za ponovno uporabo brez vsakokratnega učenja)
MODEL_DIR = Path(settings.BASE_DIR) / 'ml' / 'saved'
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# Seznam slovenskih stop-words, ki jih odstranimo iz besedil knjig.
# (scikit-learn ima vgrajene stop-words za angleščino, za slovenščino jih moramo podati ročno.)
SLOVENIAN_STOP_WORDS = [
    'in', 'ter', 'ali', 'pa', 'ampak', 'toda', 'čeprav', 'ker',
    'je', 'so', 'bil', 'bila', 'bilo', 'bili', 'bile', 'bi', 'sem', 'si', 'smo', 'ste',
    'ne', 'ni', 'nič', 'nikoli', 'nobenega',
    'se', 'ga', 'jo', 'jih', 'mu', 'ji', 'jim', 'nam', 'vam', 'mi', 'ti', 'on', 'ona', 'ono',
    'v', 'na', 'za', 'po', 'pri', 'pred', 'med', 'čez', 'skozi', 'do', 'od', 'iz', 's', 'z', 'k',
    'ki', 'ko', 'kaj', 'kdo', 'kako', 'kje', 'kam', 'kdaj', 'zakaj',
    'ta', 'to', 'te', 'ti', 'tisti', 'tista', 'tisto', 'tu', 'tam', 'tukaj', 'tja',
    'mi', 'ti', 'on', 'ona', 'ono', 'naj', 'ker', 'le', 'samo', 'tudi', 'še', 'že',
    'kot', 'vse', 'vsak', 'vsi', 'vse', 'več', 'manj', 'precej', 'zelo',
    'ta', 'ga', 'jo', 'tak', 'taka', 'tako', 'tem', 'nje', 'njo', 'njih', 'njegov', 'njen',
    'dva', 'dve', 'tri', 'štiri', 'pet', 'šest', 'deset',
    'leta', 'let', 'dni', 'čas',
]


class ContentBasedRecommender:
    """Content-based priporočilni model z uporabo TF-IDF + kosinusne podobnosti."""

    # --- KONSTANTE / HIPERPARAMETRI ---
    MIN_RATING_FOR_POSITIVE = 3.5  # ocene >= 3.5 se štejejo kot "všeč"
    MIN_USER_RATINGS = 3           # uporabnik potrebuje vsaj toliko ocen za priporočila
    DEFAULT_TOP_N = 20             # privzeto število priporočil na uporabnika

    # --- TF-IDF parametri ---
    TFIDF_MAX_FEATURES = 2000      # največje število besed v besedišču
    TFIDF_MIN_DF = 1               # beseda mora biti vsaj v 1 knjigi
    TFIDF_MAX_DF = 0.85            # ignoriraj besede, ki so v več kot 85 % knjig

    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.book_ids: list = []
        self._book_id_to_idx: dict = {}

    # ===============================================================
    # 1. PRIPRAVA PODATKOV
    # ===============================================================

    @staticmethod
    def _build_book_text(book: Book) -> str:
        """Sestavi besedilo za TF-IDF iz metapodatkov knjige.

        Žanre in avtorje ponovimo večkrat, da imajo večjo utež kot opis,
        ker so najbolj informativni za podobnost.
        """
        parts = []

        # Žanri (utež 3x)
        for genre in book.genres.all():
            parts.extend([genre.name] * 3)

        # Avtorji (utež 2x)
        for author in book.authors.all():
            parts.extend([author.name] * 2)

        # Opis (1x)
        if book.description:
            parts.append(book.description)

        # Založba (1x) – pomaga pri istih zbirkah/urednikih
        if book.publisher:
            parts.append(book.publisher)

        return ' '.join(parts).lower()

    def _collect_book_texts(self):
        """Zbere besedilo in ID vseh potrjenih knjig."""
        books = (
            Book.objects
            .filter(is_approved=True)
            .prefetch_related('authors', 'genres')
            .order_by('id')
        )
        texts = []
        ids = []
        for book in books:
            texts.append(self._build_book_text(book))
            ids.append(book.id)
        return ids, texts

    # ===============================================================
    # 2. UČENJE (fit)
    # ===============================================================

    def fit(self):
        """Zgradi TF-IDF matriko iz vseh knjig v bazi.

        To je "učenje" modela: iz besedil knjig se zgradi besedišče
        in vsaka knjiga postane vektor v tem prostoru besed.
        """
        logger.info('Priprava podatkov za TF-IDF ...')
        self.book_ids, texts = self._collect_book_texts()

        if not texts:
            raise ValueError('V bazi ni nobene knjige. Najprej poženi python manage.py load_books.')

        logger.info('Gradnja TF-IDF matrike za %d knjig ...', len(texts))
        self.vectorizer = TfidfVectorizer(
            max_features=self.TFIDF_MAX_FEATURES,
            min_df=self.TFIDF_MIN_DF,
            max_df=self.TFIDF_MAX_DF,
            stop_words=SLOVENIAN_STOP_WORDS,
            lowercase=True,
            ngram_range=(1, 2),  # posamezne besede in dvojice
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self._book_id_to_idx = {bid: i for i, bid in enumerate(self.book_ids)}

        logger.info(
            'TF-IDF končan. Velikost matrike: %s, besedišče: %d besed.',
            self.tfidf_matrix.shape,
            len(self.vectorizer.vocabulary_),
        )
        return self

    # ===============================================================
    # 3. UPORABNIKOV PROFIL
    # ===============================================================

    def _build_user_profile(self, user) -> Optional[np.ndarray]:
        """Zgradi uporabnikov vektor iz njegovih ocen.

        Vsaka ocenjena knjiga prispeva svoj TF-IDF vektor, utežen z oceno
        (minus nevtralna točka 3.0), tako da negativne ocene delujejo kot
        "odbijanje" od podobnih knjig. Končni vektor normaliziramo.

        Vrne None, če ima uporabnik premalo ocen.
        """
        ratings = Rating.objects.filter(user=user).select_related('book')

        if ratings.count() < self.MIN_USER_RATINGS:
            return None

        # Zgradimo profil kot tehtano vsoto vektorjev ocenjenih knjig
        profile = np.zeros(self.tfidf_matrix.shape[1])
        total_weight = 0

        for rating in ratings:
            idx = self._book_id_to_idx.get(rating.book_id)
            if idx is None:
                continue  # knjiga ni v katalogu (npr. neodobrena)

            # Utež: pozitivna za ocene > 3, negativna za ocene < 3, ~0 za 3
            # npr. ocena 5.0 -> utež +2.0, ocena 1.0 -> utež -2.0
            weight = float(rating.score) - 3.0
            if weight == 0:
                continue

            book_vector = self.tfidf_matrix[idx].toarray().flatten()
            profile += weight * book_vector
            total_weight += abs(weight)

        if total_weight == 0:
            return None

        # Normaliziramo profil
        profile = profile / total_weight

        # L2 normalizacija (za kosinusno podobnost)
        norm = np.linalg.norm(profile)
        if norm > 0:
            profile = profile / norm

        return profile

    # ===============================================================
    # 4. PRIPOROČILA
    # ===============================================================

    def recommend_for_user(self, user, top_n: int = None) -> list:
        """Vrne seznam priporočil za enega uporabnika.

        Vsako priporočilo je slovar: {'book': Book, 'score': float, 'reason': str}
        """
        if self.tfidf_matrix is None:
            raise RuntimeError('Model ni naučen. Najprej pokliči .fit().')

        top_n = top_n or self.DEFAULT_TOP_N

        # Zgradi uporabnikov profil
        profile = self._build_user_profile(user)
        if profile is None:
            logger.info(
                'Uporabnik %s ima premalo ocen (<%d). Priporočila niso na voljo.',
                user.username, self.MIN_USER_RATINGS,
            )
            return []

        # Izračunaj kosinusno podobnost uporabnikovega profila z vsemi knjigami
        similarities = cosine_similarity(
            profile.reshape(1, -1),
            self.tfidf_matrix
        ).flatten()

        # Izključi knjige, ki jih je uporabnik že ocenil ali ima v evidenci
        excluded_ids = set(
            Rating.objects.filter(user=user).values_list('book_id', flat=True)
        )
        from reading.models import ReadingEntry
        excluded_ids.update(
            ReadingEntry.objects.filter(
                user=user, status__in=['read', 'dropped']
            ).values_list('book_id', flat=True)
        )

        # Razvrsti po podobnosti (padajoče)
        ranked_indices = np.argsort(similarities)[::-1]

        # Pripravi rezultate
        results = []
        # Pripravi uporabnikove najljubše knjige (za razlago)
        favorite_books = list(
            Rating.objects
            .filter(user=user, score__gte=self.MIN_RATING_FOR_POSITIVE)
            .select_related('book')
            .order_by('-score', '-updated_at')[:10]
        )

        for idx in ranked_indices:
            book_id = self.book_ids[idx]
            if book_id in excluded_ids:
                continue

            score = float(similarities[idx])
            if score <= 0:
                continue  # nič podobnega

            book = Book.objects.filter(pk=book_id, is_approved=True).first()
            if book is None:
                continue

            reason = self._explain_recommendation(book, favorite_books, idx)

            results.append({
                'book': book,
                'score': round(score, 3),
                'reason': reason,
            })

            if len(results) >= top_n:
                break

        return self.diversify_recommendations(results)

    def _explain_recommendation(self, book, favorite_books, book_idx) -> str:
        """Generira razlago za priporočilo.

        Primerja priporočeno knjigo z uporabnikovimi najljubšimi knjigami
        in vrne razlog glede na največje ujemanje.
        """
        if not favorite_books:
            return 'Priporočeno na podlagi tvojega profila branja.'

        # Najdi najbolj podobno knjigo iz uporabnikovih najljubših
        best_match = None
        best_similarity = 0

        for fav_rating in favorite_books:
            fav_idx = self._book_id_to_idx.get(fav_rating.book_id)
            if fav_idx is None:
                continue

            sim = cosine_similarity(
                self.tfidf_matrix[fav_idx],
                self.tfidf_matrix[book_idx],
            )[0, 0]

            if sim > best_similarity:
                best_similarity = sim
                best_match = fav_rating.book

        if best_match is None:
            return 'Priporočeno na podlagi tvojega profila branja.'

        # Preveri skupne zvrsti in avtorje
        shared_genres = set(book.genres.values_list('name', flat=True)) & \
                        set(best_match.genres.values_list('name', flat=True))
        shared_authors = set(book.authors.values_list('name', flat=True)) & \
                         set(best_match.authors.values_list('name', flat=True))

        if shared_authors:
            author = list(shared_authors)[0]
            return f'Istega avtorja ({author}) kot »{best_match.title}«, ki ti je bila všeč.'
        elif shared_genres:
            genre = list(shared_genres)[0]
            return f'Podobno kot »{best_match.title}« ({genre.lower()}), ki ti je bila všeč.'
        else:
            return f'Podobno kot »{best_match.title}«, ki ti je bila všeč.'

    def diversify_recommendations(self, recommendations: list, max_per_author: int = 2) -> list:
        """Zagotovi raznolikost – omejimo število predlogov istega avtorja.

        Brez tega bi model pogosto priporočal 10 knjig istega avtorja.
        """
        if not recommendations:
            return recommendations

        author_counts = {}
        diversified = []

        for rec in recommendations:
            authors = [a.name for a in rec['book'].authors.all()]
            # Preveri, ali je katerikoli od avtorjev že dosegel mejo
            if any(author_counts.get(a, 0) >= max_per_author for a in authors):
                continue
            diversified.append(rec)
            for a in authors:
                author_counts[a] = author_counts.get(a, 0) + 1

        return diversified

    # ===============================================================
    # 5. IZRAČUN ZA VSE UPORABNIKE
    # ===============================================================

    def recommend_for_all_users(self) -> dict:
        """Izračuna priporočila za vse aktivne uporabnike z dovolj ocenami.

        Rezultati se shranijo v bazo (tabela Recommendation).
        Vrne slovar: {user_id: število_priporočil}
        """
        from recommendations.models import Recommendation

        # Najdi uporabnike, ki imajo dovolj ocen
        eligible_users = User.objects.filter(
            is_active=True,
            ratings__isnull=False,
        ).distinct().annotate(
            last_rating=Max('ratings__updated_at')
        )

        stats = {}
        for user in eligible_users:
            try:
                recs = self.recommend_for_user(user, top_n=self.DEFAULT_TOP_N)
            except Exception as e:
                logger.error('Napaka pri izračunu za uporabnika %s: %s', user.username, e)
                continue

            if not recs:
                continue

            # Pobriši stara priporočila
            Recommendation.objects.filter(user=user).delete()

            # Shrani nova
            Recommendation.objects.bulk_create([
                Recommendation(
                    user=user,
                    book=r['book'],
                    score=r['score'],
                    reason=r['reason'][:255],
                ) for r in recs
            ])
            stats[user.id] = len(recs)
            logger.info('Uporabnik %s: %d priporočil', user.username, len(recs))

        return stats

    # ===============================================================
    # 6. SHRANJEVANJE / NALAGANJE (joblib)
    # ===============================================================

    def save(self, path=None):
        """Shrani naučen model v datoteko."""
        path = path or (MODEL_DIR / 'recommender.joblib')
        data = {
            'vectorizer': self.vectorizer,
            'tfidf_matrix': self.tfidf_matrix,
            'book_ids': self.book_ids,
        }
        joblib.dump(data, path)
        logger.info('Model shranjen v: %s', path)

    def load(self, path=None):
        """Naloži predhodno shranjen model."""
        path = path or (MODEL_DIR / 'recommender.joblib')
        data = joblib.load(path)
        self.vectorizer = data['vectorizer']
        self.tfidf_matrix = data['tfidf_matrix']
        self.book_ids = data['book_ids']
        self._book_id_to_idx = {bid: i for i, bid in enumerate(self.book_ids)}
        return self
