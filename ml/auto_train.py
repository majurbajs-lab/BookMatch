"""Samodejni trening ML modelov ob spremembah ocen.

Trening teče sinhrono v request threadu, vendar kvečjemu enkrat na 60 sekund
(THROTTLE_SECONDS). Sinhronizacija je zanesljiva na vseh platformah, vključno
z PythonAnywhere, kjer zunanji procesi in daemon niti niso zanesljivi.
"""

import logging
import tempfile
import time
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.db.models import Count

logger = logging.getLogger(__name__)

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


def _run_sync(cmd_name: str):
    from django.core.management import call_command
    try:
        call_command(cmd_name, stdout=StringIO(), stderr=StringIO())
        logger.info('auto_train %s: OK', cmd_name)
    except Exception:
        logger.exception('auto_train %s: napaka', cmd_name)


def maybe_train_recommender():
    """Zaženi train_recommender sinhrono, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_RECOMMENDER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_RECOMMENDER_STAMP)
    _run_sync('train_recommender')


def maybe_train_matcher():
    """Zaženi train_matcher sinhrono, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_MATCHER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_MATCHER_STAMP)
    _run_sync('train_matcher')
