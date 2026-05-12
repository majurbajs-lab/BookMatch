# BookMatch – Faza 1

Spletna aplikacija, ki povezuje bralce. Projekt za predmet UUI – Uvod v umetno inteligenco.

Ta paket vsebuje **Fazo 1**: postavitev Django projekta, povezava z MySQL bazo, osnovno predlogo ter sistem registracije, prijave in profilov.

## Vsebina Faze 1

- ✅ Django projekt povezan z MySQL bazo `bookmatchDjango`
- ✅ Osnovna predloga z navigacijo (bela + #1A5C6E + #F28C28, pisava Inter)
- ✅ Registracija novih uporabnikov
- ✅ Prijava in odjava
- ✅ Javni profil uporabnika (pogled in urejanje)
- ✅ Samodejno ustvarjanje profila ob registraciji
- ✅ Admin plošča za upravljanje

## Predpogoji

- Python 3.12 ✅ (imaš nameščen)
- MySQL strežnik ✅ (imaš nameščenega)
- Windows ✅

## 1. Prenos in priprava projekta

Odpri **PowerShell** ali **Command Prompt** in pojdi v mapo, kjer želiš imeti projekt:

```powershell
cd C:\Users\TvojeUporabnisko\Documents
```

Razpakiraj `bookmatch.zip`, tako da dobiš mapo `bookmatch`. Pojdi vanjo:

```powershell
cd bookmatch
```

## 2. Ustvari bazo v MySQL

Odpri **MySQL Command Line Client** ali **MySQL Workbench** in zaženi:

```sql
CREATE DATABASE bookmatchDjango CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> Če uporabiš drugo uporabniško ime kot `root`, pazi, da ima ta uporabnik pravice nad to bazo.

## 3. Nastavi .env datoteko

V korenu projekta je datoteka `.env`. Odpri jo z urejevalnikom (npr. Notepad) in popravi geslo:

```
SECRET_KEY=django-insecure-spremeni-me-v-produkciji-2026-bookmatch
DEBUG=True
DB_NAME=bookmatchDjango
DB_USER=root
DB_PASSWORD=tvoje_mysql_geslo    ← SEM VPIŠI SVOJE GESLO
DB_HOST=localhost
DB_PORT=3306
```

## 4. Ustvari virtualno okolje in namesti knjižnice

V korenu projekta (mapa `bookmatch`, kjer je `manage.py`) v PowerShellu zaženi:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> Če `pip install` javi napako pri `mysqlclient`, namesto tega uporabi:
> ```powershell
> pip install PyMySQL
> ```
> In dodaj na vrh `bookmatch/__init__.py`:
> ```python
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

## 5. Ustvari tabele v bazi (migracije)

```powershell
python manage.py makemigrations
python manage.py migrate
```

Če je vse v redu, boš videl izpis o ustvarjenih tabelah.

## 6. Ustvari superuporabnika za admin ploščo

```powershell
python manage.py createsuperuser
```

Izberi uporabniško ime, e-naslov in geslo (ne se ustraši opozoril – za razvoj lahko izbereš kratko geslo).

## 7. Zaženi strežnik

```powershell
python manage.py runserver
```

Odpri brskalnik in pojdi na:

- **Aplikacija:** http://127.0.0.1:8000/
- **Admin plošča:** http://127.0.0.1:8000/admin/

## Kaj lahko testiraš

1. Na http://127.0.0.1:8000/ vidiš predstavitveno stran (brez prijave).
2. Klikni **Ustvari račun** in se registriraj.
3. Po registraciji te preusmeri na urejanje profila – dodaj biografijo, mesto, profilno sliko.
4. Klikni **Moj profil** v navigaciji in preveri, kako izgleda.
5. Odjavi se in se poskusi znova prijaviti.
6. V admin plošči (`/admin/`) lahko pregleduješ uporabnike in profile.

## Struktura projekta

```
bookmatch/
├── bookmatch/              # glavna nastavitvena mapa
│   ├── settings.py         # nastavitve
│   ├── urls.py             # glavne URL poti
│   ├── wsgi.py / asgi.py
├── accounts/               # registracija, prijava, profili
│   ├── models.py           # Profile model
│   ├── views.py            # pogledi
│   ├── forms.py            # obrazci
│   ├── urls.py             # poti
│   ├── signals.py          # samodejno ustvarjanje profila
│   └── admin.py
├── core/                   # domača stran, skupne komponente
│   ├── views.py
│   └── urls.py
├── static/
│   └── css/
│       └── main.css        # glavna slogovna datoteka
├── templates/
│   ├── base.html           # osnovna predloga
│   ├── accounts/           # predloge za registracijo, prijavo, profil
│   └── core/               # predloge za domačo stran in O nas
├── media/                  # uporabniško naložene datoteke (ustvari se samodejno)
├── .env                    # okoljske spremenljivke (geslo!)
├── manage.py
├── requirements.txt
└── README.md
```

## Pogoste težave

### "Access denied for user 'root'@'localhost'"
Preveri geslo v `.env` datoteki.

### "Unknown database 'bookmatchDjango'"
Bazo je treba najprej ustvariti (glej 2. korak).

### "No module named 'MySQLdb'"
Uporabi PyMySQL workaround (glej 4. korak).

### Strani se prikazujejo brez CSS
Prepričaj se, da je v `.env` nastavljeno `DEBUG=True`.

## Kaj pride naprej?

Ko Faza 1 deluje pri tebi, nadaljujemo s **Fazo 2**: katalog knjig, bralna evidenca, ocenjevanje. Takrat boš dobil naslednji paket datotek, ki jih dodaš v obstoječi projekt.

---

**Če kaj ne deluje, pošlji mi celotno sporočilo o napaki in ti pomagam.**
