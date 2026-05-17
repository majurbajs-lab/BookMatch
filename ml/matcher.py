"""Drugi UI model za BookMatch: gručenje bralcev in priporočanje skupin.

== Opis modela ==

Ta modul implementira dve povezani funkcionalnosti:

1. **Gručenje bralcev (K-Means)**: vsakega uporabnika opišemo z žanrskim profilom
   (relativni delež ocen po posameznih zvrsteh) in ga s K-Means uvrstimo v eno
   od K gruč. Znotraj iste gruče izračunamo kosinusno podobnost med uporabniki
   in jih predstavimo drug drugemu kot "bralce s podobnim okusom".

2. **Priporočanje skupin**: vsakega uporabnika ujamemo s skupinami, katerih
   zvrsti se prekrivajo z njegovim žanrskim profilom.

== Zakaj K-Means ==

K-Means je standardni nenadzorovani algoritem gručenja. Primeren je za primere,
kjer ne poznamo vnaprej pravilnih skupin in želimo, da jih algoritem sam najde.
V našem primeru pričakujemo, da se bodo naravno oblikovale skupine kot "ljubitelji
fantazije", "ljubitelji klasike" itd. – algoritem ne pozna imen, samo odkrije
vzorce v podatkih.

Za izbiro števila gruč K uporabimo silhouette score – metriko, ki meri, koliko
dobro se točke v isti gruči ujemajo v primerjavi s točkami iz drugih gruč.
Poskusimo K = 2 do 8 in izberemo tisti, ki daje najvišji silhouette.

== Uporaba ==

    from ml.matcher import ReaderMatcher

    matcher = ReaderMatcher()
    matcher.fit()                   # zgradi profile in izvede K-Means
    matcher.compute_user_matches()  # izračuna pare in shrani v bazo
    matcher.compute_group_suggestions()  # izračuna predloge skupin
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from books.models import Genre
from reading.models import Rating

User = get_user_model()
logger = logging.getLogger(__name__)

MODEL_DIR = Path(settings.BASE_DIR) / 'ml' / 'saved'
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class ReaderMatcher:
    """K-Means gručenje bralcev in priporočanje skupin."""

    # --- KONSTANTE / HIPERPARAMETRI ---
    MIN_USER_RATINGS = 3
    MIN_RATING_FOR_POSITIVE = 3.0

    K_MIN = 2
    K_MAX = 8

    # Pragi za shranjevanje
    MIN_SIMILARITY_FOR_MATCH = 0.3  # pod tem ujemanje ni smiselno
    MAX_MATCHES_PER_USER = 20
    MAX_GROUP_SUGGESTIONS_PER_USER = 10

    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.kmeans: Optional[KMeans] = None
        self.user_ids: list = []
        self.genre_ids: list = []
        self.genre_names: list = []
        self.feature_matrix = None  # normalizirana matrika uporabnikovih profilov
        self.raw_profiles = None    # surovi profili (za priporočanje skupin)
        self.labels: Optional[np.ndarray] = None
        self.k_used: Optional[int] = None
        self.silhouette: Optional[float] = None

    # ===============================================================
    # 1. PRIPRAVA PODATKOV
    # ===============================================================

    def _build_user_profiles(self):
        """Zgradi žanrske profile uporabnikov.

        Za vsakega uporabnika z vsaj MIN_USER_RATINGS ocenami:
        - Preštejemo njegove pozitivne ocene (>= MIN_RATING_FOR_POSITIVE) po zvrsteh.
        - Normiramo po skupnem številu pozitivnih ocen – tako dobimo relativni delež.

        Primer: uporabnik ima 10 pozitivnih ocen, od tega 6 fantazije, 3 krimi, 1 klasika.
        → profil: fantazija 0.6, krimi 0.3, klasika 0.1, drugo 0.0
        """
        genres = list(Genre.objects.all().order_by('id'))
        self.genre_ids = [g.id for g in genres]
        self.genre_names = [g.name for g in genres]
        n_genres = len(genres)
        genre_idx = {g.id: i for i, g in enumerate(genres)}

        # Pripravi za vsakega primernega uporabnika
        user_profiles = {}

        eligible_users = User.objects.filter(is_active=True).prefetch_related('ratings')
        for user in eligible_users:
            positive_ratings = Rating.objects.filter(
                user=user,
                score__gte=self.MIN_RATING_FOR_POSITIVE,
            ).select_related('book').prefetch_related('book__genres')

            if positive_ratings.count() < self.MIN_USER_RATINGS:
                continue

            profile = np.zeros(n_genres)
            total = 0
            for rating in positive_ratings:
                for genre in rating.book.genres.all():
                    if genre.id in genre_idx:
                        profile[genre_idx[genre.id]] += 1
                        total += 1

            if total == 0:
                continue

            profile = profile / total  # normiramo na 1
            user_profiles[user.id] = profile

        if not user_profiles:
            return

        self.user_ids = list(user_profiles.keys())
        self.raw_profiles = np.array([user_profiles[uid] for uid in self.user_ids])

    # ===============================================================
    # 2. UČENJE (fit)
    # ===============================================================

    def fit(self):
        """Pripravi profile in izvede K-Means gručenje.

        Samodejno izbere najboljši K prek silhouette score.
        """
        logger.info('Priprava uporabniških profilov ...')
        self._build_user_profiles()

        if len(self.user_ids) < 2:
            logger.warning(
                'Samo %d uporabnik(ov) ima dovolj ocen. Gručenje ni smiselno.',
                len(self.user_ids),
            )
            return self

        # Standardizacija
        self.scaler = StandardScaler()
        self.feature_matrix = self.scaler.fit_transform(self.raw_profiles)

        # Izberi najboljši K
        n_users = len(self.user_ids)
        k_max = min(self.K_MAX, n_users - 1)

        if n_users < 4:
            # Premalo uporabnikov za smiselno gručenje – vsi v isto gručo
            self.k_used = 1
            self.labels = np.zeros(n_users, dtype=int)
            self.silhouette = None
            logger.info('Manj kot 4 uporabniki – vsi v isto gručo.')
            return self

        best_k = self.K_MIN
        best_score = -1
        best_kmeans = None
        best_labels = None

        for k in range(self.K_MIN, k_max + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(self.feature_matrix)

                # Silhouette score potrebuje vsaj 2 gruči
                if len(set(labels)) < 2:
                    continue

                score = silhouette_score(self.feature_matrix, labels)
                logger.info('K=%d, silhouette=%.3f', k, score)

                if score > best_score:
                    best_score = score
                    best_k = k
                    best_kmeans = kmeans
                    best_labels = labels
            except Exception as e:
                logger.warning('Napaka pri K=%d: %s', k, e)

        self.kmeans = best_kmeans
        self.labels = best_labels
        self.k_used = best_k
        self.silhouette = best_score

        logger.info(
            'Izbran K=%d s silhouette=%.3f (od %d uporabnikov)',
            best_k, best_score, n_users,
        )

        # Shrani cluster_id v Profile
        self._save_cluster_ids()
        return self

    def _save_cluster_ids(self):
        """Posodobi cluster_id na uporabniških profilih."""
        from accounts.models import Profile

        for i, user_id in enumerate(self.user_ids):
            cluster = int(self.labels[i])
            Profile.objects.filter(user_id=user_id).update(cluster_id=cluster)

    # ===============================================================
    # 3. UJEMANJA MED UPORABNIKI
    # ===============================================================

    def compute_user_matches(self):
        """Izračuna pare uporabnikov z najvišjo podobnostjo in jih shrani v bazo.

        Za vsakega uporabnika najdemo druge uporabnike iz iste gruče in
        izračunamo kosinusno podobnost njihovih profilov. Shranimo MAX_MATCHES_PER_USER
        najbolj podobnih parov.
        """
        from matching.models import UserMatch

        if self.feature_matrix is None or len(self.user_ids) < 2:
            logger.warning('Model ni naučen ali premalo uporabnikov.')
            return {}

        # Matrika kosinusnih podobnosti med vsemi pari
        sim_matrix = cosine_similarity(self.feature_matrix)

        # Za vsakega uporabnika najdemo top-N najbolj podobnih
        stats = {}

        # Izbrišemo stare, da ne nastanejo podvojeni pari
        UserMatch.objects.all().delete()

        written_pairs = set()  # da ne pišemo (A,B) in (B,A)

        for i, user_id in enumerate(self.user_ids):
            # Podobnosti z drugimi
            sims = sim_matrix[i].copy()
            sims[i] = -1  # ignoriraj samega sebe

            # Razvrsti od najvišje do najnižje
            sorted_indices = np.argsort(sims)[::-1]

            count = 0
            for j in sorted_indices:
                if count >= self.MAX_MATCHES_PER_USER:
                    break

                other_user_id = self.user_ids[j]
                similarity = float(sims[j])

                if similarity < self.MIN_SIMILARITY_FOR_MATCH:
                    break

                # Preveri, da nismo že zapisali tega para v drugi smeri
                pair_key = tuple(sorted([user_id, other_user_id]))
                if pair_key in written_pairs:
                    continue
                written_pairs.add(pair_key)

                # Pripravi razlago (skupni najljubši žanri)
                shared = self._describe_shared_genres(i, j)

                # Pripiši, kateri gruči pripadata (če sta v isti)
                cluster_id = int(self.labels[i]) if self.labels[i] == self.labels[j] else None

                UserMatch.objects.create(
                    user_a_id=user_id,
                    user_b_id=other_user_id,
                    similarity_score=round(similarity, 3),
                    shared_genres=shared[:255],
                    cluster_id=cluster_id,
                )
                count += 1

            stats[user_id] = count

        return stats

    def _describe_shared_genres(self, i: int, j: int) -> str:
        """Opisi skupnih najbolj priljubljenih zvrsti dveh uporabnikov."""
        profile_i = self.raw_profiles[i]
        profile_j = self.raw_profiles[j]

        # Min vrednosti po žanrih – to so žanri, ki sta jih oba vidno brala
        shared = np.minimum(profile_i, profile_j)
        top_indices = np.argsort(shared)[::-1][:3]

        shared_names = []
        for idx in top_indices:
            if shared[idx] > 0.05:  # vsaj 5 % ocen vsakega
                shared_names.append(self.genre_names[idx])

        if not shared_names:
            return 'Oba imata različen, a združljiv bralni okus.'

        if len(shared_names) == 1:
            return f'Oba rada berete {shared_names[0].lower()}.'

        return 'Oba rada berete ' + ' in '.join(s.lower() for s in shared_names) + '.'

    # ===============================================================
    # 4. PREDLOGI SKUPIN
    # ===============================================================

    def compute_group_suggestions(self):
        """Ujami vsakega uporabnika s skupinami po njegovih najljubših žanrih."""
        from groups.models import ReadingGroup
        from matching.models import GroupSuggestion

        if self.raw_profiles is None or len(self.user_ids) == 0:
            logger.warning('Model ni naučen.')
            return {}

        # Pripravi matriko zvrsti po skupinah (grupa × žanri)
        groups = list(ReadingGroup.objects.prefetch_related('genres'))
        if not groups:
            logger.warning('V sistemu ni skupin.')
            return {}

        n_genres = len(self.genre_ids)
        genre_idx = {gid: i for i, gid in enumerate(self.genre_ids)}

        group_vectors = []
        for group in groups:
            vec = np.zeros(n_genres)
            for g in group.genres.all():
                if g.id in genre_idx:
                    vec[genre_idx[g.id]] = 1
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            group_vectors.append(vec)
        group_matrix = np.array(group_vectors)

        # Za vsakega uporabnika izračunaj podobnost z vsemi skupinami
        stats = {}

        # Izbriši stare predloge
        GroupSuggestion.objects.all().delete()

        for i, user_id in enumerate(self.user_ids):
            user_vec = self.raw_profiles[i]
            # Normiraj uporabnikov profil
            u_norm = np.linalg.norm(user_vec)
            if u_norm == 0:
                continue
            user_vec_normed = user_vec / u_norm

            # Kosinusna podobnost z vsemi skupinami
            similarities = group_matrix @ user_vec_normed

            # Razvrsti od najvišje
            sorted_indices = np.argsort(similarities)[::-1]

            count = 0
            for j in sorted_indices:
                if count >= self.MAX_GROUP_SUGGESTIONS_PER_USER:
                    break

                score = float(similarities[j])
                if score <= 0:
                    break

                group = groups[j]

                # Pripravi razlago
                shared_genre_names = [
                    self.genre_names[k]
                    for k, g in enumerate(group.genres.all())
                    if user_vec[genre_idx.get(g.id, -1)] > 0.05
                    if g.id in genre_idx
                ][:2]

                if shared_genre_names:
                    reason = f"Ker rad bereš {' in '.join(s.lower() for s in shared_genre_names)}."
                else:
                    reason = f"Skupina z žanri: {group.genres_list}."

                GroupSuggestion.objects.create(
                    user_id=user_id,
                    group=group,
                    match_score=round(score, 3),
                    reason=reason[:255],
                )
                count += 1

            stats[user_id] = count

        return stats

    # ===============================================================
    # 5. SHRANJEVANJE
    # ===============================================================

    def save(self, path=None):
        path = path or (MODEL_DIR / 'matcher.joblib')
        data = {
            'scaler': self.scaler,
            'kmeans': self.kmeans,
            'user_ids': self.user_ids,
            'genre_ids': self.genre_ids,
            'genre_names': self.genre_names,
            'feature_matrix': self.feature_matrix,
            'raw_profiles': self.raw_profiles,
            'labels': self.labels,
            'k_used': self.k_used,
            'silhouette': self.silhouette,
        }
        joblib.dump(data, path)
        logger.info('Matcher shranjen v: %s', path)

    def describe_clusters(self) -> dict:
        """Za vsako gručo opiše njene prevladujoče žanre (uporabno za Model Card)."""
        if self.labels is None or self.raw_profiles is None:
            return {}

        description = {}
        for cluster_id in range(self.k_used or 1):
            mask = self.labels == cluster_id
            if not mask.any():
                continue

            avg_profile = self.raw_profiles[mask].mean(axis=0)
            top_indices = np.argsort(avg_profile)[::-1][:3]

            top_genres = [
                (self.genre_names[i], round(float(avg_profile[i]), 3))
                for i in top_indices
                if avg_profile[i] > 0
            ]

            description[cluster_id] = {
                'n_users': int(mask.sum()),
                'top_genres': top_genres,
            }
        return description
