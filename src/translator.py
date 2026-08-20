"""
Translation Layer – tłumaczenie stronami (nie fragmentami).

Strategia:
- Wysyłaj CAŁĄ STRONĘ tekstu w jednym zapytaniu do Gemini (lepszy kontekst)
- Pomijaj formuły matematyczne i krótkie fragmenty
- Przy błędzie 429: czekaj i ponów próbę (max 3 razy)
- Przy wyczerpaniu: ZATRZYMAJ SIĘ natychmiast
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Wzorce tekstów do pominięcia (formuły, numery, symbole)
SKIP_PATTERNS = [
    r'^\d+[\.\,]?\d*$',             # Same numery: "6.7", "1024"
    r'^[=+\-\*/\^(){}\[\]<>≥≤±√∑∫]+$',  # Same symbole matematyczne
    r'^\s*$',                          # Puste
    r'^[A-Z]\s*$',                     # Sama litera: "N", "D"
    r'^\(?[0-9]+\.[0-9]+\)?$',        # Numery równań: (6.1), (6.7)
    r'^Fig\.\s*\d',                    # Opisy rysunków - do osobnego tłumaczenia
    r'^[ivxlcIVXLC]+$',               # Numery rzymskie
]


def should_skip(text: str) -> bool:
    """Czy tekst powinien być pominięty w tłumaczeniu."""
    t = text.strip()
    if len(t) < 3:
        return True
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, t):
            return True
    return False


class PDFTranslator:
    """Tłumacz PDF – wysyła całe strony do API."""

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "pl",
        engine: str = "google",
        gemini_api_key: str = None,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.engine = engine
        self.cache: Dict[str, str] = {}
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.consecutive_errors = 0
        self.is_exhausted = False  # Flaga: tokeny wyczerpane

        if self.engine == "gemini":
            self._setup_gemini()
        else:
            self._setup_google_translate()

    def _setup_gemini(self):
        if not self.gemini_api_key:
            raise ValueError(
                "Brak klucza API Gemini! Wygeneruj na: https://aistudio.google.com/apikey"
            )
        from google import genai
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-3.6-flash"

    def _setup_google_translate(self):
        from deep_translator import GoogleTranslator
        self.google_translator = GoogleTranslator(
            source=self.source_lang, target=self.target_lang
        )

    def translate_page(self, page_text: str) -> str:
        """
        Tłumaczy CAŁĄ STRONĘ naraz (jeden request do API).
        To daje najlepszą jakość i oszczędza tokeny.
        """
        if not page_text or not page_text.strip():
            return page_text

        if self.is_exhausted:
            raise RuntimeError("Tokeny wyczerpane – zatrzymaj tłumaczenie")

        # Sprawdź cache
        cache_key = page_text.strip()[:200]  # Klucz = pierwsze 200 znaków
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Tłumacz
        try:
            if self.engine == "gemini":
                translated = self._translate_page_gemini(page_text)
            else:
                translated = self._translate_page_google(page_text)

            self.consecutive_errors = 0

            if translated:
                self.cache[cache_key] = translated
                return translated
            return page_text

        except Exception as e:
            return self._handle_error(e, page_text)

    def _translate_page_gemini(self, text: str) -> str:
        """Tłumaczy tekst (może być wiele stron) przez Gemini – jeden request."""
        prompt = (
            "Przetłumacz poniższy tekst z angielskiego na polski.\n"
            "ZASADY:\n"
            "- Zachowaj podział na akapity (puste linie między akapitami)\n"
            "- Zachowaj separatory ===STRONA=== dokładnie tam gdzie są\n"
            "- NIE tłumacz wzorów matematycznych, numerów równań (np. (6.1)), "
            "symboli (D², N, σ, √N, P(A)=NA/N)\n"
            "- NIE tłumacz numerów rozdziałów/podrozdziałów (np. '6-2', '7-1')\n"
            "- Zamień 'Fig.' na 'Rys.' w odniesieniach do rysunków\n"
            "- Zwróć TYLKO przetłumaczony tekst, bez komentarzy\n\n"
            f"TEKST:\n\n{text}"
        )

        # Retry logic: max 3 próby z oczekiwaniem
        for attempt in range(3):
            try:
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                error_str = str(e)

                # Wyczerpanie tokenów – STOP natychmiast
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    if "prepayment credits are depleted" in error_str:
                        logger.error("🛑 PREPAID WYCZERPANE! Doładuj konto w AI Studio.")
                        self.is_exhausted = True
                        raise

                    # Rate limit – czekaj i ponów
                    retry_match = re.search(r'retry in (\d+)', error_str)
                    wait_time = int(retry_match.group(1)) + 2 if retry_match else 35
                    
                    if attempt < 2:
                        logger.warning(f"⏳ Rate limit – czekam {wait_time}s (próba {attempt+1}/3)")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("🛑 3x rate limit z rzędu – STOP")
                        self.is_exhausted = True
                        raise

                # Inny błąd – nie ponawiaj
                raise

        return text  # Fallback

    def _translate_page_google(self, text: str) -> str:
        """Tłumaczy stronę przez Google Translate (dzieli na kawałki po 5000 znaków)."""
        MAX_CHUNK = 4900  # Google Translate limit

        if len(text) <= MAX_CHUNK:
            return self.google_translator.translate(text)

        # Podziel na kawałki po akapitach
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > MAX_CHUNK:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += ("\n\n" + para if current_chunk else para)

        if current_chunk:
            chunks.append(current_chunk)

        # Tłumacz kawałki
        translated_chunks = []
        for chunk in chunks:
            translated = self.google_translator.translate(chunk)
            translated_chunks.append(translated)
            time.sleep(0.3)  # Rate limiting

        return "\n\n".join(translated_chunks)

    def _handle_error(self, e: Exception, original_text: str) -> str:
        """Obsługa błędów – decyduje czy zatrzymać czy kontynuować."""
        error_str = str(e)
        self.consecutive_errors += 1

        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            self.is_exhausted = True
            raise RuntimeError(f"Tokeny wyczerpane: {error_str[:100]}")

        if self.consecutive_errors >= 5:
            self.is_exhausted = True
            raise RuntimeError(f"Za dużo błędów z rzędu ({self.consecutive_errors})")

        logger.warning(f"Błąd tłumaczenia (kontynuuję): {error_str[:80]}")
        return original_text

    def translate_text(self, text: str) -> str:
        """Tłumaczenie pojedynczego tekstu (kompatybilność wsteczna)."""
        return self.translate_page(text)

    def get_cache_stats(self) -> Dict[str, int]:
        return {"cached_entries": len(self.cache)}
