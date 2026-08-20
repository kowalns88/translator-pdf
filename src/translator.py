"""
Translation Layer - Handles text translation from English to Polish.

Supports multiple translation engines:
- Google Gemini (najlepsza jakość, wymaga klucza API z Google AI Studio)
- Google Translate (darmowy, średnia jakość, bez rejestracji)
"""

import os
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PDFTranslator:
    """
    Translates text using selected engine.
    Handles batching, caching, and error recovery.
    """

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

        if self.engine == "gemini":
            self._setup_gemini()
        else:
            self._setup_google_translate()

    def _setup_gemini(self):
        """Configure Google Gemini as translation engine."""
        if not self.gemini_api_key:
            raise ValueError(
                "Brak klucza API Gemini!\n"
                "Ustaw go w pliku .env lub podaj w interfejsie.\n"
                "Klucz możesz wygenerować na: https://aistudio.google.com/apikey"
            )
        from google import genai
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-2.5-flash"
        logger.info(f"Silnik: Google Gemini ({self.gemini_model})")

    def _setup_google_translate(self):
        """Configure free Google Translate as fallback."""
        from deep_translator import GoogleTranslator
        self.google_translator = GoogleTranslator(
            source=self.source_lang, target=self.target_lang
        )
        logger.info("Silnik: Google Translate (darmowy)")

    def translate_text(self, text: str) -> str:
        """Translate a single text string. Uses cache."""
        if not text or not text.strip():
            return text

        cache_key = text.strip()
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            if self.engine == "gemini":
                translated = self._translate_gemini(text)
            else:
                translated = self._translate_google(text)

            if translated:
                self.cache[cache_key] = translated
                return translated
            return text
        except Exception as e:
            logger.warning(f"Błąd tłumaczenia '{text[:50]}...': {e}")
            return text

    def _translate_gemini(self, text: str) -> str:
        """Translate using Google Gemini."""
        prompt = (
            f"Przetłumacz poniższy tekst z angielskiego na polski. "
            f"Zachowaj formatowanie i styl. Nie dodawaj żadnych wyjaśnień, "
            f"zwróć TYLKO przetłumaczony tekst.\n\n"
            f"Tekst: {text}"
        )
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
        )
        return response.text.strip()

    def _translate_google(self, text: str) -> str:
        """Translate using free Google Translate."""
        return self.google_translator.translate(text)

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a batch of texts.
        For Gemini: groups texts into larger prompts for efficiency.
        For Google Translate: translates one by one.
        """
        if self.engine == "gemini":
            return self._translate_batch_gemini(texts)
        else:
            return self._translate_batch_google(texts)

    def _translate_batch_gemini(self, texts: List[str]) -> List[str]:
        """
        Batch translation with Gemini.
        Groups multiple texts into one prompt for efficiency (fewer API calls).
        """
        results = []
        BATCH_SIZE = 20  # Ile tekstów w jednym zapytaniu do Gemini

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            batch_results = []

            # Filtruj – sprawdź cache i puste
            to_translate = []
            indices = []
            for idx, text in enumerate(batch):
                if not text or not text.strip():
                    batch_results.append(text)
                elif text.strip() in self.cache:
                    batch_results.append(self.cache[text.strip()])
                else:
                    to_translate.append(text)
                    indices.append(idx)
                    batch_results.append(None)  # placeholder

            if to_translate:
                try:
                    # Buduj prompt z numerowanymi liniami
                    numbered_texts = "\n".join(
                        f"[{j+1}] {t}" for j, t in enumerate(to_translate)
                    )
                    prompt = (
                        f"Przetłumacz poniższe teksty z angielskiego na polski. "
                        f"Zachowaj numerację [1], [2], itd. "
                        f"Nie dodawaj wyjaśnień. Zwróć TYLKO przetłumaczone linie "
                        f"z zachowaną numeracją.\n\n{numbered_texts}"
                    )

                    response = self.gemini_client.models.generate_content(
                        model=self.gemini_model,
                        contents=prompt,
                    )

                    # Parsuj odpowiedź
                    translated_lines = self._parse_numbered_response(
                        response.text, len(to_translate)
                    )

                    # Wstaw przetłumaczone teksty
                    translate_idx = 0
                    for idx in range(len(batch_results)):
                        if batch_results[idx] is None:
                            if translate_idx < len(translated_lines):
                                translated = translated_lines[translate_idx]
                                batch_results[idx] = translated
                                # Cache
                                orig = to_translate[translate_idx]
                                self.cache[orig.strip()] = translated
                            else:
                                batch_results[idx] = to_translate[translate_idx] if translate_idx < len(to_translate) else ""
                            translate_idx += 1

                except Exception as e:
                    logger.warning(f"Gemini batch error: {e}, falling back to single")
                    # Fallback: tłumacz pojedynczo
                    translate_idx = 0
                    for idx in range(len(batch_results)):
                        if batch_results[idx] is None:
                            text = to_translate[translate_idx]
                            batch_results[idx] = self.translate_text(text)
                            translate_idx += 1

            results.extend(batch_results)

            # Mały delay między batchami
            if i + BATCH_SIZE < len(texts):
                time.sleep(0.3)

        return results

    def _parse_numbered_response(self, response_text: str, expected_count: int) -> List[str]:
        """Parse Gemini's numbered response into a list of translations."""
        lines = response_text.strip().split("\n")
        results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Usuń numerację [1], [2], etc.
            import re
            cleaned = re.sub(r'^\[\d+\]\s*', '', line)
            if cleaned:
                results.append(cleaned)

        # Jeśli nie udało się sparsować – fallback na całość
        if len(results) < expected_count:
            # Spróbuj po prostu podzielić na linie
            all_lines = [l.strip() for l in response_text.strip().split("\n") if l.strip()]
            if len(all_lines) >= expected_count:
                results = all_lines[:expected_count]

        return results

    def _translate_batch_google(self, texts: List[str]) -> List[str]:
        """Batch translation with Google Translate (one by one with delay)."""
        results = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append(text)
                continue
            results.append(self.translate_text(text))
            # Rate limiting
            if i > 0 and i % 50 == 0:
                time.sleep(0.5)
        return results

    def translate_spans(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Translate spans, adding 'translated_text' to each."""
        texts = [span["text"] for span in spans]
        translated_texts = self.translate_batch(texts)

        for span, translated in zip(spans, translated_texts):
            span["translated_text"] = translated

        return spans

    def get_cache_stats(self) -> Dict[str, int]:
        """Return translation cache statistics."""
        return {
            "cached_entries": len(self.cache),
            "unique_translations": len(set(self.cache.values())),
        }
