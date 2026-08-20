"""
Nowy skład PDF – wyciąga treść z oryginału i generuje ładny polski PDF.

Strategia:
1. Wyciągnij tekst strona po stronie (z rozróżnieniem nagłówków/akapitów)
2. Wyciągnij obrazki
3. Przetłumacz pełnymi akapitami (lepsza jakość)
4. Złóż nowy PDF z reportlab (profesjonalny skład)
"""

import os
import io
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

try:
    import fitz
except ImportError:
    import pymupdf as fitz

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# === KONFIGURACJA STYLU ===
# Zbliżone do oryginału: LM Roman ~10pt, strona ~5.8x7.7 cali
PAGE_WIDTH = 5.8 * 72  # punkty
PAGE_HEIGHT = 7.7 * 72

MARGIN_LEFT = 1.2 * cm
MARGIN_RIGHT = 1.2 * cm
MARGIN_TOP = 1.5 * cm
MARGIN_BOTTOM = 1.5 * cm

# Kolor czerwony z okładki Feynmana
FEYNMAN_RED = HexColor("#CC2222")


def zarejestruj_czcionki():
    """Rejestruje czcionki do składu PDF. Szuka w wielu lokalizacjach."""
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    # Możliwe lokalizacje czcionek
    font_dirs = [
        "/usr/share/fonts/google-noto",
        "/usr/share/fonts/truetype/noto",
        "/usr/share/fonts/noto",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts",
    ]

    # Szukamy czcionek w kolejności preferencji
    font_variants = {
        "NotoSerif": [
            "NotoSerif-Regular.ttf", "NotoSans-Regular.ttf", "DejaVuSerif.ttf", "DejaVuSans.ttf"
        ],
        "NotoSerif-Bold": [
            "NotoSerif-Bold.ttf", "NotoSans-Bold.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf"
        ],
        "NotoSerif-Italic": [
            "NotoSerif-Italic.ttf", "NotoSans-Italic.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSans-Oblique.ttf"
        ],
        "NotoSerif-BoldItalic": [
            "NotoSerif-BoldItalic.ttf", "NotoSans-BoldItalic.ttf", "DejaVuSerif-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf"
        ],
    }

    def find_font(filenames):
        """Szuka pliku czcionki w znanych katalogach."""
        for font_dir in font_dirs:
            for filename in filenames:
                path = os.path.join(font_dir, filename)
                if os.path.exists(path):
                    return path
        # Szukaj rekursywnie
        for font_dir in font_dirs:
            if os.path.isdir(font_dir):
                for root, dirs, files in os.walk(font_dir):
                    for filename in filenames:
                        if filename in files:
                            return os.path.join(root, filename)
        return None

    # Rejestruj każdy wariant
    registered_any = False
    for font_name, candidates in font_variants.items():
        path = find_font(candidates)
        if path:
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                registered_any = True
                logger.debug(f"Czcionka {font_name} → {path}")
            except Exception as e:
                logger.warning(f"Nie udało się zarejestrować {font_name}: {e}")

    if not registered_any:
        # Ostateczny fallback – użyj wbudowanej Helvetica
        logger.warning("Brak zewnętrznych czcionek – używam wbudowanych")
        # Reportlab ma wbudowaną Helvetica, nie trzeba nic rejestrować
        # Ale musimy zmienić nazwy w stylach
        return False

    # Zarejestruj rodzinę
    try:
        registerFontFamily(
            'NotoSerif',
            normal='NotoSerif',
            bold='NotoSerif-Bold',
            italic='NotoSerif-Italic',
            boldItalic='NotoSerif-BoldItalic',
        )
    except Exception as e:
        logger.warning(f"Nie udało się zarejestrować rodziny czcionek: {e}")

    return True


def stworz_style():
    """Tworzy style akapitów zbliżone do oryginału Feynmana."""
    styles = getSampleStyleSheet()

    # Tekst główny – 10pt serif, justowany
    styles.add(ParagraphStyle(
        name='Tresc',
        fontName='NotoSerif',
        fontSize=10,
        leading=13,  # interlinia
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        firstLineIndent=18,
    ))

    # Pierwszy akapit (bez wcięcia)
    styles.add(ParagraphStyle(
        name='TrescPierwszy',
        parent=styles['Tresc'],
        firstLineIndent=0,
    ))

    # Nagłówek rozdziału – duży, bold
    styles.add(ParagraphStyle(
        name='Rozdzial',
        fontName='NotoSerif-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_LEFT,
        spaceAfter=20,
        spaceBefore=30,
    ))

    # Numer rozdziału
    styles.add(ParagraphStyle(
        name='NumerRozdzialu',
        fontName='NotoSerif-Bold',
        fontSize=24,
        leading=28,
        alignment=TA_LEFT,
        spaceAfter=4,
        textColor=FEYNMAN_RED,
    ))

    # Podrozdział – bold, 11pt
    styles.add(ParagraphStyle(
        name='Podrozdzial',
        fontName='NotoSerif-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceBefore=16,
        spaceAfter=8,
        firstLineIndent=0,
    ))

    # Kursywa (cytaty, nazwy dzieł)
    styles.add(ParagraphStyle(
        name='Kursywa',
        fontName='NotoSerif-Italic',
        fontSize=10,
        leading=13,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))

    # Stopka / numery stron
    styles.add(ParagraphStyle(
        name='Stopka',
        fontName='NotoSerif',
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
    ))

    return styles


def wyciagnij_strukture_strony(page: fitz.Page) -> Dict[str, Any]:
    """
    Wyciąga strukturę strony: nagłówki, akapity, obrazki.
    Rozpoznaje typy bloków po rozmiarze czcionki.
    """
    text_dict = page.get_text("dict")
    elementy = []

    for block in text_dict.get("blocks", []):
        if block["type"] == 1:
            # Obrazek
            elementy.append({"typ": "obrazek", "bbox": block["bbox"]})
            continue

        if block["type"] != 0:
            continue

        # Zbierz tekst bloku
        block_text = ""
        max_font_size = 0
        is_bold = False
        is_italic = False

        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                line_text += span["text"]
                max_font_size = max(max_font_size, span["size"])
                if span["flags"] & 16:
                    is_bold = True
                if span["flags"] & 2:
                    is_italic = True
            block_text += line_text + "\n"

        block_text = block_text.strip()
        if not block_text:
            continue

        # Klasyfikacja bloku
        if max_font_size > 12:
            # Duża czcionka = numer rozdziału lub tytuł
            if re.match(r'^\d+$', block_text.strip()):
                typ = "numer_rozdzialu"
            else:
                typ = "tytul_rozdzialu"
        elif is_bold or re.match(r'^\d+-\d+\s', block_text):
            typ = "podrozdzial"
        elif len(block_text) < 10 and re.match(r'^[ivxlc\d]+$', block_text.strip()):
            typ = "numer_strony"
        elif max_font_size < 9.5 and len(block_text) < 15:
            typ = "numer_strony"
        else:
            typ = "akapit"

        elementy.append({
            "typ": typ,
            "tekst": block_text,
            "rozmiar_czcionki": max_font_size,
            "bold": is_bold,
            "italic": is_italic,
        })

    return elementy


def wyciagnij_obrazki(doc: fitz.Document, page_num: int, output_dir: str) -> List[str]:
    """Wyciąga obrazki ze strony i zapisuje do plików."""
    page = doc[page_num]
    img_list = page.get_images()
    saved_paths = []

    for i, img in enumerate(img_list):
        xref = img[0]
        try:
            base_image = doc.extract_image(xref)
            img_data = base_image["image"]
            img_ext = base_image["ext"]
            img_path = os.path.join(output_dir, f"img_p{page_num+1}_{i+1}.{img_ext}")

            with open(img_path, "wb") as f:
                f.write(img_data)

            saved_paths.append(img_path)
        except Exception as e:
            logger.warning(f"Nie udało się wyciągnąć obrazka ze strony {page_num+1}: {e}")

    return saved_paths


def wyciagnij_caly_dokument(input_path: str, img_dir: str = "obrazki") -> List[Dict]:
    """
    Wyciąga pełną strukturę dokumentu: strony → elementy (nagłówki, akapity, obrazki).
    """
    os.makedirs(img_dir, exist_ok=True)
    doc = fitz.open(input_path)
    strony = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        elementy = wyciagnij_strukture_strony(page)

        # Wyciągnij obrazki
        img_paths = wyciagnij_obrazki(doc, page_num, img_dir)
        if img_paths:
            # Dodaj obrazki do elementów
            for path in img_paths:
                elementy.append({"typ": "plik_obrazka", "sciezka": path})

        strony.append({
            "numer": page_num + 1,
            "elementy": elementy,
        })

    doc.close()
    return strony


def zbuduj_pdf(
    strony_przetlumaczone: List[Dict],
    output_path: str,
    tytul: str = "Wykłady Feynmana z Fizyki, Tom I",
):
    """
    Generuje nowy PDF z przetłumaczoną treścią.
    """
    zarejestruj_czcionki()
    styles = stworz_style()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title=tytul,
        author="Feynman, Leighton, Sands (tłumaczenie automatyczne)",
    )

    # Buduj elementy dokumentu
    story = []

    for strona in strony_przetlumaczone:
        for elem in strona.get("elementy", []):
            typ = elem.get("typ", "")
            tekst = elem.get("tekst", "").strip()

            if not tekst and typ != "plik_obrazka":
                continue

            # Escape HTML characters for reportlab
            tekst_safe = tekst.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

            if typ == "numer_rozdzialu":
                story.append(Spacer(1, 20))
                story.append(Paragraph(tekst_safe, styles["NumerRozdzialu"]))

            elif typ == "tytul_rozdzialu":
                story.append(Paragraph(tekst_safe, styles["Rozdzial"]))
                story.append(Spacer(1, 10))

            elif typ == "podrozdzial":
                story.append(Paragraph(tekst_safe, styles["Podrozdzial"]))

            elif typ == "akapit":
                # Zamień łamanie wierszy na spacje (reportlab sam łamie)
                tekst_joined = " ".join(tekst_safe.split())
                if elem.get("italic"):
                    tekst_joined = f"<i>{tekst_joined}</i>"
                story.append(Paragraph(tekst_joined, styles["Tresc"]))

            elif typ == "plik_obrazka":
                sciezka = elem.get("sciezka", "")
                if os.path.exists(sciezka):
                    try:
                        # Dopasuj szerokość obrazka do kolumny
                        avail_width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
                        img = Image(sciezka)
                        # Skaluj proporcjonalnie
                        ratio = img.imageWidth / img.imageHeight
                        img_width = min(avail_width, img.imageWidth)
                        img_height = img_width / ratio
                        if img_height > PAGE_HEIGHT * 0.6:
                            img_height = PAGE_HEIGHT * 0.6
                            img_width = img_height * ratio
                        img.drawWidth = img_width
                        img.drawHeight = img_height
                        story.append(Spacer(1, 10))
                        story.append(img)
                        story.append(Spacer(1, 10))
                    except Exception as e:
                        logger.warning(f"Nie udało się wstawić obrazka {sciezka}: {e}")

            elif typ == "numer_strony":
                # Pomijamy – reportlab sam numeruje
                pass

    # Generuj PDF
    doc.build(story)
    return output_path
