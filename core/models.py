"""Modeli aplikacije core."""

from django.db import models


class DailyJobLog(models.Model):
    """Beleži kdaj je bil dnevni ML job nazadnje uspešno zagnan."""

    JOB_RECOMMENDATIONS = 'recommendations'
    JOB_MATCHING = 'matching'
    JOB_TOP_BOOKS = 'top_books'

    JOB_CHOICES = [
        (JOB_RECOMMENDATIONS, 'Priporočila knjig'),
        (JOB_MATCHING, 'Ujemanje bralcev in skupin'),
        (JOB_TOP_BOOKS, 'Top knjige'),
    ]

    job_name = models.CharField(
        max_length=50,
        choices=JOB_CHOICES,
        unique=True,
        verbose_name='Ime joba',
    )
    last_run_at = models.DateTimeField(verbose_name='Zadnji uspešen zagon')
    users_processed = models.IntegerField(
        default=0,
        verbose_name='Število obdelanih uporabnikov',
    )

    class Meta:
        verbose_name = 'Log dnevnega joba'
        verbose_name_plural = 'Logi dnevnih jobov'

    def __str__(self):
        return f'{self.get_job_name_display()} – {self.last_run_at:%d.%m.%Y %H:%M}'
