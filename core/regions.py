"""Konstante za slovenske statistične regije.

Uporablja se v accounts (registracija) in groups (ustvarjanje skupine z regijo).
"""

# 12 uradnih statističnih regij Slovenije (SURS)
REGION_CHOICES = [
    ('', '— Izberi regijo —'),
    ('osrednjeslovenska', 'Osrednjeslovenska'),
    ('gorenjska', 'Gorenjska'),
    ('savinjska', 'Savinjska'),
    ('podravska', 'Podravska'),
    ('pomurska', 'Pomurska'),
    ('koroska', 'Koroška'),
    ('zasavska', 'Zasavska'),
    ('posavska', 'Posavska'),
    ('jv_slovenija', 'Jugovzhodna Slovenija'),
    ('goriska', 'Goriška'),
    ('obalno_kraska', 'Obalno-kraška'),
    ('primorsko_notranjska', 'Primorsko-notranjska'),
    ('drugo', 'Drugo / tujina'),
]

# Poseben ključ, ki pomeni "skupina ni vezana na regijo"
REGION_ALL = 'all'

# Za ustvarjanje skupin - vse regije + možnost "vse regije"
REGION_CHOICES_FOR_GROUP = [
    (REGION_ALL, 'Vse regije (skupina za celotno Slovenijo)'),
] + [r for r in REGION_CHOICES if r[0] != '']


def region_label(code: str) -> str:
    """Vrne človeško berljivo ime regije iz kode."""
    if code == REGION_ALL:
        return 'Vse regije'
    for c, label in REGION_CHOICES:
        if c == code:
            return label
    return code or '—'
