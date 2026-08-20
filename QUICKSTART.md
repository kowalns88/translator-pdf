# 🚀 Instrukcja – tłumaczenie PDF (dla nie-programistów)

## Czego potrzebujesz?
- Konto na GitHub (darmowe) – https://github.com/signup
- Przeglądarkę internetową
- **Nic nie instalujesz na komputerze!**

---

## Krok 1: Otwórz środowisko w przeglądarce

Kliknij ten link:

👉 **https://codespaces.new/kowalns88/translator-pdf?quickstart=1**

(Albo: wejdź na https://github.com/kowalns88/translator-pdf → zielony przycisk "Code" → zakładka "Codespaces" → "Create codespace on main")

Poczekaj ~2 minuty – otworzy się edytor kodu w przeglądarce. Wszystko gotowe!

---

## Krok 2: Otwórz terminal

Na dole ekranu zobaczysz **Terminal** (czarne okienko z tekstem).

Jeśli go nie widzisz: w menu na górze kliknij **Terminal → New Terminal**

---

## Krok 3: Uruchom tłumaczenie

Wpisz w terminalu:

```
python tlumacz.py
```

Program zacznie tłumaczyć po 10 stron. Zobaczysz coś takiego:

```
============================================================
  📖 TŁUMACZENIE: The_Feynman_Lectures_on_Physics_Volume_1.pdf
  📄 Stron w dokumencie: 968
  📦 Rozmiar partii: 10 stron
  ▶️  Start od strony: 1
  📁 Części zapisywane w: czesci/
============================================================

  🔄 Partia 1: strony 1-10...
  Strony 1-10 |██████████| 10/10 [00:27]
  ✅ Zapisano: czesci/czesc_001_strony_1-10.pdf (27 sek)

  🔄 Partia 2: strony 11-20...
```

**Każda partia (10 stron) zajmuje ok. 30 sekund.**

---

## Krok 4: Jeśli program się zawiesi

Spokojnie! Wszystkie przetłumaczone części są już zapisane.

Wpisz w terminalu (zamień 41 na numer strony od której chcesz kontynuować):

```
python tlumacz.py --od 41
```

Program pominie części, które już przetłumaczył i zacznie od podanej strony.

> 💡 **Wskazówka:** Jeśli program stanął na stronie 35, wpisz `--od 31` (początek tej partii). Program sam zobaczy, że część 1-10 i 11-20 i 21-30 już istnieją i je pominie.

---

## Krok 5: Połącz wszystkie części w jeden PDF

Gdy wszystkie części będą przetłumaczone, wpisz:

```
python tlumacz.py --polacz
```

Powstanie jeden plik: **Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf**

---

## Krok 6: Pobierz gotowy plik

1. W panelu po lewej stronie (Explorer) znajdź plik `Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf`
2. Kliknij na niego **prawym przyciskiem myszy**
3. Wybierz **Download**

🎉 **Gotowe!**

---

## ⏱️ Ile to trwa?

| Stron | Czas | Polecenie |
|-------|------|-----------|
| 10 | ~30 sekund | `python tlumacz.py --od 1` (zatrzymaj Ctrl+C po 1 partii) |
| 100 | ~5 minut | |
| 500 | ~25 minut | |
| 968 (cała książka) | ~50 minut | `python tlumacz.py` |

---

## ❓ Najczęstsze pytania

**Czy to coś kosztuje?**
→ Nie. GitHub Codespaces daje 60 godzin miesięcznie za darmo.

**Mogę zamknąć przeglądarkę w trakcie?**
→ Tak! Codespace działa w tle. Wróć do niego: https://github.com/codespaces

**Program wyrzucił błąd o "rate limit"**
→ Google Translate czasem blokuje zbyt częste zapytania. Poczekaj 5 minut i uruchom: `python tlumacz.py --od [strona]`

**Chcę przetłumaczyć inny PDF**
→ Przeciągnij swój plik do panelu po lewej (Explorer). Potem otwórz plik `tlumacz.py` i zmień linijkę:
```
PLIK_WEJSCIOWY = "nazwa_twojego_pliku.pdf"
```

**Jak zatrzymać tłumaczenie?**
→ Naciśnij `Ctrl + C` w terminalu. Dotychczasowe części pozostaną zapisane.
