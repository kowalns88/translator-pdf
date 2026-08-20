#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║       TŁUMACZ PDF – interfejs graficzny (przeglądarka)       ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import time
import json
import glob
import threading
import logging
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import fitz
except ImportError:
    import pymupdf as fitz

from flask import Flask, render_template_string, jsonify, request, send_file
from src.nowy_sklad import wyciagnij_strukture_strony, wyciagnij_obrazki, zbuduj_pdf
from src.translator import PDFTranslator

app = Flask(__name__)

# === STAN APLIKACJI ===
stan = {
    "aktywne": False,
    "postep": 0,
    "total_stron": 0,
    "aktualna_partia": 0,
    "total_partii": 0,
    "aktualna_strona": 0,
    "status": "gotowy",
    "komunikat": "",
    "czas_start": 0,
}

# Logi – ostatnie 200 wpisów
logi = deque(maxlen=200)

FOLDER_CZESCI = "czesci"
FOLDER_OBRAZKI = "obrazki"
ROZMIAR_PARTII = 50  # 50 stron na partię = 1 zapytanie API
PLIK_KONCOWY = "Wyklady_Feynmana_z_Fizyki_Tom_1_PL.pdf"


def dodaj_log(msg: str, poziom: str = "info"):
    """Dodaje wpis do logów widocznych w interfejsie."""
    timestamp = time.strftime("%H:%M:%S")
    logi.append({"czas": timestamp, "msg": msg, "poziom": poziom})


def znajdz_pdf():
    pliki = glob.glob("*.pdf")
    return [p for p in pliki if "_PL" not in p and "Wyklady" not in p and "czesc" not in p]


def policz_przetlumaczone():
    if not os.path.exists(FOLDER_CZESCI):
        return []
    return sorted(glob.glob(os.path.join(FOLDER_CZESCI, "czesc_*.pdf")))


def tlumacz_w_tle(plik_wejsciowy, od_strony, do_strony, silnik, gemini_key):
    """Tłumaczenie w osobnym wątku."""
    global stan

    try:
        stan["aktywne"] = True
        stan["status"] = "tłumaczę"
        stan["czas_start"] = time.time()

        os.makedirs(FOLDER_CZESCI, exist_ok=True)
        os.makedirs(FOLDER_OBRAZKI, exist_ok=True)

        doc = fitz.open(plik_wejsciowy)
        total_pages = len(doc)

        # Walidacja zakresu
        od_idx = max(0, od_strony - 1)
        do_idx = min(total_pages, do_strony)
        stron_do_tlumaczenia = do_idx - od_idx

        stan["total_stron"] = stron_do_tlumaczenia
        stan["total_partii"] = (stron_do_tlumaczenia + ROZMIAR_PARTII - 1) // ROZMIAR_PARTII

        dodaj_log(f"Start: strony {od_strony}–{do_strony} ({stron_do_tlumaczenia} stron)")
        dodaj_log(f"Silnik: {'Google Gemini' if silnik == 'gemini' else 'Google Translate'}")

        # Inicjalizuj tłumacza
        try:
            translator = PDFTranslator(
                source_lang="en", target_lang="pl",
                engine=silnik,
                gemini_api_key=gemini_key if silnik == "gemini" else None,
            )
            dodaj_log("Tłumacz zainicjalizowany ✓")
        except Exception as e:
            dodaj_log(f"BŁĄD inicjalizacji tłumacza: {e}", "error")
            stan["status"] = "błąd"
            stan["komunikat"] = str(e)
            stan["aktywne"] = False
            doc.close()
            return

        partia_nr = ((od_idx) // ROZMIAR_PARTII) + 1
        strony_przetlumaczone = 0

        for batch_start in range(od_idx, do_idx, ROZMIAR_PARTII):
            if not stan["aktywne"]:
                dodaj_log("Zatrzymano przez użytkownika", "warn")
                stan["status"] = "zatrzymany"
                break

            batch_end = min(batch_start + ROZMIAR_PARTII, do_idx)
            nazwa_pliku = os.path.join(
                FOLDER_CZESCI,
                f"czesc_{partia_nr:03d}_strony_{batch_start+1}-{batch_end}.pdf"
            )

            # Pomiń istniejące
            if os.path.exists(nazwa_pliku):
                dodaj_log(f"Partia {partia_nr} (str. {batch_start+1}–{batch_end}) już istnieje, pomijam")
                partia_nr += 1
                strony_przetlumaczone += (batch_end - batch_start)
                stan["postep"] = int(strony_przetlumaczone / stron_do_tlumaczenia * 100)
                continue

            stan["aktualna_partia"] = partia_nr
            stan["komunikat"] = f"Partia {partia_nr}: strony {batch_start+1}–{batch_end}"
            dodaj_log(f"── Partia {partia_nr}: strony {batch_start+1}–{batch_end} ──")

            # 1. Wyciągnij strukturę
            strony = []
            for page_num in range(batch_start, batch_end):
                if not stan["aktywne"]:
                    break
                page = doc[page_num]
                elementy = wyciagnij_strukture_strony(page)
                img_paths = wyciagnij_obrazki(doc, page_num, FOLDER_OBRAZKI)
                for path in img_paths:
                    elementy.append({"typ": "plik_obrazka", "sciezka": path})
                strony.append({"numer": page_num + 1, "elementy": elementy})

            if not stan["aktywne"]:
                break

            # 2. Tłumacz – CAŁA PARTIA (50 stron) w 1 zapytaniu API
            if not stan["aktywne"]:
                break

            all_pages_text = []
            for strona in strony:
                page_text_parts = []
                for elem in strona["elementy"]:
                    if elem.get("typ") in ("numer_strony", "plik_obrazka"):
                        continue
                    tekst = elem.get("tekst", "").strip()
                    if tekst:
                        page_text_parts.append(tekst)
                all_pages_text.append("\n\n".join(page_text_parts))

            SEPARATOR = "\n\n===STRONA===\n\n"
            full_batch_text = SEPARATOR.join(all_pages_text)

            if not full_batch_text.strip():
                strony_przetlumaczone += len(strony)
                stan["postep"] = int(strony_przetlumaczone / stron_do_tlumaczenia * 100)
                partia_nr += 1
                continue

            dodaj_log(f"  Wysyłam {len(strony)} stron w 1 zapytaniu...")

            try:
                translated_batch = translator.translate_page(full_batch_text)
            except (RuntimeError, Exception) as e:
                err_msg = str(e)[:150]
                dodaj_log(f"🛑 STOP: {err_msg}", "error")
                dodaj_log(f"Wznów od strony {strony[0]['numer']}", "error")
                stan["status"] = "błąd"
                stan["komunikat"] = f"Wznów od strony {strony[0]['numer']}"
                stan["aktywne"] = False
                doc.close()
                return

            translated_pages = [p.strip() for p in translated_batch.split("===STRONA===")]

            for i, strona in enumerate(strony):
                translated_parts = translated_pages[i].split("\n\n") if i < len(translated_pages) else []
                elem_idx = 0
                for elem in strona["elementy"]:
                    if elem.get("typ") in ("numer_strony", "plik_obrazka"):
                        continue
                    tekst = elem.get("tekst", "").strip()
                    if tekst and elem_idx < len(translated_parts):
                        elem["tekst"] = translated_parts[elem_idx]
                        elem_idx += 1

            strony_przetlumaczone += len(strony)
            stan["postep"] = int(strony_przetlumaczone / stron_do_tlumaczenia * 100)
            stan["aktualna_strona"] = strony[-1]["numer"]
            dodaj_log(f"  ✓ {len(strony)} stron przetłumaczonych (1 zapytanie API)")

            if not stan["aktywne"]:
                break

            # 3. Generuj PDF
            try:
                zbuduj_pdf(strony, nazwa_pliku, "Wykłady Feynmana z Fizyki")
                dodaj_log(f"✅ Zapisano {nazwa_pliku}")
            except Exception as e:
                dodaj_log(f"❌ Błąd zapisu PDF: {e}", "error")

            partia_nr += 1

        doc.close()

        if stan["aktywne"]:
            elapsed = time.time() - stan["czas_start"]
            stan["status"] = "zakończone"
            stan["postep"] = 100
            stan["komunikat"] = f"Gotowe! Czas: {elapsed/60:.1f} min"
            dodaj_log(f"🎉 Tłumaczenie zakończone ({elapsed/60:.1f} min)")
            dodaj_log(f"Kliknij 'Połącz części' → 'Pobierz'")

    except Exception as e:
        stan["status"] = "błąd"
        stan["komunikat"] = f"Błąd: {str(e)}"
        dodaj_log(f"❌ KRYTYCZNY BŁĄD: {e}", "error")

    finally:
        stan["aktywne"] = False


# === HTML INTERFEJS ===
STRONA_HTML = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tłumacz PDF</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 5px; font-size: 1.6em; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { text-align: center; color: #888; margin-bottom: 20px; }
        .panel { background: #16213e; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
        .panel h3 { margin-bottom: 12px; color: #a8d8ea; font-size: 1em; }
        .row { display: flex; gap: 15px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
        .row label { color: #aaa; min-width: 120px; font-size: 0.9em; }
        .row input, .row select { background: #0a1a3a; border: 1px solid #1a4080; color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 0.95em; }
        .row input[type=number] { width: 80px; }
        .row select { width: 100%; max-width: 350px; }
        .row input[type=password] { width: 280px; }
        .btn { display: inline-block; padding: 12px 24px; border: none; border-radius: 8px; font-size: 0.95em; font-weight: 600; cursor: pointer; margin: 4px; transition: all 0.2s; }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
        .btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .btn-success { background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }
        .btn-danger { background: linear-gradient(135deg, #eb3349, #f45c43); color: white; }
        .buttons { text-align: center; margin: 15px 0; }
        .progress-container { background: #0a1a3a; border-radius: 8px; padding: 3px; margin: 10px 0; }
        .progress-bar { background: linear-gradient(135deg, #667eea, #764ba2); height: 22px; border-radius: 6px; transition: width 0.5s; display: flex; align-items: center; justify-content: center; font-size: 0.8em; font-weight: bold; min-width: 30px; }
        .info-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #0f3460; font-size: 0.9em; }
        .info-row:last-child { border: none; }
        .info-label { color: #777; }
        .info-value { color: #ddd; }
        .log-box { background: #0a0a1a; border: 1px solid #1a3060; border-radius: 8px; padding: 12px; max-height: 300px; overflow-y: auto; font-family: 'Consolas', 'Monaco', monospace; font-size: 0.82em; line-height: 1.6; }
        .log-line { padding: 1px 0; }
        .log-time { color: #555; }
        .log-info { color: #8c8; }
        .log-warn { color: #ec8; }
        .log-error { color: #e88; font-weight: bold; }
        .parts-list { font-size: 0.85em; max-height: 150px; overflow-y: auto; }
        .parts-list div { padding: 2px 0; color: #8a8; }
        .hint { font-size: 0.8em; color: #666; margin-top: 5px; }
        #gemini-extra { display: none; margin-top: 8px; }
    </style>
</head>
<body>
<div class="container">
    <h1>📄 Tłumacz PDF</h1>
    <p class="subtitle">angielski → polski | nowy skład z zachowaniem struktury</p>

    <div class="panel">
        <h3>📁 Plik</h3>
        <div id="file-info">Ładowanie...</div>
    </div>

    <div class="panel" id="panel-opcje">
        <h3>⚙️ Opcje tłumaczenia</h3>
        <div class="row">
            <label>Od strony:</label>
            <input type="number" id="od-strony" value="1" min="1">
            <label>Do strony:</label>
            <input type="number" id="do-strony" value="968" min="1">
        </div>
        <div class="row">
            <label>Silnik:</label>
            <select id="silnik" onchange="zmienSilnik()">
                <option value="google">Google Translate (darmowy, średnia jakość)</option>
                <option value="gemini">Google Gemini (lepsza jakość, wymaga klucza)</option>
            </select>
        </div>
        <div id="gemini-extra">
            <div class="row">
                <label>Klucz API:</label>
                <input type="password" id="gemini-key" placeholder="AIzaSy...">
            </div>
            <p class="hint">💡 Klucz: <a href="https://aistudio.google.com/apikey" target="_blank" style="color:#8af">aistudio.google.com/apikey</a></p>
        </div>
    </div>

    <div class="buttons">
        <button class="btn btn-primary" id="btn-start" onclick="rozpocznij()">▶️ Rozpocznij tłumaczenie</button>
        <button class="btn btn-danger" id="btn-stop" onclick="zatrzymaj()" style="display:none">⏹️ Zatrzymaj</button>
        <button class="btn btn-success" id="btn-polacz" onclick="polacz()">🔗 Połącz części</button>
    </div>

    <div class="panel" id="panel-postep" style="display:none">
        <h3>📊 Postęp</h3>
        <div class="progress-container">
            <div class="progress-bar" id="progress-bar" style="width:0%">0%</div>
        </div>
        <div class="info-row"><span class="info-label">Status:</span><span class="info-value" id="status-text">–</span></div>
        <div class="info-row"><span class="info-label">Strona:</span><span class="info-value" id="strona-info">–</span></div>
        <div class="info-row"><span class="info-label">Partia:</span><span class="info-value" id="partia-info">–</span></div>
        <div class="info-row"><span class="info-label">Info:</span><span class="info-value" id="komunikat">–</span></div>
    </div>

    <div class="panel">
        <h3>📋 Logi (na żywo)</h3>
        <div class="log-box" id="log-box">
            <div class="log-line"><span class="log-time">--:--:--</span> <span class="log-info">Gotowy do pracy. Kliknij "Rozpocznij tłumaczenie".</span></div>
        </div>
    </div>

    <div class="panel">
        <h3>✅ Przetłumaczone części</h3>
        <div class="parts-list" id="parts-list">Brak</div>
    </div>

    <div class="panel" id="panel-pobierz" style="display:none">
        <h3>📥 Pobierz</h3>
        <div class="buttons">
            <button class="btn btn-success" onclick="pobierz()">⬇️ Pobierz gotowy PDF</button>
        </div>
    </div>
</div>

<script>
let timer = null;

function zmienSilnik() {
    document.getElementById('gemini-extra').style.display =
        document.getElementById('silnik').value === 'gemini' ? 'block' : 'none';
}

async function zaladujInfo() {
    const r = await fetch('/api/info');
    const d = await r.json();
    let html = '';
    if (d.pliki.length > 0) {
        html += `<div class="info-row"><span class="info-label">Plik:</span><span class="info-value">${d.pliki[0]}</span></div>`;
        html += `<div class="info-row"><span class="info-label">Stron:</span><span class="info-value">${d.total_stron}</span></div>`;
        document.getElementById('do-strony').value = d.total_stron;
        document.getElementById('do-strony').max = d.total_stron;
    } else {
        html = '<p style="color:#f55">Nie znaleziono pliku PDF!</p>';
    }
    document.getElementById('file-info').innerHTML = html;
    odswiezCzesci(d.czesci);
    if (d.plik_koncowy) document.getElementById('panel-pobierz').style.display = 'block';
}

function odswiezCzesci(czesci) {
    const el = document.getElementById('parts-list');
    el.innerHTML = czesci.length === 0
        ? '<div style="color:#666">Brak – rozpocznij tłumaczenie</div>'
        : czesci.map(c => `<div>✅ ${c}</div>`).join('');
}

async function rozpocznij() {
    const od = parseInt(document.getElementById('od-strony').value) || 1;
    const doo = parseInt(document.getElementById('do-strony').value) || 968;
    const silnik = document.getElementById('silnik').value;
    const key = document.getElementById('gemini-key').value;

    if (silnik === 'gemini' && !key) {
        alert('Wklej klucz API Gemini!');
        return;
    }

    const r = await fetch('/api/tlumacz', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({od_strony: od, do_strony: doo, silnik, gemini_key: key})
    });
    const d = await r.json();
    if (d.ok) {
        document.getElementById('btn-start').style.display = 'none';
        document.getElementById('btn-stop').style.display = 'inline-block';
        document.getElementById('panel-postep').style.display = 'block';
        timer = setInterval(odswiezPostep, 1500);
    } else {
        alert(d.blad || 'Błąd');
    }
}

async function zatrzymaj() {
    await fetch('/api/zatrzymaj', {method: 'POST'});
    document.getElementById('btn-start').style.display = 'inline-block';
    document.getElementById('btn-stop').style.display = 'none';
    if (timer) clearInterval(timer);
}

async function polacz() {
    const r = await fetch('/api/polacz', {method: 'POST'});
    const d = await r.json();
    if (d.ok) {
        alert('✅ Połączono! ' + d.stron + ' stron');
        document.getElementById('panel-pobierz').style.display = 'block';
    } else {
        alert('❌ ' + (d.blad || 'Błąd'));
    }
}

function pobierz() { window.location.href = '/api/pobierz'; }

async function odswiezPostep() {
    const r = await fetch('/api/postep');
    const d = await r.json();

    const bar = document.getElementById('progress-bar');
    bar.style.width = d.postep + '%';
    bar.textContent = d.postep + '%';

    document.getElementById('status-text').textContent = d.status;
    document.getElementById('strona-info').textContent = d.aktualna_strona + ' / ' + d.total_stron;
    document.getElementById('partia-info').textContent = d.aktualna_partia + ' / ' + d.total_partii;
    document.getElementById('komunikat').textContent = d.komunikat;

    // Logi
    const logBox = document.getElementById('log-box');
    let logHtml = '';
    for (const log of d.logi) {
        logHtml += `<div class="log-line"><span class="log-time">${log.czas}</span> <span class="log-${log.poziom}">${log.msg}</span></div>`;
    }
    logBox.innerHTML = logHtml;
    logBox.scrollTop = logBox.scrollHeight;

    // Części
    odswiezCzesci(d.czesci);

    // Koniec?
    if (d.status === 'zakończone' || d.status === 'błąd' || d.status === 'zatrzymany') {
        document.getElementById('btn-start').style.display = 'inline-block';
        document.getElementById('btn-stop').style.display = 'none';
        if (timer) clearInterval(timer);
    }
}

zaladujInfo();
</script>
</body>
</html>
"""


# === API ===

@app.route('/')
def index():
    return render_template_string(STRONA_HTML)


@app.route('/api/info')
def api_info():
    pliki = znajdz_pdf()
    total = 0
    if pliki:
        try:
            d = fitz.open(pliki[0])
            total = len(d)
            d.close()
        except:
            pass
    return jsonify({
        "pliki": pliki,
        "total_stron": total,
        "czesci": [os.path.basename(f) for f in policz_przetlumaczone()],
        "plik_koncowy": os.path.exists(PLIK_KONCOWY),
    })


@app.route('/api/tlumacz', methods=['POST'])
def api_tlumacz():
    global stan
    if stan["aktywne"]:
        return jsonify({"ok": False, "blad": "Tłumaczenie już trwa!"})

    pliki = znajdz_pdf()
    if not pliki:
        return jsonify({"ok": False, "blad": "Brak pliku PDF"})

    dane = request.json or {}
    od = dane.get("od_strony", 1)
    do = dane.get("do_strony", 968)
    silnik = dane.get("silnik", "google")
    key = dane.get("gemini_key", "")

    # Reset
    stan["postep"] = 0
    stan["status"] = "tłumaczę"
    stan["komunikat"] = "Rozpoczynam..."
    stan["aktualna_strona"] = 0
    stan["aktualna_partia"] = 0
    logi.clear()
    dodaj_log("Uruchamiam tłumaczenie...")

    t = threading.Thread(target=tlumacz_w_tle, args=(pliki[0], od, do, silnik, key))
    t.daemon = True
    t.start()

    return jsonify({"ok": True})


@app.route('/api/zatrzymaj', methods=['POST'])
def api_zatrzymaj():
    stan["aktywne"] = False
    dodaj_log("Zatrzymywanie...", "warn")
    return jsonify({"ok": True})


@app.route('/api/postep')
def api_postep():
    return jsonify({
        "postep": stan["postep"],
        "status": stan["status"],
        "komunikat": stan["komunikat"],
        "aktualna_strona": stan["aktualna_strona"],
        "total_stron": stan["total_stron"],
        "aktualna_partia": stan["aktualna_partia"],
        "total_partii": stan["total_partii"],
        "logi": list(logi),
        "czesci": [os.path.basename(f) for f in policz_przetlumaczone()],
    })


@app.route('/api/polacz', methods=['POST'])
def api_polacz():
    pliki = policz_przetlumaczone()
    if not pliki:
        return jsonify({"ok": False, "blad": "Brak części do połączenia"})

    try:
        wynik = fitz.open()
        for p in pliki:
            c = fitz.open(p)
            wynik.insert_pdf(c)
            c.close()
        wynik.save(PLIK_KONCOWY, garbage=4, deflate=True, clean=True)
        stron = wynik.page_count
        wynik.close()
        dodaj_log(f"✅ Połączono {len(pliki)} części → {PLIK_KONCOWY} ({stron} stron)")
        return jsonify({"ok": True, "plik": PLIK_KONCOWY, "stron": stron})
    except Exception as e:
        return jsonify({"ok": False, "blad": str(e)})


@app.route('/api/pobierz')
def api_pobierz():
    if os.path.exists(PLIK_KONCOWY):
        return send_file(os.path.abspath(PLIK_KONCOWY), as_attachment=True, download_name=PLIK_KONCOWY)
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
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    app.run(host="0.0.0.0", port=5000, debug=False)
