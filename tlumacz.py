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

UŻYCIE:

  python aplikacja.py            Interfejs graficzny (NAJŁATWIEJ)

  python tlumacz.py              Tłumacz od początku (Google Translate)
  python tlumacz.py --gemini KLUCZ   Tłumacz z Gemini (lepsza jakość)
  python tlumacz.py --od 41      Tłumacz od strony 41
  python tlumacz.py --polacz     Połącz części w jeden PDF
"""

import sys
import os
import time
import glob
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import fitz
except ImportError:
    import pymupdf as fitz

from tqdm import tqdm
from src.nowy_sklad import (
    wyciagnij_strukture_strony, wyciagnij_obrazki, zbuduj_pdf
)
from src.translator import PDFTranslator

# === KONFIGURACJA ===
PLIK_WEJSCIOWY = "The_Feynman_Lectures_on_Physics_Volume_1.pdf"
FOLDER_CZESCI = "czesci"
FOLDER_OBRAZKI = "obrazki"
PLIK_KONCOWY = "Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf"
ROZMIAR_PARTII = 10
# ====================


def tlumacz(od_strony: int = 1, silnik: str = "google", gemini_key: str = ""):
    """Tłumaczy PDF partiami po 10 stron – nowy skład."""

    if not os.path.exists(PLIK_WEJSCIOWY):
        print(f"\n❌ Nie znaleziono pliku: {PLIK_WEJSCIOWY}")
        sys.exit(1)

    os.makedirs(FOLDER_CZESCI, exist_ok=True)
    os.makedirs(FOLDER_OBRAZKI, exist_ok=True)

    doc = fitz.open(PLIK_WEJSCIOWY)
    total_pages = len(doc)

    silnik_nazwa = "Google Gemini" if silnik == "gemini" else "Google Translate"

    print(f"\n{'='*60}")
    print(f"  📖 TŁUMACZENIE: {PLIK_WEJSCIOWY}")
    print(f"  📄 Stron: {total_pages}")
    print(f"  📦 Partia: {ROZMIAR_PARTII} stron")
    print(f"  ▶️  Od strony: {od_strony}")
    print(f"  🔤 Silnik: {silnik_nazwa}")
    print(f"  📁 Części → {FOLDER_CZESCI}/")
    print(f"{'='*60}\n")

    translator = PDFTranslator(
        source_lang="en", target_lang="pl",
        engine=silnik,
        gemini_api_key=gemini_key if silnik == "gemini" else None,
    )

    start_idx = od_strony - 1
    partia_nr = (start_idx // ROZMIAR_PARTII) + 1

    for batch_start in range(start_idx, total_pages, ROZMIAR_PARTII):
        batch_end = min(batch_start + ROZMIAR_PARTII, total_pages)
        nazwa_pliku = os.path.join(
            FOLDER_CZESCI,
            f"czesc_{partia_nr:03d}_strony_{batch_start+1}-{batch_end}.pdf"
        )

        if os.path.exists(nazwa_pliku):
            print(f"  ⏭️  Partia {partia_nr} (strony {batch_start+1}-{batch_end}) – pomijam")
            partia_nr += 1
            continue

        print(f"\n  🔄 Partia {partia_nr}: strony {batch_start+1}-{batch_end}...")
        batch_start_time = time.time()

        # 1. Wyciągnij strukturę
        strony = []
        for page_num in range(batch_start, batch_end):
            page = doc[page_num]
            elementy = wyciagnij_strukture_strony(page)
            img_paths = wyciagnij_obrazki(doc, page_num, FOLDER_OBRAZKI)
            for path in img_paths:
                elementy.append({"typ": "plik_obrazka", "sciezka": path})
            strony.append({"numer": page_num + 1, "elementy": elementy})

        # 2. Tłumacz
        for strona in strony:
            for elem in strona["elementy"]:
                if elem.get("typ") in ("numer_strony", "plik_obrazka", "numer_rozdzialu"):
                    continue
                tekst = elem.get("tekst", "").strip()
                if tekst and len(tekst) > 2:
                    elem["tekst"] = translator.translate_text(tekst)

        # 3. Wygeneruj PDF
        zbuduj_pdf(strony, nazwa_pliku, "Wykłady Feynmana z Fizyki")

        elapsed = time.time() - batch_start_time
        print(f"  ✅ Zapisano: {nazwa_pliku} ({elapsed:.0f} sek)")
        partia_nr += 1

    doc.close()

    print(f"\n{'='*60}")
    print(f"  🎉 TŁUMACZENIE ZAKOŃCZONE!")
    print(f"  📁 Części w: {FOLDER_CZESCI}/")
    print(f"  Aby połączyć: python tlumacz.py --polacz")
    print(f"{'='*60}\n")


def polacz_czesci():
    """Łączy części w jeden PDF."""
    pliki = sorted(glob.glob(os.path.join(FOLDER_CZESCI, "czesc_*.pdf")))

    if not pliki:
        print(f"\n❌ Brak części w '{FOLDER_CZESCI}/'")
        sys.exit(1)

    print(f"\n  🔗 Łączę {len(pliki)} części...")

    wynik = fitz.open()
    for plik in tqdm(pliki, desc="  Łączenie", unit="część"):
        czesc = fitz.open(plik)
        wynik.insert_pdf(czesc)
        czesc.close()

    wynik.save(PLIK_KONCOWY, garbage=4, deflate=True, clean=True)
    stron = wynik.page_count
    wynik.close()

    print(f"\n  ✅ Gotowe: {PLIK_KONCOWY} ({stron} stron)")
    print(f"  Kliknij prawym → Download\n")


def pokaz_pomoc():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           TŁUMACZ PDF – angielski → polski                   ║
╚══════════════════════════════════════════════════════════════╝

  python aplikacja.py            Interfejs graficzny (NAJŁATWIEJ)

  python tlumacz.py              Tłumacz (Google Translate)
  python tlumacz.py --gemini KLUCZ   Tłumacz z Gemini (lepsza jakość)
  python tlumacz.py --od 41      Wznów od strony 41
  python tlumacz.py --polacz     Połącz części w jeden PDF

  Klucz Gemini: https://aistudio.google.com/apikey
""")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    args = sys.argv[1:]

    if "--pomoc" in args or "--help" in args or "-h" in args:
        pokaz_pomoc()
    elif "--polacz" in args:
        polacz_czesci()
    else:
        od_strony = 1
        silnik = "google"
        gemini_key = ""

        if "--od" in args:
            try:
                od_strony = int(args[args.index("--od") + 1])
            except (IndexError, ValueError):
                print("❌ Podaj numer strony: --od 41")
                sys.exit(1)

        if "--gemini" in args:
            try:
                gemini_key = args[args.index("--gemini") + 1]
                silnik = "gemini"
            except (IndexError, ValueError):
                print("❌ Podaj klucz: --gemini AIzaSy...")
                sys.exit(1)

        tlumacz(od_strony=od_strony, silnik=silnik, gemini_key=gemini_key)
