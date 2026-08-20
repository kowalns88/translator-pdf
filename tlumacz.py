#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           TŁUMACZ PDF – angielski → polski                   ║
║                                                              ║
║  Tłumaczy PDF partiami po 10 stron.                          ║
║  Każda partia zapisywana osobno w folderze "czesci/".        ║
║  Jak się zawiesi – uruchom ponownie od strony, na której     ║
║  stanęło. Na koniec połącz wszystkie części w jeden plik.     ║
╚══════════════════════════════════════════════════════════════╝

UŻYCIE (w terminalu):

  1) Interfejs graficzny (najprostszy sposób):
     python aplikacja.py
     → otworzy się strona w przeglądarce z przyciskami

  2) Tłumacz całość (od początku):
     python tlumacz.py

  3) Tłumacz od konkretnej strony (np. program stanął na stronie 40):
     python tlumacz.py --od 41

  4) Połącz wszystkie przetłumaczone części w jeden PDF:
     python tlumacz.py --polacz

  5) Użyj Google Gemini (lepsza jakość):
     python tlumacz.py --gemini TWOJ_KLUCZ_API
"""

import sys
import os
import time
import logging
import glob

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import fitz
except ImportError:
    import pymupdf as fitz

from tqdm import tqdm
from src.extractor import extract_page_elements, extract_translatable_texts
from src.translator import PDFTranslator
from src.reconstructor import reconstruct_page

# === KONFIGURACJA (możesz zmienić) ===
PLIK_WEJSCIOWY = "The_Feynman_Lectures_on_Physics_Volume_1.pdf"
FOLDER_CZESCI = "czesci"
PLIK_KONCOWY = "Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf"
ROZMIAR_PARTII = 10  # ile stron na raz
# =====================================


def tlumacz(od_strony: int = 1, silnik: str = "google", gemini_key: str = ""):
    """
    Tłumaczy PDF partiami po 10 stron.
    Każda partia zapisywana jako osobny plik w folderze 'czesci/'.
    """
    # Sprawdź czy plik istnieje
    if not os.path.exists(PLIK_WEJSCIOWY):
        print(f"\n❌ Nie znaleziono pliku: {PLIK_WEJSCIOWY}")
        print(f"   Upewnij się, że plik PDF jest w tym samym folderze.\n")
        sys.exit(1)

    # Utwórz folder na części
    os.makedirs(FOLDER_CZESCI, exist_ok=True)

    # Otwórz dokument
    doc = fitz.open(PLIK_WEJSCIOWY)
    total_pages = len(doc)

    silnik_nazwa = "Google Gemini (wysoka jakość)" if silnik == "gemini" else "Google Translate (darmowy)"

    print(f"\n{'='*60}")
    print(f"  📖 TŁUMACZENIE: {PLIK_WEJSCIOWY}")
    print(f"  📄 Stron w dokumencie: {total_pages}")
    print(f"  📦 Rozmiar partii: {ROZMIAR_PARTII} stron")
    print(f"  ▶️  Start od strony: {od_strony}")
    print(f"  🔤 Silnik: {silnik_nazwa}")
    print(f"  📁 Części zapisywane w: {FOLDER_CZESCI}/")
    print(f"{'='*60}\n")

    # Inicjalizacja tłumacza
    translator = PDFTranslator(
        source_lang="en",
        target_lang="pl",
        engine=silnik,
        gemini_api_key=gemini_key if silnik == "gemini" else None,
    )

    # Oblicz partie
    start_idx = od_strony - 1  # Konwersja na indeks (od 0)
    partia_nr = (start_idx // ROZMIAR_PARTII) + 1

    for batch_start in range(start_idx, total_pages, ROZMIAR_PARTII):
        batch_end = min(batch_start + ROZMIAR_PARTII, total_pages)
        nazwa_pliku = os.path.join(
            FOLDER_CZESCI,
            f"czesc_{partia_nr:03d}_strony_{batch_start+1}-{batch_end}.pdf"
        )

        # Sprawdź czy ta część już istnieje (pomiń)
        if os.path.exists(nazwa_pliku):
            print(f"  ⏭️  Partia {partia_nr} (strony {batch_start+1}-{batch_end}) – już przetłumaczona, pomijam")
            partia_nr += 1
            continue

        print(f"\n  🔄 Partia {partia_nr}: strony {batch_start+1}-{batch_end}...")

        # Tłumacz partię
        output_doc = fitz.open()
        batch_start_time = time.time()

        with tqdm(
            total=batch_end - batch_start,
            desc=f"  Strony {batch_start+1}-{batch_end}",
            unit="str",
            bar_format="  {l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        ) as pbar:
            for page_num in range(batch_start, batch_end):
                page = doc[page_num]

                # Ekstrakcja tekstu
                elements = extract_page_elements(page)
                translatable_spans = extract_translatable_texts(elements)

                if translatable_spans:
                    # Tłumaczenie
                    translated_spans = translator.translate_spans(translatable_spans)
                    # Rekonstrukcja strony
                    reconstruct_page(doc, page_num, translated_spans, output_doc)
                else:
                    # Strona bez tekstu – kopiuj jak jest
                    new_page = output_doc.new_page(
                        -1, width=page.rect.width, height=page.rect.height
                    )
                    new_page.show_pdf_page(new_page.rect, doc, page_num)

                pbar.update(1)

        # Zapisz partię
        output_doc.save(nazwa_pliku, garbage=4, deflate=True, clean=True)
        output_doc.close()

        elapsed = time.time() - batch_start_time
        print(f"  ✅ Zapisano: {nazwa_pliku} ({elapsed:.0f} sek)")
        partia_nr += 1

    doc.close()

    print(f"\n{'='*60}")
    print(f"  🎉 TŁUMACZENIE ZAKOŃCZONE!")
    print(f"  📁 Części w folderze: {FOLDER_CZESCI}/")
    print(f"  ")
    print(f"  Aby połączyć w jeden plik, uruchom:")
    print(f"  python tlumacz.py --polacz")
    print(f"{'='*60}\n")


def polacz_czesci():
    """
    Łączy wszystkie przetłumaczone części w jeden PDF.
    """
    # Znajdź wszystkie części, posortowane
    wzorzec = os.path.join(FOLDER_CZESCI, "czesc_*.pdf")
    pliki = sorted(glob.glob(wzorzec))

    if not pliki:
        print(f"\n❌ Nie znaleziono żadnych części w folderze '{FOLDER_CZESCI}/'")
        print(f"   Najpierw uruchom tłumaczenie: python tlumacz.py\n")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  🔗 ŁĄCZENIE CZĘŚCI W JEDEN PLIK")
    print(f"  📁 Znaleziono części: {len(pliki)}")
    print(f"  📄 Plik wynikowy: {PLIK_KONCOWY}")
    print(f"{'='*60}\n")

    # Łącz PDFy
    wynik = fitz.open()

    for plik in tqdm(pliki, desc="  Łączenie", unit="część",
                     bar_format="  {l_bar}{bar}| {n_fmt}/{total_fmt}"):
        czesc = fitz.open(plik)
        wynik.insert_pdf(czesc)
        czesc.close()

    # Zapisz
    wynik.save(PLIK_KONCOWY, garbage=4, deflate=True, clean=True)
    wynik.close()

    print(f"\n  ✅ GOTOWE! Plik zapisany jako: {PLIK_KONCOWY}")
    print(f"  📊 Łączna liczba stron: {fitz.open(PLIK_KONCOWY).page_count}")
    print(f"\n  Teraz kliknij prawym przyciskiem na plik → Download")
    print(f"{'='*60}\n")


def pokaz_pomoc():
    """Wyświetla instrukcję użycia."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           TŁUMACZ PDF – angielski → polski                   ║
╚══════════════════════════════════════════════════════════════╝

POLECENIA:

  python aplikacja.py            Otwórz interfejs graficzny (NAJŁATWIEJ)

  python tlumacz.py              Tłumacz od początku (Google Translate)
  python tlumacz.py --gemini KLUCZ   Tłumacz z Gemini (lepsza jakość)
  python tlumacz.py --od 41      Tłumacz od strony 41
  python tlumacz.py --polacz     Połącz części w jeden PDF
  python tlumacz.py --pomoc      Pokaż tę pomoc

SILNIKI TŁUMACZENIA:

  Google Translate (domyślny) – darmowy, nie wymaga rejestracji
  Google Gemini (--gemini)   – DUŻO lepsza jakość, wymaga klucza API
                               Klucz: https://aistudio.google.com/apikey

JAK TO DZIAŁA:

  1. Program tłumaczy po 10 stron na raz
  2. Każda partia zapisywana w folderze 'czesci/'
  3. Jeśli program się zawiesi → uruchom ponownie z --od [strona]
  4. Na koniec → --polacz łączy wszystko w jeden PDF

PRZYKŁAD:

  $ python tlumacz.py --gemini AIzaSyB...   ← start z Gemini
  ... (program tłumaczy strony 1-10, 11-20, 21-30...)
  ... (program stanął na stronie 35)
  $ python tlumacz.py --gemini AIzaSyB... --od 31  ← wznowienie
  ... (dalej: 31-40, 41-50, ...)
  $ python tlumacz.py --polacz                     ← łączy w jeden plik
""")


# === GŁÓWNA LOGIKA ===

if __name__ == "__main__":
    # Konfiguracja logowania (ukryj szczegóły techniczne)
    logging.basicConfig(level=logging.WARNING)

    args = sys.argv[1:]

    if "--pomoc" in args or "--help" in args or "-h" in args:
        pokaz_pomoc()

    elif "--polacz" in args:
        polacz_czesci()

    else:
        # Parametry
        od_strony = 1
        silnik = "google"
        gemini_key = ""

        if "--od" in args:
            try:
                idx = args.index("--od")
                od_strony = int(args[idx + 1])
                if od_strony < 1:
                    print("\n❌ Numer strony musi być większy od 0\n")
                    sys.exit(1)
            except (IndexError, ValueError):
                print("\n❌ Podaj numer strony, np: python tlumacz.py --od 41\n")
                sys.exit(1)

        if "--gemini" in args:
            try:
                idx = args.index("--gemini")
                gemini_key = args[idx + 1]
                silnik = "gemini"
            except (IndexError, ValueError):
                print("\n❌ Podaj klucz API Gemini, np: python tlumacz.py --gemini AIzaSy...\n")
                print("   Klucz dostaniesz na: https://aistudio.google.com/apikey\n")
                sys.exit(1)

        tlumacz(od_strony=od_strony, silnik=silnik, gemini_key=gemini_key)
