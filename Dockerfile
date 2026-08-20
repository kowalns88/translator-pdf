# PDF Translator - Docker image
# Użycie: docker build -t pdf-translator .
#         docker run -v $(pwd):/data pdf-translator --input /data/plik.pdf --pages 1-10

FROM python:3.11-slim

# Instalacja czcionek i zależności systemowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    && rm -rf /var/lib/apt/lists/*

# Katalog roboczy
WORKDIR /app

# Instalacja zależności Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY config.py .
COPY translate_pdf.py .
COPY src/ ./src/

# Katalog na pliki wyjściowe
RUN mkdir -p /app/output

# Domyślne polecenie
ENTRYPOINT ["python", "translate_pdf.py"]
CMD ["--help"]
