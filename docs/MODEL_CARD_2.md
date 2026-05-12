# Model Card – Drugi model: K-Means gručenje bralcev

> Ta dokument opisuje drugi model strojnega učenja v aplikaciji BookMatch in dopolnjuje `MODEL_CARD.md` iz Faze 3. Ker projektni zvezek UUI predvideva dokumentacijo enega modela, lahko to uporabiš kot **dopolnilo razdelka 5** ali kot osnovo za **razširitev projekta**.

## 5.1 Namen drugega modela

Drugi model napoveduje, kateri uporabniki aplikacije imajo podoben bralni okus, in katere tematske skupine bi bile posameznemu uporabniku najbolj zanimive. Za razliko od prvega modela, ki priporoča knjige, drugi model povezuje ljudi med seboj in s skupinami, s čimer omogoča socialno komponento aplikacije.

## 5.2 Podatki

Drugi model uporablja iste podatke kot prvi, vendar drugače strukturirane. Osnova je **žanrski profil uporabnika**, ki ga izračunamo iz njegovih pozitivnih ocen (ocena 4.0 ali višja). Za vsakega uporabnika naredimo vektor dolžine 16 (število zvrsti v katalogu), kjer vsaka komponenta pove relativni delež ocen, ki jih je ta uporabnik dal knjigam iz posamezne zvrsti.

Primer: če ima uporabnik 10 pozitivnih ocen, od tega 6 knjigam iz fantazije, 3 iz krimi in 1 klasike, je njegov profil:
- Fantazija: 0.6
- Krimi: 0.3
- Klasika: 0.1
- Ostali žanri: 0.0

Kot pri prvem modelu potrebuje uporabnik vsaj 3 ocene, da se lahko vključi v analizo.

## 5.3 Priprava podatkov

Surove žanrske profile standardiziramo s StandardScalerjem iz scikit-learn, da imajo vsi atributi povprečje 0 in standardni odklon 1. Standardizacija je pri K-Means pomembna, ker algoritem meri razdalje v prostoru atributov – brez standardizacije bi žanri z več ocenami prevladali nad tistimi z manj.

## 5.4 Modeliranje

### Preizkušeni modeli

**Model 1: K-Means gručenje** – uporabniki z najpodobnejšimi profili spadajo v isto skupino. Algoritem sam najde K središč (centroid) in točke uvrsti v najbližjo gručo.

**Model 2: Hierarhično gručenje** – drevesno združuje točke po podobnosti. Prednost: ni treba vnaprej določiti števila gruč. Slabost: počasnejše pri več točkah.

**Model 3: DBSCAN** – gruča so povezana območja gostih točk, ostale so "šum". Primerno za prostorske podatke, pri naših žanrskih profilih pa slabše, ker so točke v visokorazsežnem prostoru.

### Izbrani model – utemeljitev

Izbrali smo **K-Means**. Za manjše nabore uporabnikov deluje hitro in razumljivo. Rezultati so lahko interpretljivi: vsaka gruča ima svoj centroid, ki ga lahko opišemo kot tipičnega "predstavnika bralskega tipa" (npr. "ljubitelji fantazije", "ljubitelji klasike" itd.). Hierarhično gručenje bi bilo prepočasno pri večjem številu uporabnikov, DBSCAN pa potrebuje nastavitev parametrov (epsilon), ki je za naše podatke netrivialna.

### Samodejna izbira K

Pomembna značilnost naše implementacije je, da **število gruč K ni fiksno**. Algoritem poskuša K od 2 do 8 in za vsako vrednost izračuna **silhouette score** – metriko, ki meri, kako dobro so točke uvrščene v svoje gruče v primerjavi z drugimi gručami. Izberemo tisti K, ki doseže najvišji silhouette score. Na ta način se število skupin prilagodi strukturi podatkov in se s časom lahko spreminja.

## 5.5 Vrednotenje

### Metrika: Silhouette score

Silhouette score meri kakovost gručenja. Za vsako točko primerja njeno povprečno razdaljo do točk v lastni gruči (a) s povprečno razdaljo do najbližje druge gruče (b). Formula je:

`silhouette = (b - a) / max(a, b)`

Vrednosti se gibljejo med -1 in 1, pri čemer:
- **> 0.5**: zelo dobro gručenje, jasno ločene skupine
- **0.25 – 0.5**: sprejemljivo gručenje
- **0 – 0.25**: šibko gručenje, gruče se prekrivajo
- **< 0**: napačno gručenje

### Rezultati

Rezultate vrednotenja dobiš s ukazom `python manage.py evaluate_matcher`. Izpis vsebuje silhouette score za vse preizkušene vrednosti K od 2 do 8, kot tudi izbrani najboljši K.

Pri trenutnih podatkih je silhouette score predvidoma v območju 0.3 do 0.5, kar ustreza šibkemu do sprejemljivemu gručenju. Razlog je, da imamo v bazi malo uporabnikov in žanrski profili so zaradi majhnega števila ocen občutljivi. Z rastjo števila uporabnikov in ocen bo gručenje bolj stabilno in silhouette score višji.

## 5.6 Omejitve

**Majhno število uporabnikov**: pri manj kot 4 uporabnikih algoritem ne more tvoriti gruč (vsi gredo v isto). Tudi pri 4-6 uporabnikih so rezultati občutljivi.

**Hladna gruča**: če se med uporabniki oblikuje zelo majhna gruča (npr. 1 uporabnik), zanj ni mogoče najti "bralcev s podobnim okusom". Tak uporabnik dobi predloge na osnovi kosinusne podobnosti z najbolj podobnimi profili ne glede na pripadnost gruči.

**Žanrska omejenost**: model temelji izključno na žanrih, ne na konkretnih avtorjih ali naslovih. Dva uporabnika sta lahko v isti gruči "ljubiteljev fantazije", a ima eden rad Tolkiena, drugi pa ne. Za bolj natančno ujemanje bi v prihodnje lahko dodali še profile po avtorjih.

**Nepoznavanje zgodovine**: model upošteva zgolj vsoto ocen, ne pa tega, kdaj so bile dane. Če je uporabnik pred letom dni veliko bral fantazijo, zdaj pa krimi, bo njegov profil "mešan" in gruča ne bo povsem natančna.

## 5.7 Integracija v aplikacijo

Oba modela delujeta kot samostojni moduli v mapi `ml/`. Drugi model je implementiran v razredu `ReaderMatcher` v `ml/matcher.py`. Rezultati se hranijo v tabelah `matching_usermatch` (pari bralcev) in `matching_groupsuggestion` (predlogi skupin), ter dodatno v polju `cluster_id` na uporabnikovem profilu.

Preračun se izvede z ukazom `python manage.py train_matcher`, ki izvede vse tri korake: gradnjo profilov, K-Means gručenje in zapis ujemanj ter predlogov skupin v bazo. Rezultate si uporabnik ogleda na strani **Bralci zate**.

Pri prikazu uporabnik vidi dva ločena razdelka: predlagane skupine in predlagane bralce. Za vsak predlog je naveden odstotek ujemanja (kosinusna podobnost × 100) in kratek razlog (npr. "Oba rada berete fantazijo in klasiko"). Uporabnik lahko vsak predlog zavrne, kar se shrani kot `is_dismissed=True` in se več ne prikaže.

Model spoštuje uporabnikovo nastavitev zasebnosti. Če v profilu izklopi možnost "Sodeluj v sistemu ujemanj", njegov profil ni vključen v seznam predlogov drugih uporabnikov, sam pa tudi ne dobi predlogov bralcev.
