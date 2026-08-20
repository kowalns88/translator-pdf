# 🚀 Szybki start – GitHub Codespaces (bez instalacji!)

## Krok 1: Otwórz w Codespaces

Kliknij przycisk poniżej lub wejdź na stronę repozytorium i kliknij **Code → Codespaces → Create codespace on main**:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/kowalns88/translator-pdf?quickstart=1)

> ⏱️ Pierwsze uruchomienie trwa ~2 minuty (instalacja zależności). Kolejne otwierania są natychmiastowe.

## Krok 2: Uruchom tłumaczenie

Gdy Codespace się otworzy (zobaczysz VS Code w przeglądarce), otwórz **Terminal** (Ctrl+` lub menu Terminal → New Terminal) i wpisz:

```bash
# Tłumaczenie pierwszych 10 stron (test ~30 sekund)
python translate_pdf.py --input The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-10

# Tłumaczenie stron 1-50 (~10 minut)
python translate_pdf.py --input The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-50

# Tłumaczenie całej książki (968 stron, ~8 godzin)
python translate_pdf.py --input The_Feynman_Lectures_on_Physics_Volume_1.pdf
```

## Krok 3: Pobierz wynik

Po zakończeniu tłumaczenia:
1. W panelu **Explorer** (po lewej) znajdź plik `The_Feynman_Lectures_on_Physics_Volume_1_PL.pdf`
2. Kliknij prawym przyciskiem → **Download**

Gotowe! 🎉

---

## 💡 Wskazówki

| Polecenie | Co robi | Czas |
|-----------|---------|------|
| `--pages 1-10` | Tłumaczy strony 1-10 (test) | ~30 sek |
| `--pages 1-50` | Tłumaczy strony 1-50 | ~10 min |
| `--pages 1-100` | Tłumaczy strony 1-100 | ~20 min |
| (bez --pages) | Cała książka (968 stron) | ~8 godz |

### Tłumaczenie w tle (dla długich zadań):
```bash
# Uruchom w tle – możesz zamknąć przeglądarkę, a tłumaczenie będzie działać
nohup python translate_pdf.py --input The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-100 > progress.log 2>&1 &

# Sprawdź postęp:
tail -f progress.log
```

### Własny plik PDF:
1. Przeciągnij swój PDF do panelu Explorer w Codespaces
2. Uruchom:
```bash
python translate_pdf.py --input twoj_plik.pdf
```

---

## ❓ FAQ

**P: Ile kosztuje Codespaces?**
O: GitHub daje **60 godzin/miesiąc za darmo** na darmowym koncie. Tłumaczenie 100 stron zajmie ~20 minut.

**P: Czy mogę zamknąć przeglądarkę w trakcie tłumaczenia?**
O: Tak! Codespace działa dalej. Wróć do niego przez github.com/codespaces.

**P: Dostałem błąd o rate limiting**
O: Google Translate może tymczasowo ograniczyć dostęp. Poczekaj 5 minut i uruchom ponownie z `--pages` od strony, na której się zatrzymało.
