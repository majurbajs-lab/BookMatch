"""Samodejni asinhronski trening ML modelov ob spremembah ocen."""

import logging
import tempfile
import threading
import time
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.db.models import Count

logger = logging.getLogger(__name__)

# Največ enkrat na uro, da ne obremenjujemo baze
THROTTLE_SECONDS = 3600

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


def _run_recommender():
    try:
        from django.core.management import call_command
        call_command('train_recommender', stdout=StringIO(), stderr=StringIO())
        logger.info('auto_train recommender: OK')
    except Exception:
        logger.exception('auto_train recommender: napaka')
    finally:
        from django.db import connection
        connection.close()


def _run_matcher():
    try:
        from django.core.management import call_command
        call_command('train_matcher', stdout=StringIO(), stderr=StringIO())
        logger.info('auto_train matcher: OK')
    except Exception:
        logger.exception('auto_train matcher: napaka')
    finally:
        from django.db import connection
        connection.close()


def maybe_train_recommender():
    """Zaženi train_recommender v ozadju, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_RECOMMENDER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_RECOMMENDER_STAMP)
    threading.Thread(target=_run_recommender, daemon=True).start()


def maybe_train_matcher():
    """Zaženi train_matcher v ozadju, če so pogoji izpolnjeni."""
    if time.time() - _last_run(_MATCHER_STAMP) < THROTTLE_SECONDS:
        return
    if _eligible_users_count() < 1:
        return
    _mark_run(_MATCHER_STAMP)
    threading.Thread(target=_run_matcher, daemon=True).start()
