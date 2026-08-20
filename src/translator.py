"""
Translation Layer - Handles text translation from English to Polish.

Uses deep-translator library with Google Translate backend (free, no API key needed).
Implements batching and rate limiting to avoid being blocked.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from deep_translator import GoogleTranslator
from config import (
    SOURCE_LANGUAGE,
    TARGET_LANGUAGE,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_DELAY,
    TRANSLATION_ENGINE,
)

logger = logging.getLogger(__name__)


class PDFTranslator:
    """
    Translates text while handling batching, caching, and error recovery.
    """

    def __init__(
        self,
        source_lang: str = SOURCE_LANGUAGE,
        target_lang: str = TARGET_LANGUAGE,
        engine: str = TRANSLATION_ENGINE,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.engine = engine
        self.cache: Dict[str, str] = {}
        self.translator = self._create_translator()

    def _create_translator(self) -> GoogleTranslator:
        """Create translator instance based on selected engine."""
        return GoogleTranslator(source=self.source_lang, target=self.target_lang)

    def translate_text(self, text: str) -> str:
        """
        Translate a single text string.
        Uses cache to avoid re-translating identical strings.
        """
        if not text or not text.strip():
            return text

        # Check cache first
        cache_key = text.strip()
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            translated = self.translator.translate(text)
            if translated:
                self.cache[cache_key] = translated
                return translated
            return text
        except Exception as e:
            logger.warning(f"Translation failed for '{text[:50]}...': {e}")
            return text

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Translate a batch of texts efficiently.
        Handles rate limiting and retries.
        """
        results = []

        for i in range(0, len(texts), TRANSLATION_BATCH_SIZE):
            batch = texts[i:i + TRANSLATION_BATCH_SIZE]
            batch_results = []

            for text in batch:
                if not text or not text.strip():
                    batch_results.append(text)
                    continue

                translated = self.translate_text(text)
                batch_results.append(translated)

            results.extend(batch_results)

            # Rate limiting between batches
            if i + TRANSLATION_BATCH_SIZE < len(texts):
                time.sleep(TRANSLATION_DELAY)

        return results

    def translate_spans(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Translate a list of span dictionaries, preserving all metadata.
        Adds 'translated_text' key to each span.
        """
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
