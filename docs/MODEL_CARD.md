# Model Card – Priporočilni model BookMatch

> Ta dokument služi kot pomoč pri izpolnjevanju **razdelka 5 projektnega zvezka UUI** (Podatki in strojno učenje). Vsebina je prilagojena za projekt BookMatch, številke pa boš moral nadomestiti s svojimi, ko boš pognal `python manage.py evaluate_recommender`.

---

## 5.1 Namen modela

**Kaj model napoveduje / razvršča in zakaj?**

Model napoveduje, katere knjige bi bile uporabniku najbolj všeč, glede na knjige, ki jih je že ocenil. To je **content-based priporočilni sistem** (vsebinsko filtriranje).

Vhod: uporabnikove ocene knjig in metapodatki knjig (žanri, avtorji, opis).
Izhod: razvrščen seznam knjig z oceno relevantnosti (kosinusna podobnost med 0 in 1).

Namen je uporabnikom olajšati odkrivanje novih knjig in rešiti problem "informacijske preobremenjenosti" – v katalogu je veliko knjig in uporabnik težko ve, katero naj izbere naslednjo.

## 5.2 Podatki

**Vir podatkov:**
Lastna MySQL baza aplikacije BookMatch (tabele `books_book`, `books_author`, `books_genre`, `reading_rating`).

**Način zbiranja:**
- **Knjige:** začetni nabor 105 knjig ročno pripravljen v `seed_books.json` in uvožen z ukazom `load_books`.
- **Ocene:** zbiramo jih znotraj aplikacije – vsak uporabnik po branju oceni knjigo (1.0–5.0).

**Število primerov:**
Zamenjaj s svojimi številkami:
- Število knjig v katalogu: **105**
- Število ocen: **_ (poženi `python manage.py evaluate_recommender` in prenesi številko)_**
- Število uporabnikov z vsaj 1 oceno: **_** 
- Povprečno število ocen na uporabnika: **_**

**Opis atributov:**

| Atribut knjige | Tip | Uporaba v modelu |
|---|---|---|
| `title` | besedilo | ni v modelu (samo za prikaz) |
| `authors` | M2M | v TF-IDF besedilu (utež 2x) |
| `genres` | M2M | v TF-IDF besedilu (utež 3x, najpomembnejše) |
| `description` | besedilo | v TF-IDF besedilu (utež 1x) |
| `publisher` | besedilo | v TF-IDF besedilu (utež 1x) |
| `publication_year` | celo število | ni v modelu |

| Atribut ocene | Tip | Uporaba v modelu |
|---|---|---|
| `user_id` | ključ | identifikacija |
| `book_id` | ključ | povezava z vektorjem knjige |
| `score` | 1.0–5.0 | utež v uporabnikovem profilu |

**Ciljna spremenljivka:**
Ocena relevantnosti (kosinusna podobnost) med uporabnikovim profilom in vsako knjigo v katalogu, ki je še ni ocenil.

**Etika in zakonitost:**
- Uporabljamo **samo podatke iz lastne aplikacije**, ki jih uporabniki sami vnesejo.
- Ne uporabljamo občutljivih osebnih podatkov (spol, narodnost ipd.).
- Uporabnik ve, da so priporočila algoritmsko generirana (jasno označeno v vmesniku z "Za vas" in razlogom predloga).
- Uporabnik lahko vsako priporočilo zavrne ("Ne zanima me") – ta podatek se shrani in predlog se ne prikaže več.
- Podatki so shranjeni v lastni bazi in niso posredovani tretjim osebam.

## 5.3 Priprava podatkov

**Opis čiščenja in obdelave:**

1. **Gradnja besedila knjige:** za vsako knjigo iz baze sestavimo eno besedilo iz žanrov (ponovimo 3x), avtorjev (2x), opisa in založbe (1x). Ponavljanje služi kot utež – pomembnejše lastnosti se štejejo večkrat.

2. **Predprocesiranje besedil:**
   - Pretvorba v male črke.
   - Odstranitev slovenskih stop-words (seznam ~70 najpogostejših slovenskih besed, definiran v `recommender.py`).
   - Tokenizacija na posamezne besede in dvojice besed (n-grami 1–2).

3. **TF-IDF vektorizacija** (`sklearn.feature_extraction.text.TfidfVectorizer`):
   - Omejitev besedišča: največ 2000 najpogostejših značilk.
   - Minimalna dokumentna frekvenca: 1 (beseda mora biti vsaj v 1 knjigi).
   - Maksimalna dokumentna frekvenca: 0.85 (ignoriramo besede, ki so v več kot 85 % knjig).

4. **Uporabnikov profil:**
   - Za vsako uporabnikovo oceno izračunamo utež: `utež = ocena - 3.0` (tako 5 → +2, 4 → +1, 2 → -1, 1 → -2; nevtralna ocena 3 → 0).
   - Profil je tehtana vsota TF-IDF vektorjev ocenjenih knjig.
   - Na koncu profil L2-normaliziramo (za izračun kosinusne podobnosti).

5. **Filtriranje:** iz priporočil izključimo knjige, ki jih je uporabnik že ocenil ali označil kot prebrane/opuščene.

## 5.4 Modeliranje

**Preizkušeni modeli:**

1. **Content-based s TF-IDF in kosinusno podobnostjo** – izbrani model.
2. **(Opcijsko za razširitev):** kolaborativno filtriranje z matrično faktorizacijo – ne uporabljeno, ker potrebuje veliko uporabnikov in ocen.

**Izbrani model – utemeljitev:**

Content-based pristop smo izbrali iz naslednjih razlogov:
- **Deluje z malo podatkov** – tudi če ima uporabnik samo 3 ocene, lahko že izračunamo njegov profil. Kolaborativno filtriranje bi potrebovalo veliko več uporabnikov in prekrivajočih se ocen.
- **Ne potrebuje ocen drugih uporabnikov** – nov uporabnik dobi priporočila takoj po prvih nekaj ocenah.
- **Razložljivost** – lahko jasno pokažemo, zakaj je bila knjiga predlagana (npr. "ker ti je bila všeč knjiga X").
- **Transparentnost** – celoten postopek je deterministen in pregleden.

Glavna omejitev je, da se pristop zapre v "mehurček" (priporoča samo podobne vsebine). To omilimo z **raznolikostjo** – omejimo število predlogov istega avtorja na 2.

## 5.5 Vrednotenje

**Metrike:**

- **precision@K** – delež knjig v top-K priporočilih, ki so uporabniku dejansko všeč.
- **recall@K** – delež vseh uporabnikovih všečnih knjig, ki jih model najde v top-K.

Pri nas K = 10.

**Način validacije – train/test split:**

Za vsakega uporabnika z dovolj pozitivnimi ocenami (≥ 4):
1. Vzamemo vse njegove pozitivne ocene (score ≥ 4.0).
2. **Naključno 30 % skrijemo** (test set).
3. Model zgradi profil samo iz preostalih 70 % ocen.
4. Preverimo, koliko knjig iz test seta model predlaga v top-10.

Primer: če ima uporabnik 10 pozitivnih ocen, jih 3 skrijemo. Model zna 7 ocen. Če je v njegovem top-10 2 od teh 3 skritih, je:
- precision@10 = 2/10 = 0.2
- recall@10 = 2/3 = 0.67

**Rezultati:**

Zamenjaj s svojimi številkami po zagonu `python manage.py evaluate_recommender`:

| Metrika | Vrednost |
|---|---|
| Število vrednotenih uporabnikov | **_** |
| Povprečni precision@10 | **_** |
| Povprečni recall@10 | **_** |
| Skupno zadetkov | **_** |

**Interpretacija:**
- precision@10 = 0.2 pomeni, da je v povprečju 2 od 10 predlaganih knjig res všečnih uporabniku.
- Zaradi majhnega števila ocen v zgodnji fazi je natančnost nižja. Pričakujemo izboljšanje ob večanju baze.

## 5.6 Omejitve modela

1. **Cold start problem:** novi uporabniki brez ocen ne morejo prejeti smiselnih priporočil. V aplikaciji zato uporabnika, ki ima manj kot 3 ocene, preusmerimo v katalog z opozorilom.

2. **Filter bubble (mehurček):** content-based model priporoča predvsem vsebinsko podobne knjige, kar lahko vodi v premajhno raznolikost priporočil. Omilili smo s pravilom "največ 2 knjigi istega avtorja" v top-N.

3. **Odvisnost od kakovosti opisov:** če knjiga nima dobrega opisa ali žanrov, je njena uvrstitev v TF-IDF prostor slabša.

4. **Ne upošteva dinamike bralnega okusa:** model obravnava vse ocene enakovredno. Če se okus uporabnika sčasoma spremeni, model tega ne zazna (novejše ocene nimajo večje uteži).

5. **Potreba po periodičnem preračunu:** ko se dodajo nove knjige ali ocene, je treba model ponovno natrenirati z ukazom `python manage.py train_recommender`. V produkciji bi to reševali s Celery opravili.

6. **Jezik:** seznam stop-words je ročno pripravljen za slovenščino. Za druge jezike bi bil potreben drug seznam ali uporaba jezikovno nevtralnega pristopa.

## 5.7 Integracija v aplikacijo

**Kako je model povezan s spletno aplikacijo?**

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Uporabnik oceni knjigo                                        │
│         ↓                                                      │
│  Ocena se shrani v bazo (reading.Rating)                       │
│         ↓                                                      │
│  [Administrator / planirano opravilo]                          │
│  Zagon: python manage.py train_recommender                     │
│         ↓                                                      │
│  ml/recommender.py:                                            │
│    1. Preberi vse knjige → TF-IDF matrika                      │
│    2. Za vsakega uporabnika zgradi profil iz ocen              │
│    3. Izračunaj kosinusno podobnost profila in vseh knjig      │
│    4. Shrani top-20 v recommendations.Recommendation           │
│         ↓                                                      │
│  Uporabnik odpre stran /recommendations/for-you/               │
│         ↓                                                      │
│  Priporočila se preberejo iz baze (hiter prikaz)               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Model je implementiran v modulu `ml/` znotraj Django projekta. Glavna datoteka je `ml/recommender.py` z razredom `ContentBasedRecommender`. Rezultati se shranjujejo v bazo (tabela `recommendations_recommendation`), da je prikaz v vmesniku takojšen in ne zahteva ponovnega izračuna.

Trenutno se model osveži ročno (`python manage.py train_recommender`). V produkciji bi to avtomatizirali z orodjem Celery in ga sprožili:
- vsak večer (batch osvežitev),
- ali takoj, ko uporabnik doda vsaj 3 nove ocene.

---

## Uporabne ukazne vrstice

```bash
# Naučimo model in izračunamo priporočila za vse uporabnike
python manage.py train_recommender

# Samo za enega uporabnika (preverjanje)
python manage.py train_recommender --user-id 1

# Vrednotenje (precision@K, recall@K)
python manage.py evaluate_recommender --k 10

# Shranjevanje naučenega modela v datoteko (za hitrejše nalaganje)
python manage.py train_recommender --save
```
