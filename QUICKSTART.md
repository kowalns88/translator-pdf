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

## Krok 2: Uruchom interfejs graficzny

W terminalu (czarne okienko na dole) wpisz:

```
python aplikacja.py
```

Pojawi się komunikat z linkiem. **W Codespaces automatycznie wyskoczy powiadomienie** – kliknij "Open in Browser". Otworzy się ładna strona z przyciskami.

> Jeśli powiadomienie nie wyskoczyło: w zakładce "PORTS" (obok Terminal) kliknij ikonkę 🌐 przy porcie 5000.

---

## Krok 3: Wybierz silnik tłumaczenia

W interfejsie zobaczysz dropdown "Silnik tłumaczenia":

### Opcja A: Google Translate (domyślna)
- ✅ Darmowy, zero rejestracji
- ⚠️ Średnia jakość – zdania bywają nienaturalne

### Opcja B: Google Gemini (zalecana!)
- ✅ **Dużo lepsza jakość** – naturalne zdania, lepsze terminy naukowe
- ℹ️ Wymaga klucza API (darmowy z limitem, lub bez limitu z planem Pro)

**Jak dostać klucz API Gemini:**
1. Wejdź na: https://aistudio.google.com/apikey
2. Zaloguj się kontem Google (tym z planem Pro)
3. Kliknij "Create API Key"
4. Skopiuj klucz i wklej go w pole w aplikacji

---

## Krok 4: Kliknij "Rozpocznij tłumaczenie"

Gotowe! Program tłumaczy po 10 stron. Zobaczysz pasek postępu.

---

## Krok 5: Jeśli się zawiesi

Bez stresu! Wpisz numer strony w pole "Tłumacz od strony" i kliknij znowu.
Program pominie to, co już przetłumaczył.

---

## Krok 6: Połącz i pobierz

Gdy skończy – kliknij przycisk **"Połącz części w jeden PDF"**, a potem **"Pobierz"**.

🎉 **Gotowe!**

---

## ⏱️ Ile to trwa?

| Stron | Google Translate | Google Gemini |
|-------|-----------------|---------------|
| 10 | ~30 sekund | ~15 sekund |
| 100 | ~5 minut | ~3 minuty |
| 968 (cała książka) | ~50 minut | ~30 minut |

---

## ❓ Najczęstsze pytania

**Czy to coś kosztuje?**
→ Codespaces: darmowe 60h/miesiąc. Google Translate: darmowy. Gemini: darmowy limit 1500 zapytań/dzień (wystarczy na ~300 stron), lub bez limitu z planem Google One AI Pro.

**Mam plan Google One AI Pro – jak go użyć?**
→ Wystarczy wygenerować klucz na aistudio.google.com/apikey – będąc zalogowanym na konto z planem Pro, automatycznie masz wyższe limity.

**Mogę zamknąć przeglądarkę w trakcie?**
→ Tak! Codespace działa w tle. Wróć: https://github.com/codespaces

**Program wyrzucił błąd**
→ Kliknij "Rozpocznij" z wyższym numerem strony (od tej, na której stanął).
