# Jak uruchomić tłumacz PDF

## Krok 1: Otwórz Codespaces

Wejdź na tę stronę:

https://github.com/kowalns88/translator-pdf

Zobaczysz coś takiego:

```
┌─────────────────────────────────────────────┐
│  kowalns88/translator-pdf                   │
│                                             │
│  [<> Code ▼]  ← kliknij ten zielony przycisk│
└─────────────────────────────────────────────┘
```

Po kliknięciu "Code" pojawi się menu. Kliknij zakładkę **"Codespaces"** (druga z góry), a potem:

```
┌─────────────────────────────────────┐
│  Codespaces                         │
│                                     │
│  [+ Create codespace on main]       │ ← kliknij to
└─────────────────────────────────────┘
```

**Poczekaj 2-3 minuty.** Zobaczysz ładowanie – to normalne, system instaluje wszystko za Ciebie.

---

## Krok 2: Uruchom aplikację

Gdy Codespace się załaduje, zobaczysz ekran podzielony na:
- Górna/lewa część: edytor plików (możesz zignorować)
- **Dolna część: TERMINAL** (czarne okienko z tekstem)

W tym czarnym okienku wpisz dokładnie to:

```
python aplikacja.py
```

i naciśnij **Enter**.

---

## Krok 3: Otwórz interfejs

Po chwili zobaczysz w prawym dolnym rogu powiadomienie:

```
┌───────────────────────────────────────────┐
│  Your application running on port 5000    │
│  is available.                            │
│                                           │
│  [Open in Browser]  ← KLIKNIJ TO         │
└───────────────────────────────────────────┘
```

Kliknij **"Open in Browser"**. Otworzy się nowa karta z aplikacją.

> **Jeśli powiadomienie zniknęło:** kliknij na dole ekranu zakładkę "PORTS" (obok "TERMINAL"), znajdź wiersz z portem 5000 i kliknij ikonkę globusa 🌐.

---

## Krok 4: Korzystaj z aplikacji

Teraz masz przed sobą stronę z przyciskami:

1. **Pole "Tłumacz od strony"** – zostaw 1 (albo wpisz inny numer, jeśli wznawiasz)

2. **Silnik tłumaczenia** – wybierz:
   - "Google Translate" = darmowy, słabsza jakość
   - "Google Gemini" = lepsza jakość (trzeba wkleić klucz – patrz niżej)

3. **Kliknij niebieski przycisk "Rozpocznij tłumaczenie"**

4. Zobaczysz pasek postępu – czekaj.

5. Jak skończy → kliknij **"Połącz części w jeden PDF"**

6. Kliknij **"Pobierz"** → plik zapisze się na Twoim komputerze

---

## Skąd wziąć klucz API Gemini (opcjonalnie)

Jeśli chcesz lepszą jakość tłumaczenia:

1. Otwórz: https://aistudio.google.com/apikey
2. Zaloguj się kontem Google
3. Kliknij "Create API Key"
4. Skopiuj klucz (wygląda jak: AIzaSyB1abc...)
5. Wklej go w pole "Klucz API Gemini" w aplikacji

---

## Co jeśli program się zawiesi?

1. Wróć do zakładki Codespaces
2. W terminalu wpisz: `python aplikacja.py`
3. Otwórz znowu interfejs (krok 3)
4. W pole "Tłumacz od strony" wpisz numer strony, na której stanęło
5. Kliknij "Rozpocznij" – program pominie to, co już przetłumaczył

---

## Co jeśli zamknę przeglądarkę?

Nic złego! Codespace dalej działa. Wróć na:
https://github.com/codespaces

Zobaczysz swoją otwartą sesję – kliknij na nią.

---

## Ile to kosztuje?

- **GitHub Codespaces:** 60 darmowych godzin miesięcznie (wystarczy)
- **Google Translate:** za darmo
- **Google Gemini:** darmowy limit ~300 stron/dzień, bez limitu z planem Google One AI Pro
