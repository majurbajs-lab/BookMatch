"""Vrednoti K-Means gručenje bralcev (silhouette score).

Uporaba:
    python manage.py evaluate_matcher
"""

from django.core.management.base import BaseCommand
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ml.matcher import ReaderMatcher


class Command(BaseCommand):
    help = 'Vrednoti K-Means model za različne vrednosti K (silhouette score).'

    def handle(self, *args, **options):
        self.stdout.write('📊 Vrednotenje K-Means modela (gručenje bralcev) ...\n')

        matcher = ReaderMatcher()
        matcher._build_user_profiles()

        if len(matcher.user_ids) < 4:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Samo {len(matcher.user_ids)} uporabnik(ov) ima dovolj ocen.\n'
                'Za smiselno vrednotenje potrebujemo vsaj 4 uporabnike.\n'
                'Rešitev: registriraj še kakšnega uporabnika in oceni vsaj 3 knjige.'
            ))
            return

        # Standardiziraj
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        features = scaler.fit_transform(matcher.raw_profiles)

        n_users = len(matcher.user_ids)
        k_max = min(matcher.K_MAX, n_users - 1)

        self.stdout.write(self.style.HTTP_INFO('📈 Silhouette score po K:'))
        results = []
        for k in range(matcher.K_MIN, k_max + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(features)
                if len(set(labels)) < 2:
                    continue
                score = silhouette_score(features, labels)
                results.append((k, score))
                self.stdout.write(f'  K={k}: silhouette = {score:.3f}')
            except Exception as e:
                self.stdout.write(f'  K={k}: napaka ({e})')

        if not results:
            self.stdout.write(self.style.ERROR('❌ Vrednotenje ni uspelo.'))
            return

        best_k, best_score = max(results, key=lambda x: x[1])
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Najboljši K = {best_k} s silhouette = {best_score:.3f}'
        ))

        # Interpretacija
        self.stdout.write(self.style.HTTP_INFO('\n💡 Interpretacija silhouette score:'))
        self.stdout.write('  > 0.5 : zelo dobre, jasno ločene gruče')
        self.stdout.write('  0.25–0.5 : sprejemljive gruče')
        self.stdout.write('  < 0.25 : šibko gručenje (gruče se prekrivajo)')
        self.stdout.write('  < 0    : napačno gručenje (točke so v napačnih gručah)')

        self.stdout.write(self.style.HTTP_INFO(f'\n📝 Tvoj rezultat ({best_score:.3f}):'))
        if best_score > 0.5:
            self.stdout.write(self.style.SUCCESS('  Zelo dobro – gruče so jasno ločene.'))
        elif best_score > 0.25:
            self.stdout.write(self.style.SUCCESS('  Sprejemljivo – pričakovano za šolski projekt.'))
        elif best_score > 0:
            self.stdout.write(self.style.WARNING(
                '  Šibko – gruče se prekrivajo. To je normalno pri malo uporabnikih.'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                '  Slabo – premalo podatkov ali preveč raznolik okus.'
            ))

        # Statistika
        stats = {
            'n_users': n_users,
            'n_genres': len(matcher.genre_ids),
            'best_k': best_k,
            'best_silhouette': round(best_score, 3),
        }
        self.stdout.write(self.style.HTTP_INFO('\n📋 Za Model Card (razdelek 5):'))
        for key, value in stats.items():
            self.stdout.write(f'  {key}: {value}')
