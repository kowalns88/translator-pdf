"""
Configuration for the PDF Translator application.
"""

# Translation settings
SOURCE_LANGUAGE = "en"
TARGET_LANGUAGE = "pl"

# Translation engine: "google", "mymemory", "libre"
TRANSLATION_ENGINE = "google"

# Batch size for translation requests (to avoid rate limiting)
TRANSLATION_BATCH_SIZE = 50

# Delay between translation batches (seconds)
TRANSLATION_DELAY = 0.5

# PDF processing settings
# Minimum text length to translate (skip very short strings like single chars)
MIN_TEXT_LENGTH = 2

# Skip translation for text that appears to be a number, formula, or symbol
SKIP_PATTERNS = [
    r"^\d+\.?\d*$",          # Numbers
    r"^[=+\-*/^(){}[\]]+$",  # Math operators
    r"^\s*$",                 # Whitespace only
    r"^[A-Z]$",              # Single capital letters (often used as variables)
]

# Font settings
# Fallback font for Polish characters (supports diacritics: ą, ć, ę, ł, ń, ó, ś, ź, ż)
FALLBACK_FONT = "helv"  # Helvetica - built-in, supports basic Latin
USE_CUSTOM_FONT = False
CUSTOM_FONT_PATH = None  # Set to path of .ttf file with Polish character support

# Output settings
OUTPUT_SUFFIX = "_PL"  # Added to filename for translated version

# Logging
VERBOSE = True
LOG_FILE = "translation.log"
