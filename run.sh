#!/bin/bash
# =============================================================================
# PDF Translator - Skrypt uruchomieniowy (Linux/Mac)
# =============================================================================
# Użycie:
#   ./run.sh plik.pdf              - tłumaczy cały plik
#   ./run.sh plik.pdf 1-10         - tłumaczy strony 1-10
#   ./run.sh plik.pdf 1-50 wynik.pdf  - tłumaczy strony 1-50, zapisuje jako wynik.pdf
# =============================================================================

set -e

INPUT_FILE="${1}"
PAGES="${2}"
OUTPUT_FILE="${3}"

if [ -z "$INPUT_FILE" ]; then
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║         PDF Translator - English → Polish               ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║                                                          ║"
    echo "║  Użycie:                                                 ║"
    echo "║    ./run.sh plik.pdf              (cały plik)            ║"
    echo "║    ./run.sh plik.pdf 1-10         (strony 1-10)          ║"
    echo "║    ./run.sh plik.pdf 1-50 wynik.pdf                      ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 1
fi

# Sprawdź czy plik istnieje
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Plik nie znaleziony: $INPUT_FILE"
    exit 1
fi

# Sprawdź czy Docker jest zainstalowany
if ! command -v docker &> /dev/null; then
    echo "❌ Docker nie jest zainstalowany!"
    echo ""
    echo "Zainstaluj Docker Desktop:"
    echo "  Windows/Mac: https://www.docker.com/products/docker-desktop/"
    echo "  Linux:       https://docs.docker.com/engine/install/"
    echo ""
    exit 1
fi

# Zbuduj obraz (tylko za pierwszym razem)
echo "🔧 Przygotowywanie środowiska (za pierwszym razem może potrwać ~1 min)..."
docker build -t pdf-translator . -q

# Przygotuj argumenty
DOCKER_ARGS="--input /data/$(basename "$INPUT_FILE")"

if [ -n "$PAGES" ]; then
    DOCKER_ARGS="$DOCKER_ARGS --pages $PAGES"
fi

if [ -n "$OUTPUT_FILE" ]; then
    DOCKER_ARGS="$DOCKER_ARGS --output /data/$OUTPUT_FILE"
fi

# Uruchom tłumaczenie
echo "🚀 Rozpoczynam tłumaczenie..."
echo ""
docker run --rm \
    -v "$(cd "$(dirname "$INPUT_FILE")" && pwd)":/data \
    pdf-translator $DOCKER_ARGS

echo ""
echo "✅ Gotowe!"
