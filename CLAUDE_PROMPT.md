# BookMatch – Nadaljevalni prompt za Claude Code

Kopiraj vse spodaj in prilepi kot prvo sporočilo v novem Claude Code sessionu.

---

## KONTEKST PROJEKTA

Delaš na Django projektu **BookMatch** – slovenska socialna platforma za bralce.
Lokacija: `C:\Users\Maj\OneDrive\Dokumenti\bookmatchDjango`
Git branch: `main`, git user: `majurbajs-lab`
Python: 3.13, Django, SQLite, Windows 11
Server se zažene z: `python manage.py runserver`

---

## KAJ JE PROJEKT

BookMatch je spletna skupnost za bralce z naslednjimi funkcijami:
- **Katalog knjig** (104 knjig, 16 žanrov seeded v bazi)
- **Evidenca branja** – status (berem / prebral / chci prebrati / opuščeno), ocene, recenzije
- **Moja knjižnica** – fizične knjige doma
- **Priporočila** – ML algoritem (collaborative + content filtering)
- **Bralci zate** – matching med bralci po okusu (clustering)
- **Bralne skupine** – 16 starter skupin po žanrih
- **Izposoja** – P2P izposoja fizičnih knjig med bralci
- **Sporočila** – privatni klepeti med bralci

---

## DJANGO APLIKACIJE

```
accounts/     – registracija, login, profil (Profile model: bio, region, reliability_score, cluster_id)
books/        – Book, Genre, Author modeli; katalog z iskanjem/filtri
core/         – domača stran (hero za neprijavljene, dashboard za prijavljene)
groups/       – ReadingGroup, GroupMembership, GroupMessage
loans/        – LoanOffer, LoanRequest, LoanReview (P2P izposoja)
matching/     – UserMatch, GroupSuggestion (matching engine)
messaging/    – Conversation, Message (privatni klepeti)
ml/           – ML modeli (train_recommender, train_matcher management commands)
reading/      – ReadingEntry, Rating, Review, HomeBook, ReadingList
recommendations/ – Recommendation model
```

---

## DIZAJN SISTEM (POMEMBNO)

Dizajn je bil POPOLNOMA predelan. Vse je v `static/css/main.css` (trenutno `?v=14`).

### CSS spremenljivke
```css
--teal: #1A5C6E          /* primarna barva */
--teal-dark: #134755
--teal-light: #E8F1F3
--orange: #F28C28        /* akcent */
--orange-dark: #D97618
--text: #222222
--text-muted: #6B5B4E
--bg-app: #F5EFE8        /* topla ozadje za prijavljene */
--border: #E5DDD5
--radius-sm: 6px
--radius-md: 10px
--radius-lg: 14px
--sidebar-width: 220px   /* 200px @1024px, 72px @900px */
```

### Dve različni postavitvi (v base.html)
- **Neprijavljeni** → topbar navigacija + `<main class="main-content"><div class="container">`
- **Prijavljeni** → sidebar (220px, teal) + `<div class="app-shell"><div class="app-main">`

### base.html – KRITIČNA STRUKTURA
`{% block content %}` se pojavi **TOČNO ENKRAT** – med odprtjem in zaprtjem if/else blokov.
Struktura (poenostavljeno):
```
{% if user.is_authenticated %}
  <app-shell + sidebar odpre>
  <app-main + app-content odpre>
{% else %}
  <topbar odpre>
  <main.main-content + container odpre>
{% endif %}

{% block content %}{% endblock %}   ← SAMO ENKRAT!

{% if user.is_authenticated %}
  </app-content></app-main></app-shell>
  <nav class="mobile-nav"> (5 postavk)
{% else %}
  </container></main>
  <footer class="site-footer">
  <nav class="mobile-nav"> (3 postavke)
{% endif %}
```
**NIKOLI ne daj block content dvakrat** – Django vrže TemplateSyntaxError.

### Sidebar navigacija (za prijavljene)
9 postavk z Heroicons SVG ikoni: Domov, Katalog, Evidenca branja, Moja knjižnica, Priporočila, Bralci zate, Skupine, Izposoja, Sporočila.
Spodaj: link na profil + logout gumb.

### CSS za knjižne naslovnice po žanrih
Že implementirano: `.cover-genre-fantazija`, `.cover-genre-krimi`, `.cover-genre-distopija` itd.
Razred se generira iz `genre.slug` (slugify slovenskega imena).

### Auth strani (login / register)
Uporablja `.auth-split` – dvokolonski karton:
- Levo: `.auth-brand` (teal ozadje, logo, features lista)
- Desno: `.auth-form` (bel, obrazec)

---

## STANJE BAZE

```
Books:  104 (seeded z books/seed_books.json)
Genres: 16 (Fantazija, Krimi, Triler, Romanca, Distopija, Klasika, ...)
Groups: 16 (ena za vsak žanr, seeded s create_starter_groups)
Users:  1 (admin/testni user)
Ratings, Reviews, Loans: 0 (baza je sveža, čakamo prave uporabnike)
```

Seed komande (beži jih samo enkrat!):
```bash
python manage.py load_books
python manage.py create_starter_groups
```
(Opomba: na Windows konzoli pride UnicodeEncodeError za ✓ – to je samo encoding bug v success sporočilu, podatki so bili kljub temu shranjeni.)

---

## KAJ JE ŽE NAREJENO

1. **Popolna predelava dizajna** – topla paleta (teal + orange), Playfair Display + Inter pisavi
2. **Sidebar navigacija** – za prijavljene, z SVG ikonami pri vseh postavkah
3. **Dashboard** – stat kartice z SVG ikonami, sekcije z ikonami (Aktivne izposoje, Klepeti, Skupine, Zate)
4. **Login & Register strani** – `.auth-split` dvokolonski dizajn z branding panelom levo
5. **Domača stran (hero)** – za neprijavljene: hero, stats bar, features grid, how it works, bottom CTA
6. **Knjižne naslovnice** – barvne po žanrih (CSS razredi)
7. **Baza seeded** – 104 knjig, 16 žanrov, 16 skupin
8. **ML startup error popravljen** – ne crashá več ob zagonu (čaka na ocene za trening)

---

## KAJ ŠE MANJKA / ČAKA

### Prioriteta 1 – Funkcionalno
- [ ] **Dodajanje knjig s strani admina** – admin interface za dodajanje novih knjig (Book.is_approved=True)
- [ ] **Ocenjevanje knjig** – preveriti da rating flow deluje (reading/rate_book.html)
- [ ] **ML trening** – ko bo vsaj 5 ocen, zaženiti `python manage.py train_recommender` in `train_matcher`
- [ ] **Iskanje bralcev** – matching/readers_for_you.html – preveriti prikaz

### Prioriteta 2 – UX izboljšave
- [ ] **book_detail.html** – stran knjige: prikaz ocen, recenzij, možnost izposoje, gumb "Dodaj v evidenco"
- [ ] **Profile stran** – prikaz statistike bralca, njegove knjige, skupne knjige z drugimi bralci
- [ ] **Mobilna navigacija** – `.mobile-nav` (bottom bar) – preveriti delovanje na mobilnih napravah
- [ ] **Prazni stati** – boljši empty state prikazi ko ni podatkov (skupin, priporočil, izposoj)

### Prioriteta 3 – Manjše stvari  
- [ ] **Favicon** – preveriti ali obstaja `static/images/favicon.svg`
- [ ] **Error strani** – 404.html, 500.html custom strani
- [ ] **management command encoding** – popraviti UnicodeEncodeError (zamenjaj ✓ z [OK])

---

## KLJUČNE DATOTEKE

```
templates/base.html                    – master template (KRITIČNA ARHITEKTURA)
templates/core/home.html               – hero landing stran
templates/core/dashboard.html          – dashboard za prijavljene
templates/accounts/login.html          – auth-split login
templates/accounts/register.html       – auth-split register
templates/books/catalog.html           – katalog z iskanjem
templates/books/book_detail.html       – stran knjige
static/css/main.css                    – ves CSS (v=14)
books/management/commands/load_books.py
groups/management/commands/create_starter_groups.py
ml/apps.py                             – ML trening ob zagonu (tiho failá če ni podatkov)
bookmatch/settings.py                  – nastavitve
```

---

## NAVODILA ZA NADALJEVANJE

1. Najprej zaženi `python manage.py check` – mora biti 0 napak
2. Zaženi `python manage.py runserver` 
3. Odpri http://127.0.0.1:8000/ v brskalniku
4. Nadaljuj z zgornjim TODO listom po prioriteti
5. CSS verzijo bumpa ob vsaki večji spremembi (v=14 → v=15 itd.) da browser ne cachea

**Coding style:** Brez komentarjev razen kjer je WHY neočiten. Brez nepotrebnih abstrakcij. Direktne spremembe v obstoječe datoteke.
