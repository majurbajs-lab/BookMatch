"""Samodejni trening ML modelov ob spremembah ocen.

Trening se zažene kot ločen podproces, kar je zanesljivo tudi na WSGI strežnikih
(uWSGI/PythonAnywhere), kjer se daemon niti ubijejo med zahtevami.
"""

import logging
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path

from django.db.models import Count

logger = logging.getLogger(__name__)

# Največ enkrat na minuto
THROTTLE_SECONDS = 60

_TMP = Path(tempfile.gettempdir())
_RECOMMENDER_STAMP = _TMP / 'bm_recommender.txt'
_MATCHER_STAMP = _TMP / 'bm_matcher.txt'


def _last_run(stamp: Path) -> float:
    try:
        return float(stamp.read_text())
    except (FileNotFoundError, ValueError):
        return 0.0


def _mark_run(stamp: Path):
    stamp.write_text(str(time.time()))


def _eligible_users_count() -> int:
    """Vrni število uporabnikov z vsaj 3 ne-nevtralnimi ocenami."""
    from reading.models import Rating
    return (
        Rating.objects
        .exclude(score=Decimal('3.0'))
        .values('user')
        .annotate(n=Count('id'))
        .filter(n__gte=3)
        .count()
    )


def _spawn(cmd_name: str):
    """Zaženi management command kot neodvisen podproces."""
    try:
        from django.conf import settings
        manage_py = str(Path(settings.BASE_DIR) / 'manage.py')
        subprocess.Popen(
            [sys.executable, manage_py, cmd_name],
            cwd=str(settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info('auto_train: zagnan %s', cmd_name)
    except Exception:
        logger.exception('auto_train %s: napaka pri zagonu', cmd_name)


def maybe_train_recommender():
    """Zaženi train_recommender v ozadju, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_RECOMMENDER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_RECOMMENDER_STAMP)
    _spawn('train_recommender')


def maybe_train_matcher():
    """Zaženi train_matcher v ozadju, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_MATCHER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_MATCHER_STAMP)
    _spawn('train_matcher')
