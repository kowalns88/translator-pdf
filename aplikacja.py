#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║       TŁUMACZ PDF – interfejs graficzny (przeglądarka)       ║
║                                                              ║
║  Uruchom:  python aplikacja.py                               ║
║  Otworzy się przeglądarka z prostym interfejsem.             ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import time
import json
import glob
import threading
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import fitz
except ImportError:
    import pymupdf as fitz

from flask import Flask, render_template_string, jsonify, request, send_file
from src.extractor import extract_page_elements, extract_translatable_texts
from src.translator import PDFTranslator
from src.reconstructor import reconstruct_page

# Konfiguracja logowania
logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)

# === STAN APLIKACJI ===
stan = {
    "tłumaczenie_aktywne": False,
    "postep": 0,
    "total_stron": 0,
    "aktualna_partia": 0,
    "total_partii": 0,
    "aktualna_strona": 0,
    "status": "gotowy",  # gotowy, tłumaczę, zakończone, błąd
    "komunikat": "",
    "czas_start": 0,
}

# === KONFIGURACJA ===
FOLDER_CZESCI = "czesci"
ROZMIAR_PARTII = 10
PLIK_KONCOWY = "Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf"


def znajdz_pdf():
    """Znajdź plik PDF w bieżącym katalogu."""
    pliki = glob.glob("*.pdf")
    # Wyklucz pliki wynikowe
    pliki = [p for p in pliki if "_PL" not in p and "Wyklady" not in p]
    return pliki


def policz_przetlumaczone():
    """Policz ile partii jest już przetłumaczonych."""
    if not os.path.exists(FOLDER_CZESCI):
        return []
    pliki = sorted(glob.glob(os.path.join(FOLDER_CZESCI, "czesc_*.pdf")))
    return pliki


def tlumacz_w_tle(plik_wejsciowy, od_strony, silnik="google", gemini_key=""):
    """Funkcja tłumaczenia uruchamiana w osobnym wątku."""
    global stan

    try:
        stan["tłumaczenie_aktywne"] = True
        stan["status"] = "tłumaczę"
        stan["czas_start"] = time.time()

        os.makedirs(FOLDER_CZESCI, exist_ok=True)

        doc = fitz.open(plik_wejsciowy)
        total_pages = len(doc)
        stan["total_stron"] = total_pages

        translator = PDFTranslator(
            source_lang="en",
            target_lang="pl",
            engine=silnik,
            gemini_api_key=gemini_key if silnik == "gemini" else None,
        )

        start_idx = od_strony - 1
        total_partii = (total_pages - start_idx + ROZMIAR_PARTII - 1) // ROZMIAR_PARTII
        stan["total_partii"] = total_partii

        partia_nr = (start_idx // ROZMIAR_PARTII) + 1

        for batch_start in range(start_idx, total_pages, ROZMIAR_PARTII):
            if not stan["tłumaczenie_aktywne"]:
                stan["status"] = "zatrzymany"
                stan["komunikat"] = f"Zatrzymano na stronie {batch_start + 1}"
                break

            batch_end = min(batch_start + ROZMIAR_PARTII, total_pages)
            nazwa_pliku = os.path.join(
                FOLDER_CZESCI,
                f"czesc_{partia_nr:03d}_strony_{batch_start+1}-{batch_end}.pdf"
            )

            # Pomiń istniejące części
            if os.path.exists(nazwa_pliku):
                stan["komunikat"] = f"Partia {partia_nr} już istnieje, pomijam..."
                partia_nr += 1
                continue

            stan["aktualna_partia"] = partia_nr
            stan["komunikat"] = f"Tłumaczę strony {batch_start+1}–{batch_end}..."

            output_doc = fitz.open()

            for page_num in range(batch_start, batch_end):
                if not stan["tłumaczenie_aktywne"]:
                    break

                stan["aktualna_strona"] = page_num + 1
                stan["postep"] = int((page_num - start_idx + 1) / (total_pages - start_idx) * 100)

                page = doc[page_num]
                elements = extract_page_elements(page)
                translatable_spans = extract_translatable_texts(elements)

                if translatable_spans:
                    translated_spans = translator.translate_spans(translatable_spans)
                    reconstruct_page(doc, page_num, translated_spans, output_doc)
                else:
                    new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
                    new_page.show_pdf_page(new_page.rect, doc, page_num)

            if stan["tłumaczenie_aktywne"]:
                output_doc.save(nazwa_pliku, garbage=4, deflate=True, clean=True)

            output_doc.close()
            partia_nr += 1

        doc.close()

        if stan["tłumaczenie_aktywne"]:
            stan["status"] = "zakończone"
            stan["postep"] = 100
            elapsed = time.time() - stan["czas_start"]
            stan["komunikat"] = f"Tłumaczenie zakończone! Czas: {elapsed/60:.1f} min"

    except Exception as e:
        stan["status"] = "błąd"
        stan["komunikat"] = f"Błąd: {str(e)}"

    finally:
        stan["tłumaczenie_aktywne"] = False


# === INTERFEJS WWW ===

STRONA_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tłumacz PDF – angielski → polski</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: #16213e;
            border-radius: 16px;
            padding: 40px;
            max-width: 700px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 1.8em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }
        .panel {
            background: #0f3460;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .panel h3 {
            margin-bottom: 12px;
            color: #a8d8ea;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1a4080;
        }
        .info-row:last-child { border-bottom: none; }
        .info-label { color: #888; }
        .info-value { color: #fff; font-weight: 500; }
        .btn {
            display: inline-block;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin: 5px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-success {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }
        .btn-danger {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
            color: white;
        }
        .btn-warning {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        .buttons { text-align: center; margin: 20px 0; }
        .progress-container {
            background: #0a1a3a;
            border-radius: 8px;
            padding: 3px;
            margin: 15px 0;
        }
        .progress-bar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 24px;
            border-radius: 6px;
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            font-weight: bold;
            min-width: 40px;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        .status-gotowy { background: #1a4080; color: #a8d8ea; }
        .status-tłumaczę { background: #4a1080; color: #d8a8ea; }
        .status-zakończone { background: #0a4020; color: #a8ead8; }
        .status-błąd { background: #401010; color: #eaa8a8; }
        .status-zatrzymany { background: #403010; color: #ead8a8; }
        .message {
            text-align: center;
            padding: 10px;
            color: #ccc;
            font-style: italic;
        }
        .input-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 10px 0;
        }
        .input-group label { color: #888; white-space: nowrap; }
        .input-group input {
            background: #0a1a3a;
            border: 1px solid #1a4080;
            color: #fff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 1em;
            width: 100px;
        }
        .parts-list {
            max-height: 200px;
            overflow-y: auto;
            font-size: 0.85em;
        }
        .parts-list div {
            padding: 4px 0;
            color: #8a8;
        }
        select {
            background: #0a1a3a;
            border: 1px solid #1a4080;
            color: #fff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 1em;
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Tłumacz PDF</h1>
        <p class="subtitle">angielski → polski (z zachowaniem układu)</p>

        <!-- Informacje o pliku -->
        <div class="panel">
            <h3>📁 Plik do tłumaczenia</h3>
            <div id="file-info">Ładowanie...</div>
        </div>

        <!-- Opcje startu -->
        <div class="panel" id="panel-start">
            <h3>⚙️ Opcje</h3>
            <div class="input-group">
                <label for="od-strony">Tłumacz od strony:</label>
                <input type="number" id="od-strony" value="1" min="1">
            </div>
            <div class="input-group">
                <label for="silnik">Silnik tłumaczenia:</label>
                <select id="silnik" onchange="pokazKlucz()">
                    <option value="google">Google Translate (darmowy, średnia jakość)</option>
                    <option value="gemini">Google Gemini (najlepsza jakość, wymaga klucza API)</option>
                </select>
            </div>
            <div class="input-group" id="klucz-group" style="display:none">
                <label for="gemini-key">Klucz API Gemini:</label>
                <input type="password" id="gemini-key" placeholder="wklej klucz z aistudio.google.com" style="width:300px">
            </div>
            <div id="gemini-info" style="display:none; margin-top:10px; padding:10px; background:#1a3060; border-radius:8px; font-size:0.85em; color:#aac">
                💡 Klucz API dostaniesz za darmo na: <a href="https://aistudio.google.com/apikey" target="_blank" style="color:#8af">aistudio.google.com/apikey</a><br>
                Mając plan Google One AI Pro, masz wyższe limity.
            </div>
        </div>

        <!-- Przyciski -->
        <div class="buttons">
            <button class="btn btn-primary" id="btn-start" onclick="rozpocznij()">
                ▶️ Rozpocznij tłumaczenie
            </button>
            <button class="btn btn-danger" id="btn-stop" onclick="zatrzymaj()" style="display:none">
                ⏹️ Zatrzymaj
            </button>
            <button class="btn btn-success" id="btn-polacz" onclick="polacz()">
                🔗 Połącz części w jeden PDF
            </button>
        </div>

        <!-- Postęp -->
        <div class="panel" id="panel-postep" style="display:none">
            <h3>📊 Postęp</h3>
            <div class="progress-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%">0%</div>
            </div>
            <div class="info-row">
                <span class="info-label">Status:</span>
                <span class="info-value"><span class="status-badge status-gotowy" id="status-badge">gotowy</span></span>
            </div>
            <div class="info-row">
                <span class="info-label">Strona:</span>
                <span class="info-value" id="strona-info">–</span>
            </div>
            <div class="info-row">
                <span class="info-label">Partia:</span>
                <span class="info-value" id="partia-info">–</span>
            </div>
            <div class="message" id="komunikat"></div>
        </div>

        <!-- Przetłumaczone części -->
        <div class="panel">
            <h3>✅ Przetłumaczone części</h3>
            <div class="parts-list" id="parts-list">Brak</div>
        </div>

        <!-- Pobranie -->
        <div class="panel" id="panel-pobierz" style="display:none">
            <h3>📥 Pobierz gotowy plik</h3>
            <div class="buttons">
                <button class="btn btn-success" onclick="pobierz()">
                    ⬇️ Pobierz przetłumaczony PDF
                </button>
            </div>
        </div>
    </div>

    <script>
        let odswiezanie = null;

        async function zaladujInfo() {
            const resp = await fetch('/api/info');
            const dane = await resp.json();

            let html = '';
            if (dane.pliki.length > 0) {
                html += `<div class="info-row"><span class="info-label">Plik:</span><span class="info-value">${dane.pliki[0]}</span></div>`;
                html += `<div class="info-row"><span class="info-label">Stron:</span><span class="info-value">${dane.total_stron}</span></div>`;
            } else {
                html = '<p style="color:#f55">Nie znaleziono pliku PDF w folderze!</p>';
            }
            document.getElementById('file-info').innerHTML = html;

            // Części
            odswiezCzesci(dane.czesci);

            // Plik końcowy
            if (dane.plik_koncowy_istnieje) {
                document.getElementById('panel-pobierz').style.display = 'block';
            }
        }

        function odswiezCzesci(czesci) {
            const el = document.getElementById('parts-list');
            if (czesci.length === 0) {
                el.innerHTML = '<div style="color:#888">Brak – rozpocznij tłumaczenie</div>';
            } else {
                el.innerHTML = czesci.map(c => `<div>✅ ${c}</div>`).join('');
            }
        }

        function pokazKlucz() {
            const silnik = document.getElementById('silnik').value;
            document.getElementById('klucz-group').style.display = silnik === 'gemini' ? 'flex' : 'none';
            document.getElementById('gemini-info').style.display = silnik === 'gemini' ? 'block' : 'none';
        }

        async function rozpocznij() {
            const odStrony = document.getElementById('od-strony').value || 1;
            const silnik = document.getElementById('silnik').value;
            const geminiKey = document.getElementById('gemini-key').value;

            if (silnik === 'gemini' && !geminiKey) {
                alert('Wklej klucz API Gemini! Dostaniesz go na: aistudio.google.com/apikey');
                return;
            }

            const resp = await fetch('/api/tlumacz', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    od_strony: parseInt(odStrony),
                    silnik: silnik,
                    gemini_key: geminiKey
                })
            });
            const dane = await resp.json();

            if (dane.ok) {
                document.getElementById('btn-start').style.display = 'none';
                document.getElementById('btn-stop').style.display = 'inline-block';
                document.getElementById('panel-postep').style.display = 'block';
                odswiezanie = setInterval(odswiezPostep, 1000);
            } else {
                alert(dane.blad || 'Wystąpił błąd');
            }
        }

        async function zatrzymaj() {
            await fetch('/api/zatrzymaj', {method: 'POST'});
            document.getElementById('btn-start').style.display = 'inline-block';
            document.getElementById('btn-stop').style.display = 'none';
            if (odswiezanie) clearInterval(odswiezanie);
        }

        async function polacz() {
            const resp = await fetch('/api/polacz', {method: 'POST'});
            const dane = await resp.json();
            if (dane.ok) {
                alert('✅ Połączono! Plik: ' + dane.plik);
                document.getElementById('panel-pobierz').style.display = 'block';
            } else {
                alert('❌ ' + (dane.blad || 'Błąd'));
            }
        }

        function pobierz() {
            window.location.href = '/api/pobierz';
        }

        async function odswiezPostep() {
            const resp = await fetch('/api/postep');
            const dane = await resp.json();

            // Pasek postępu
            const bar = document.getElementById('progress-bar');
            bar.style.width = dane.postep + '%';
            bar.textContent = dane.postep + '%';

            // Status
            const badge = document.getElementById('status-badge');
            badge.textContent = dane.status;
            badge.className = 'status-badge status-' + dane.status;

            // Info
            document.getElementById('strona-info').textContent =
                dane.aktualna_strona + ' / ' + dane.total_stron;
            document.getElementById('partia-info').textContent =
                dane.aktualna_partia + ' / ' + dane.total_partii;
            document.getElementById('komunikat').textContent = dane.komunikat;

            // Części
            odswiezCzesci(dane.czesci);

            // Koniec?
            if (dane.status === 'zakończone' || dane.status === 'błąd' || dane.status === 'zatrzymany') {
                document.getElementById('btn-start').style.display = 'inline-block';
                document.getElementById('btn-stop').style.display = 'none';
                if (odswiezanie) clearInterval(odswiezanie);
                if (dane.status === 'zakończone') {
                    document.getElementById('panel-pobierz').style.display = 'block';
                }
            }
        }

        // Załaduj info na starcie
        zaladujInfo();
    </script>
</body>
</html>
"""


@app.route('/')
def strona_glowna():
    return render_template_string(STRONA_HTML)


@app.route('/api/info')
def api_info():
    pliki = znajdz_pdf()
    total_stron = 0
    if pliki:
        try:
            doc = fitz.open(pliki[0])
            total_stron = len(doc)
            doc.close()
        except:
            pass

    czesci = [os.path.basename(f) for f in policz_przetlumaczone()]

    return jsonify({
        "pliki": pliki,
        "total_stron": total_stron,
        "czesci": czesci,
        "plik_koncowy_istnieje": os.path.exists(PLIK_KONCOWY),
    })


@app.route('/api/tlumacz', methods=['POST'])
def api_tlumacz():
    global stan

    if stan["tłumaczenie_aktywne"]:
        return jsonify({"ok": False, "blad": "Tłumaczenie już trwa!"})

    pliki = znajdz_pdf()
    if not pliki:
        return jsonify({"ok": False, "blad": "Nie znaleziono pliku PDF"})

    dane = request.json or {}
    od_strony = dane.get("od_strony", 1)
    silnik = dane.get("silnik", "google")
    gemini_key = dane.get("gemini_key", "")

    # Reset stanu
    stan["postep"] = 0
    stan["status"] = "tłumaczę"
    stan["komunikat"] = "Rozpoczynam..."
    stan["aktualna_strona"] = 0
    stan["aktualna_partia"] = 0

    # Uruchom tłumaczenie w tle
    watek = threading.Thread(
        target=tlumacz_w_tle,
        args=(pliki[0], od_strony, silnik, gemini_key)
    )
    watek.daemon = True
    watek.start()

    return jsonify({"ok": True})


@app.route('/api/zatrzymaj', methods=['POST'])
def api_zatrzymaj():
    global stan
    stan["tłumaczenie_aktywne"] = False
    return jsonify({"ok": True})


@app.route('/api/postep')
def api_postep():
    czesci = [os.path.basename(f) for f in policz_przetlumaczone()]
    return jsonify({
        "postep": stan["postep"],
        "status": stan["status"],
        "komunikat": stan["komunikat"],
        "aktualna_strona": stan["aktualna_strona"],
        "total_stron": stan["total_stron"],
        "aktualna_partia": stan["aktualna_partia"],
        "total_partii": stan["total_partii"],
        "czesci": czesci,
    })


@app.route('/api/polacz', methods=['POST'])
def api_polacz():
    czesci_pliki = policz_przetlumaczone()

    if not czesci_pliki:
        return jsonify({"ok": False, "blad": "Brak przetłumaczonych części"})

    try:
        wynik = fitz.open()
        for plik in czesci_pliki:
            czesc = fitz.open(plik)
            wynik.insert_pdf(czesc)
            czesc.close()

        wynik.save(PLIK_KONCOWY, garbage=4, deflate=True, clean=True)
        wynik.close()

        return jsonify({"ok": True, "plik": PLIK_KONCOWY, "stron": fitz.open(PLIK_KONCOWY).page_count})
    except Exception as e:
        return jsonify({"ok": False, "blad": str(e)})


@app.route('/api/pobierz')
def api_pobierz():
    if os.path.exists(PLIK_KONCOWY):
        return send_file(
            os.path.abspath(PLIK_KONCOWY),
            as_attachment=True,
            download_name=PLIK_KONCOWY
        )
    return "Plik nie istnieje", 404


if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       TŁUMACZ PDF – interfejs graficzny                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║                                                          ║")
    print("║  Otwórz w przeglądarce:                                  ║")
    print("║  👉  http://localhost:5000                                ║")
    print("║                                                          ║")
    print("║  (W Codespaces link pojawi się automatycznie)            ║")
    print("║                                                          ║")
    print("║  Aby zatrzymać: Ctrl+C                                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    app.run(host="0.0.0.0", port=5000, debug=False)
