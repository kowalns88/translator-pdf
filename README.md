# 📄 PDF Translator – English to Polish

Aplikacja do tłumaczenia dokumentów PDF z języka angielskiego na polski z **zachowaniem pełnej szaty graficznej**: układu strony, czcionek, kolorów, obrazów i formatowania.

## ✨ Funkcje

- 🔤 **Tłumaczenie tekstu** z angielskiego na polski (Google Translate, bezpłatnie)
- 🎨 **Zachowanie layoutu** – pozycje tekstu, czcionki, kolory, rozmiary
- 🖼️ **Zachowanie obrazów** – wszystkie grafiki pozostają nienaruszone
- 📐 **Zachowanie formatowania** – bold, italic, monospace, serif/sans-serif
- ⚡ **Inteligentne pomijanie** – formuły matematyczne, numery, symbole nie są tłumaczone
- 💾 **Cache tłumaczeń** – powtarzające się frazy tłumaczone tylko raz
- 📊 **Pasek postępu** – śledzenie procesu w czasie rzeczywistym
- 📖 **Zakres stron** – możliwość tłumaczenia wybranych stron

## 🚀 Instalacja

### Opcja 1: Docker (zalecana – nie wymaga Pythona!)

Potrzebujesz tylko **Docker Desktop** – reszta jest w kontenerze.

1. Zainstaluj Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/kowalns88/translator-pdf.git
   cd translator-pdf
   ```
3. Gotowe! Uruchamiaj jak poniżej.

### Opcja 2: Python (dla zaawansowanych)

Wymagania:
- Python 3.10+
- Dostęp do internetu (do tłumaczeń Google Translate)

```bash
# 1. Klonowanie repozytorium
git clone https://github.com/kowalns88/translator-pdf.git
cd translator-pdf

# 2. Utworzenie wirtualnego środowiska (zalecane)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub: venv\Scripts\activate  # Windows

# 3. Instalacja zależności
pip install -r requirements.txt
```

## 📋 Użycie

### 🐳 Z Dockerem (bez Pythona!)

**Windows** (podwójne kliknięcie lub cmd):
```cmd
run.bat The_Feynman_Lectures_on_Physics_Volume_1.pdf 1-10
```

**Linux / Mac** (terminal):
```bash
chmod +x run.sh
./run.sh The_Feynman_Lectures_on_Physics_Volume_1.pdf 1-10
```

**Bezpośrednio Docker:**
```bash
# Budowanie obrazu (tylko raz)
docker build -t pdf-translator .

# Tłumaczenie (PDF musi być w bieżącym katalogu)
docker run --rm -v "$(pwd)":/data pdf-translator --input /data/The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-10

# Windows (PowerShell):
docker run --rm -v "${PWD}:/data" pdf-translator --input /data/The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-10

# Windows (CMD):
docker run --rm -v "%cd%":/data pdf-translator --input /data/The_Feynman_Lectures_on_Physics_Volume_1.pdf --pages 1-10
```

### 🐍 Z Pythonem

```bash
# Tłumaczenie całego PDF-a
python translate_pdf.py --input The_Feynman_Lectures_on_Physics_Volume_1.pdf

# Wynik: The_Feynman_Lectures_on_Physics_Volume_1_PL.pdf
```

### Zaawansowane opcje

```bash
# Tłumaczenie wybranych stron (np. 1-10)
python translate_pdf.py --input book.pdf --pages 1-10

# Własna nazwa pliku wyjściowego
python translate_pdf.py --input book.pdf --output ksiazka_po_polsku.pdf

# Tłumaczenie na inny język (np. niemiecki)
python translate_pdf.py --input book.pdf --lang de

# Tryb cichy (bez paska postępu)
python translate_pdf.py --input book.pdf --quiet
```

### Wszystkie parametry

| Parametr | Skrót | Opis | Domyślnie |
|----------|-------|------|-----------|
| `--input` | `-i` | Ścieżka do pliku PDF (wymagany) | - |
| `--output` | `-o` | Ścieżka pliku wyjściowego | `{input}_PL.pdf` |
| `--lang` | `-l` | Język docelowy | `pl` |
| `--source` | `-s` | Język źródłowy | `en` |
| `--pages` | `-p` | Zakres stron (np. `1-10`, `5`, `1-50`) | wszystkie |
| `--verbose` | `-v` | Szczegółowe logowanie | włączone |
| `--quiet` | `-q` | Wyłącz pasek postępu | wyłączone |

## 🏗️ Architektura

```
translator-pdf/
├── translate_pdf.py        # Główny skrypt CLI
├── config.py               # Konfiguracja aplikacji
├── requirements.txt        # Zależności Python
├── src/
│   ├── __init__.py
│   ├── extractor.py        # Ekstrakcja tekstu z PDF (PyMuPDF)
│   ├── translator.py       # Warstwa tłumaczeń (deep-translator)
│   └── reconstructor.py    # Rekonstrukcja PDF z przetłumaczonym tekstem
├── fonts/                  # Folder na czcionki niestandardowe
├── output/                 # Folder na pliki wyjściowe
└── README.md
```

### Jak to działa?

1. **Ekstrakcja** (`extractor.py`)
   - Otwiera PDF za pomocą PyMuPDF
   - Dla każdej strony wyodrębnia wszystkie bloki tekstu
   - Zachowuje: pozycję (bbox), czcionkę, rozmiar, kolor, styl (bold/italic)
   - Inteligentnie pomija formuły, numery, symbole

2. **Tłumaczenie** (`translator.py`)
   - Używa Google Translate przez bibliotekę `deep-translator`
   - Tłumaczy tekst w partiach (batching) z opóźnieniami (rate limiting)
   - Cachuje tłumaczenia – identyczne frazy tłumaczone tylko raz
   - Obsługa błędów z fallbackiem na oryginalny tekst

3. **Rekonstrukcja** (`reconstructor.py`)
   - Kopiuje oryginalną stronę 1:1 (z obrazami, rysunkami, tłem)
   - Nakłada "redakcje" na oryginalny tekst (biały prostokąt)
   - Wstawia przetłumaczony tekst w dokładnie tej samej pozycji
   - Automatycznie dobiera czcionkę (serif/sans/mono, bold/italic)
   - Dostosowuje rozmiar czcionki gdy tłumaczenie jest dłuższe

## ⚙️ Konfiguracja

Plik `config.py` pozwala dostosować zachowanie aplikacji:

```python
# Język docelowy
TARGET_LANGUAGE = "pl"

# Silnik tłumaczeń
TRANSLATION_ENGINE = "google"  # Darmowy, bez klucza API

# Rozmiar partii (batch) - wpływa na szybkość
TRANSLATION_BATCH_SIZE = 50

# Opóźnienie między partiami (sekundy) - zapobiega blokowaniu
TRANSLATION_DELAY = 0.5

# Minimalna długość tekstu do tłumaczenia
MIN_TEXT_LENGTH = 2
```

## ⚠️ Ograniczenia

- **Czcionki** – Przetłumaczony tekst używa czcionek wbudowanych w PyMuPDF (Helvetica, Times, Courier). Oryginalne czcionki PDF mogą nie być dostępne.
- **Polskie znaki** – Wbudowane czcionki obsługują podstawowe znaki łacińskie. Dla pełnej obsługi polskich znaków diakrytycznych (ą, ć, ę, ł, ń, ó, ś, ź, ż) można dodać czcionkę niestandardową.
- **Długość tekstu** – Polski tekst jest zazwyczaj 15-20% dłuższy niż angielski. Aplikacja automatycznie zmniejsza rozmiar czcionki, ale w ekstremalnych przypadkach tekst może nie zmieścić się idealnie.
- **Rate limiting** – Google Translate może tymczasowo zablokować dostęp przy bardzo dużych dokumentach. Aplikacja obsługuje to przez opóźnienia między partiami.
- **Formuły matematyczne** – Proste wzory (pojedyncze symbole, numery) są pomijane automatycznie. Złożone formuły w tekście mogą być częściowo przetłumaczone.

## 🔧 Rozwiązywanie problemów

### "Translation failed" w logach
→ Prawdopodobnie tymczasowe ograniczenie Google Translate. Zwiększ `TRANSLATION_DELAY` w `config.py`.

### Brakujące polskie znaki (ą, ę, ł...)
→ Ustaw czcionkę z pełnym wsparciem polskich znaków w `config.py`:
```python
USE_CUSTOM_FONT = True
CUSTOM_FONT_PATH = "fonts/DejaVuSans.ttf"
```

### Zbyt duży plik wyjściowy
→ Aplikacja już używa kompresji. Dla dalszej redukcji rozmiaru użyj zewnętrznego narzędzia do optymalizacji PDF.

## 📝 Licencja

MIT License – używaj, modyfikuj i dystrybuuj bez ograniczeń.

## 🤝 Wkład

Pull requests mile widziane! Dla większych zmian proszę najpierw otworzyć issue.
