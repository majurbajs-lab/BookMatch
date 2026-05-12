import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class MlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ml'
    verbose_name = 'Strojno učenje'

    def ready(self):
        # Zaženi samo v glavnem server procesu, ne pri vsakem manage.py ukazu.
        # RUN_MAIN=true pomeni da smo v reloader child procesu (dejanski server).
        # --noreload: RUN_MAIN ni nastavljen, preverimo sys.argv.
        import sys
        is_runserver = 'runserver' in sys.argv
        is_main_process = os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv
        if not (is_runserver and is_main_process):
            return

        thread = threading.Thread(target=self._train_models, daemon=True)
        thread.start()

    def _train_models(self):
        try:
            from ml.matcher import ReaderMatcher
            from ml.recommender import ContentBasedRecommender

            logger.info('[ML] Treniram priporocilni model ...')
            recommender = ContentBasedRecommender()
            recommender.fit()
            recommender.recommend_for_all_users()
            logger.info('[ML] Priporocilni model OK.')

            logger.info('[ML] Treniram matcher model ...')
            matcher = ReaderMatcher()
            matcher.fit()
            if len(matcher.user_ids) >= 2:
                matcher.compute_user_matches()
                matcher.compute_group_suggestions()
            logger.info('[ML] Matcher model OK.')

        except Exception:
            logger.exception('[ML] Napaka pri treniranju modelov.')
