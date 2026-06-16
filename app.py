import base64
import os
import subprocess
import sys
import anthropic
import anweisungen
from flask import Flask, request, jsonify, render_template
from config import (load_settings, save_settings, build_system_prompt,
                    ensure_anweisungen)
from ai_client import analyze_book
from price_analysis import analyze_price
from web_ai import chat
from derive_instructions import derive_from_example
from image_host import upload_image
from ebay_csv import (append_listing, entry_exists, remove_listing, title_for,
                      recent_listings, listing_stats, list_archives,
                      archive_as_file, set_action_all, DEFAULT_FILENAME)
from draft import (load_draft, update_fields, update_images, clear_draft,
                   save_draft, mark_completed, update_price_result, EMPTY)
from cases import (list_cases, save_case, load_case, delete_case,
                   find_csv_case_id, case_status, set_case_status,
                   delete_in_csv_cases)

# Port, auf dem das Programm läuft (auch in der Handy-Adresse verwendet).
PORT = 5050

# Anzeige-Version oben im Kopf (z. B. „v1.0"). Bei einer Veröffentlichung hochzählen.
APP_VERSION = "1.0"

# Anzeigenamen der Chat-Modelle, damit sich die KI mit ihrem Namen vorstellen kann.
CHAT_MODELLNAMEN = {
    "claude-haiku-4-5": "Haiku",
    "claude-sonnet-4-6": "Sonnet",
    "claude-opus-4-8": "Opus",
}

def _has_content(draft: dict) -> bool:
    """True, wenn der Fall etwas enthält (mindestens ein Foto oder ein gefülltes Feld)."""
    if draft.get("images"):
        return True
    return any(isinstance(v, str) and v.strip()
               for v in draft.get("fields", {}).values())

# Die 10 Anzeige-Felder eines Falls (genau die, die in die CSV einfließen).
CASE_FIELDS = ("title", "author", "book_title", "language", "publisher",
               "publication_year", "book_format", "description",
               "price", "condition_id")

def _data_url_bytes(data_url: str) -> bytes:
    """Holt die rohen Bilddaten aus einem gespeicherten data:-URL zurück."""
    komma = data_url.find(",")
    return base64.standard_b64decode(data_url[komma + 1:])

def _append_from_fields(folder, fields, picture_urls, settings):
    """Schreibt eine Anzeige aus einem Feld-Wörterbuch in die Sammeldatei
    (gleiche Logik wie beim normalen Erstellen). Gibt (Pfad, Anzahl) zurück."""
    aktion = "Add" if settings.get("upload_action") == "add" else "Draft"
    return append_listing(
        folder, action=aktion,
        title=fields.get("title", ""), author=fields.get("author", ""),
        book_title=fields.get("book_title", ""), language=fields.get("language", ""),
        description=fields.get("description", ""), price=fields.get("price", ""),
        condition_id=fields.get("condition_id", ""), picture_urls=picture_urls,
        publisher=fields.get("publisher", ""),
        publication_year=fields.get("publication_year", ""),
        book_format=fields.get("book_format", ""),
        location=settings["location"], shipping_service=settings["shipping_service"],
        shipping_cost=settings["shipping_cost"],
        dispatch_time_max=settings["dispatch_time_max"])

def _handy_qr_svg(url: str) -> str:
    """Erzeugt einen QR-Code als SVG-Text (skaliert sauber, braucht kein Pillow).
    Bei einem Fehler kommt ein leerer String zurück (QR ist Komfort, kein Muss)."""
    try:
        import io
        import qrcode
        import qrcode.image.svg
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception:  # noqa: BLE001
        return ""

def _ki_fehlerantwort(e: Exception, *, kontext: str = "KI-Fehler"):
    """Wandelt eine Ausnahme aus einem KI-Aufruf in eine verständliche Meldung
    (JSON + HTTP-Status) um. So sehen alle KI-Routen dieselben klaren Texte."""
    if isinstance(e, anthropic.AuthenticationError):
        return jsonify({"error": "Der Anthropic-API-Schlüssel fehlt oder ist "
                                 "ungültig. Bitte in den Einstellungen den richtigen "
                                 "Schlüssel eintragen (er beginnt mit „sk-ant-“)."}), 401
    if isinstance(e, anthropic.APIConnectionError):
        return jsonify({"error": "Keine Verbindung zu den KI-Servern. Bitte die "
                                 "Internetverbindung prüfen und erneut versuchen."}), 503
    if isinstance(e, anthropic.RateLimitError):
        # 429 = zu viele/zu große Anfragen in kurzer Zeit (Token-Limit pro Minute).
        return jsonify({"error": "Das Anfrage-Limit ist erreicht (zu viele Token in "
                                 "kurzer Zeit). Bitte ein bis zwei Minuten warten und "
                                 "es dann erneut versuchen."}), 429
    if isinstance(e, anthropic.APIStatusError):
        msg = (getattr(e, "message", "") or "").lower()
        # 400 mit Hinweis auf zu viele Token / zu langen Text = Eingabe zu groß.
        if e.status_code == 400 and any(w in msg for w in
                ("token", "too long", "context", "prompt is too long")):
            return jsonify({"error": "Die Anfrage ist zu groß für die KI (Token-Limit "
                                     "erreicht). Bitte weniger oder kleinere Fotos "
                                     "verwenden und es erneut versuchen."}), 413
        if e.status_code >= 500:
            # 5xx = Server überlastet/kurz weg. Kein Code-Fehler.
            return jsonify({"error": "Die KI-Server sind gerade überlastet oder kurz "
                                     "nicht erreichbar. Bitte ein paar Sekunden warten "
                                     "und es erneut versuchen."}), 503
        return jsonify({"error": f"KI-Fehler ({e.status_code}): {e.message}"}), 502
    return jsonify({"error": f"{kontext}: {e}"}), 502

def _chat_wissen() -> str:
    """Liest das App-Wissen für das Fragen-Fenster aus chat_wissen.txt (neben app.py).
    Fehlt die Datei, kommt ein leerer Text zurück – der Chat funktioniert dann ohne
    Spezialwissen weiter, statt abzubrechen."""
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_wissen.txt")
    try:
        with open(pfad, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""

def _chat_kontext(folder: str, cases_dir: str) -> str:
    """Fasst die aktuell gespeicherten Einträge zusammen (offene Fälle, Anzeigen in
    der Sammeldatei, Archiv), damit der Chat konkrete Fragen dazu beantworten kann.
    Bewusst kurz gehalten (höchstens je 50 Einträge)."""
    from datetime import datetime

    def datum(ts):
        try:
            return datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
        except Exception:  # noqa: BLE001
            return "unbekannt"

    def eur(x):
        return f"{x:.2f}".replace(".", ",") + " EUR"

    offen = list_cases(cases_dir, status="offen")
    zeilen = ["== AKTUELLER STAND DER GESPEICHERTEN EINTRÄGE ==",
              "Beantworte konkrete Fragen zu Fällen, Sammeldatei und Archiv anhand "
              "dieser Liste – sie ist der aktuelle Stand auf diesem Computer.",
              f"\nOffene Fälle (begonnen, noch nicht in der Sammeldatei): {len(offen)}"]
    for c in offen[:50]:
        zeilen.append(f"- {c['name']} – {c['photo_count']} Foto(s) – begonnen am {datum(c['saved_at'])}")

    if not folder:
        zeilen.append("\nSammeldatei und Archiv: noch kein Speicherordner gewählt.")
        return "\n".join(zeilen)

    stats = listing_stats(folder)
    zeilen.append(f"\nAnzeigen in der aktuellen Sammeldatei: {stats['count']} Stück, "
                  f"Summe der Startpreise {eur(stats['total'])}")
    for r in recent_listings(folder, limit=50):
        teil = f"- {r.get('title', '')}"
        if (r.get("author") or "").strip():
            teil += f" – {r['author'].strip()}"
        if (r.get("price") or "").strip():
            teil += f" – {r['price'].strip()} EUR"
        zeilen.append(teil)

    archive = list_archives(folder)
    zeilen.append(f"\nArchivierte Sammeldateien: {len(archive)}")
    for a in archive[:50]:
        zeilen.append(f"- {a['filename']} – {a['count']} Anzeigen – Summe {eur(a['total'])}")
    return "\n".join(zeilen)

def _open_in_os(path: str) -> None:
    """Öffnet eine Datei im Standardprogramm des Betriebssystems.

    Wirft eine Ausnahme, wenn das Öffnen fehlschlägt (die Aufrufer fangen sie ab)."""
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", path], check=False)

def _pick_folder_dialog() -> str:
    """Öffnet ein natives Ordner-Auswahlfenster und gibt den gewählten Pfad zurück.

    Läuft in einem eigenen Prozess, damit es das Flask-Fenster/den Hauptthread
    nicht stört. Leerer String = abgebrochen."""
    script = (
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
        "print(filedialog.askdirectory(title='Speicherordner für eBay-Dateien'))\n"
    )
    try:
        out = subprocess.run([sys.executable, "-c", script],
                             capture_output=True, text=True, timeout=180)
        return out.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""

def create_app(config_path: str = "config.json",
               draft_path: str = "draft.json",
               cases_dir: str = "cases") -> Flask:
    app = Flask(__name__)
    # Statische Dateien (app.js/style.css) nicht im Browser zwischenspeichern, damit
    # nach einem Update ein normales Neuladen reicht (sonst läuft veralteter Code).
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    # Seitenvorlage (index.html) bei Änderung automatisch neu einlesen, damit nach
    # einem Update ein normales Neuladen reicht – ohne das Programm neu zu starten.
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    ensure_anweisungen(config_path)  # anweisungen.txt anlegen, falls sie fehlt

    @app.get("/")
    def index():
        # mtime von app.js/style.css als Cache-Kennung an die Datei-Links hängen
        # (?v=…), damit der Browser nach jeder Änderung automatisch die neue Datei
        # lädt. Im Kopf angezeigt wird die App-Version (z. B. v1.0).
        ver = 0
        for name in ("app.js", "style.css"):
            try:
                ver = max(ver, int(os.path.getmtime(os.path.join(app.static_folder, name))))
            except OSError:
                pass
        return render_template("index.html", asset_ver=ver, app_version=APP_VERSION)

    @app.get("/api/draft")
    def get_draft():
        return jsonify(load_draft(draft_path))

    @app.post("/api/draft")
    def post_draft():
        data = request.get_json(force=True)
        update_fields(data.get("fields", {}),
                      bool(data.get("result_visible", False)), draft_path)
        return jsonify({"ok": True})

    @app.post("/api/draft/price")
    def post_draft_price():
        """Speichert das Preis-Recherche-Ergebnis, damit der Preis-Kasten erhalten bleibt."""
        data = request.get_json(force=True) or {}
        update_price_result(data.get("price_result"), draft_path)
        return jsonify({"ok": True})

    @app.post("/api/draft/images")
    def post_draft_images():
        images = []
        for f in request.files.getlist("images"):
            raw = f.read()
            media_type = "image/png" if raw[:8].startswith(b"\x89PNG") else "image/jpeg"
            data_url = f"data:{media_type};base64," + \
                base64.standard_b64encode(raw).decode("ascii")
            images.append({"media_type": media_type, "data_url": data_url})
        d = update_images(images, draft_path)
        return jsonify({"ok": True, "count": len(images),
                        "images_rev": d.get("images_rev", 0)})

    @app.get("/api/draft/images-rev")
    def draft_images_rev():
        """Leichte Abfrage: nur die Foto-Versionsnummer (für die Live-Aktualisierung)."""
        d = load_draft(draft_path)
        return jsonify({"images_rev": d.get("images_rev", 0),
                        "count": len(d.get("images", []))})

    @app.post("/api/draft/clear")
    def post_draft_clear():
        # „Neuen Fall starten": einen offenen Fall mit Inhalt zuerst parken
        # (in die Liste „Aktive Fälle"), damit keine unfertige Arbeit verloren geht.
        d = load_draft(draft_path)
        parked = False
        if _has_content(d) and not d.get("completed"):
            save_case(d, cases_dir)
            parked = True
        clear_draft(draft_path)
        return jsonify({"ok": True, "parked": parked})

    @app.get("/api/cases")
    def get_cases():
        """Liste der Fälle zum Wiederaufnehmen (nur offene, noch nicht abgesendete)."""
        return jsonify({"cases": list_cases(cases_dir, status="offen")})

    @app.post("/api/cases/<case_id>/open")
    def open_case(case_id):
        status = case_status(case_id, cases_dir)
        target = load_case(case_id, cases_dir)
        if target is None:
            return jsonify({"error": "Fall nicht gefunden."}), 404
        cur = load_draft(draft_path)
        if _has_content(cur) and not cur.get("completed"):
            save_case(cur, cases_dir)   # aktuellen offenen Fall nicht verlieren
        new_draft = dict(EMPTY)
        new_draft["fields"] = target.get("fields", {})
        new_draft["images"] = target.get("images", [])
        new_draft["result_visible"] = target.get("result_visible", False)
        new_draft["price_result"] = target.get("price_result")   # Preis-Ergebnis mitnehmen
        new_draft["images_rev"] = int(cur.get("images_rev", 0))  # Zähler nicht zurückwerfen
        save_draft(new_draft, draft_path)
        # Einen offenen (geparkten) Fall „verbraucht" das Öffnen → löschen. Einen
        # „in Sammeldatei"-Fall behalten: er bleibt der bearbeitbare CSV-Datensatz.
        if status != "in_csv":
            delete_case(case_id, cases_dir)
        return jsonify({"ok": True})

    def _remove_csv_row(case_id):
        """Entfernt die CSV-Zeile eines „in Sammeldatei"-Falls (falls ein Ordner gesetzt
        ist). Tut nichts, wenn der Fall nicht in der CSV steht."""
        target = load_case(case_id, cases_dir) or {}
        fields = target.get("fields", {})
        folder = load_settings(config_path).get("save_folder", "")
        if folder:
            remove_listing(folder, fields.get("author", ""), fields.get("book_title", ""))

    @app.post("/api/cases/<case_id>/delete")
    def remove_case(case_id):
        # War der Fall in der Sammeldatei, auch dessen CSV-Zeile entfernen.
        if case_status(case_id, cases_dir) == "in_csv":
            _remove_csv_row(case_id)
        return jsonify({"ok": delete_case(case_id, cases_dir)})

    @app.post("/api/draft/zurueckhalten")
    def post_draft_zurueckhalten():
        """„Zurückhalten": aktuellen Entwurf fertig speichern, aber NICHT freigeben.
        Er landet als Fall mit Status „zurückgehalten" (nicht in der Upload-CSV)."""
        d = load_draft(draft_path)
        if not _has_content(d):
            return jsonify({"error": "Der Entwurf ist leer – nichts zum Zurückhalten."}), 400
        save_case(d, cases_dir, status="zurückgehalten")
        clear_draft(draft_path)
        return jsonify({"ok": True})

    @app.post("/api/cases/<case_id>/freigeben")
    def freigeben_case(case_id):
        """Gibt einen zurückgehaltenen Eintrag frei: Fotos zu imgbb hochladen, Zeile in
        die Sammeldatei schreiben, Status → in_csv."""
        if case_status(case_id, cases_dir) != "zurückgehalten":
            return jsonify({"error": "Nur zurückgehaltene Einträge können "
                                     "freigegeben werden."}), 400
        settings = load_settings(config_path)
        if not settings["imgbb_api_key"]:
            return jsonify({"error": "Kein imgbb-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        folder = settings.get("save_folder", "")
        if not folder:
            return jsonify({"error": "Kein Speicherordner gewählt. "
                                     "Bitte zuerst auf 'Ordner wählen' klicken."}), 400
        target = load_case(case_id, cases_dir) or {}
        fields = target.get("fields", {})
        images = target.get("images", [])
        if not images:
            return jsonify({"error": "Im Eintrag sind keine Fotos vorhanden."}), 400
        try:
            urls = [upload_image(_data_url_bytes(im["data_url"]),
                                 settings["imgbb_api_key"]) for im in images]
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Foto-Upload fehlgeschlagen: {e}"}), 502
        try:
            path, count = _append_from_fields(folder, fields, urls, settings)
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Datei konnte nicht gespeichert werden: {e}"}), 500
        csv_title = title_for(fields.get("title", ""))
        # Einen anderen „in Sammeldatei"-Fall mit gleichem Titel aufräumen.
        if csv_title:
            alt = find_csv_case_id(csv_title, cases_dir)
            if alt and alt != case_id:
                delete_case(alt, cases_dir)
        set_case_status(case_id, "in_csv", cases_dir, csv_title=csv_title)
        return jsonify({"ok": True, "count": count})

    @app.post("/api/cases/<case_id>/zurueckziehen")
    def zurueckziehen_case(case_id):
        """Zieht einen freigegebenen Eintrag aus der Sammeldatei zurück (Status →
        zurückgehalten); die Fotos/Felder bleiben im Fall erhalten."""
        if case_status(case_id, cases_dir) != "in_csv":
            return jsonify({"error": "Nur freigegebene Einträge können "
                                     "zurückgezogen werden."}), 400
        _remove_csv_row(case_id)
        set_case_status(case_id, "zurückgehalten", cases_dir, csv_title="")
        return jsonify({"ok": True})

    @app.post("/api/cases/<case_id>/archivieren")
    def archivieren_case(case_id):
        """Räumt einen Eintrag weg (Status → archiviert). War er freigegeben, wird
        seine CSV-Zeile entfernt – Archiviertes wird nie hochgeladen."""
        st = case_status(case_id, cases_dir)
        if st is None:
            return jsonify({"error": "Eintrag nicht gefunden."}), 404
        if st == "in_csv":
            _remove_csv_row(case_id)
        set_case_status(case_id, "archiviert", cases_dir, csv_title="")
        return jsonify({"ok": True})

    @app.post("/api/cases/<case_id>/wiederherstellen")
    def wiederherstellen_case(case_id):
        """Holt einen archivierten Eintrag zurück – als „zurückgehalten", also NICHT
        automatisch wieder in der Upload-CSV."""
        if case_status(case_id, cases_dir) != "archiviert":
            return jsonify({"error": "Nur archivierte Einträge können "
                                     "wiederhergestellt werden."}), 400
        set_case_status(case_id, "zurückgehalten", cases_dir)
        return jsonify({"ok": True})

    @app.post("/api/shutdown")
    def shutdown():
        # Beendet den lokalen Server. Erst antworten, dann beenden (kurze Verzögerung).
        import os
        import threading
        import time
        threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)),
                         daemon=True).start()
        return jsonify({"ok": True})

    @app.get("/api/settings")
    def get_settings():
        return jsonify(load_settings(config_path))

    @app.post("/api/settings")
    def post_settings():
        current = load_settings(config_path)
        current.update(request.get_json(force=True))
        save_settings(current, config_path)
        # Die aktuell eingestellte Upload-Art (Entwurf/sofort) sofort auf die ganze
        # Sammeldatei anwenden, damit sie für ALLE Einträge gilt – auch ältere.
        folder = current.get("save_folder", "")
        if folder:
            aktion = "Add" if current.get("upload_action") == "add" else "Draft"
            set_action_all(folder, aktion)
        return jsonify({"ok": True})

    @app.post("/api/apply-upload-action")
    def apply_upload_action():
        """Wendet die aktuelle Upload-Art (Entwurf/sofort) auf die ganze Sammeldatei
        an, sodass sie für ALLE Einträge gilt. Wird beim Öffnen des Upload-Fensters
        aufgerufen, damit die Datei immer der aktuellen Einstellung entspricht."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        aktion = "Add" if settings.get("upload_action") == "add" else "Draft"
        n = set_action_all(folder, aktion) if folder else 0
        return jsonify({"ok": True, "action": aktion, "count": n})

    @app.post("/api/open-anweisungen")
    def open_anweisungen():
        """Öffnet anweisungen.txt im Standard-Editor des Systems (schneller Zugriff)."""
        path = os.path.abspath(anweisungen.path_for(config_path))
        if not os.path.exists(path):
            return jsonify({"error": "anweisungen.txt wurde nicht gefunden."}), 404
        try:
            _open_in_os(path)
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Konnte die Datei nicht öffnen: {e}"}), 500
        return jsonify({"ok": True, "path": path})

    @app.get("/api/handy-zugang")
    def handy_zugang():
        """Liefert die WLAN-Adresse dieses PCs (+ QR-Code), damit ein Handy im selben
        WLAN die App öffnen und Fotos hochladen kann."""
        ip = _lan_ip()
        if not ip:
            return jsonify({"url": "", "qr_svg": "",
                            "error": "Keine Netzwerk-Adresse gefunden. Ist der PC mit "
                                     "dem Netzwerk (WLAN oder Kabel) verbunden?"})
        url = f"http://{ip}:{PORT}"
        return jsonify({"url": url, "qr_svg": _handy_qr_svg(url)})

    @app.get("/api/listings")
    def listings():
        """Liefert die zuletzt gespeicherten Anzeigen aus der Sammeldatei + Überblick.
        Pro Zeile case_id, falls ein bearbeitbarer Fall dazu vorliegt."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        rows = recent_listings(folder) if folder else []
        for r in rows:
            r["case_id"] = find_csv_case_id(r.get("title", ""), cases_dir)
        return jsonify({
            "listings": rows,
            "stats": listing_stats(folder) if folder else {"count": 0, "total": 0.0},
        })

    @app.get("/api/overview")
    def overview():
        """Alles gebündelt für das Übersicht-Fenster: Fälle in Arbeit, Anzeigen in
        der Sammeldatei (inkl. Anzahl/Summe) und archivierte Sammeldateien."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        rows = recent_listings(folder, limit=200) if folder else []
        for r in rows:
            r["case_id"] = find_csv_case_id(r.get("title", ""), cases_dir)
        return jsonify({
            "active_cases": list_cases(cases_dir, status="offen"),
            "held_cases": list_cases(cases_dir, status="zurückgehalten"),
            "archived_cases": list_cases(cases_dir, status="archiviert"),
            "listings": rows,
            "stats": listing_stats(folder) if folder else {"count": 0, "total": 0.0},
            "archives": list_archives(folder) if folder else [],
        })

    @app.post("/api/archive-file")
    def archive_file():
        """Archiviert die aktuelle Sammeldatei unter eBayClient_<Datum>[_Name].csv
        und gibt den Platz für eine frische Datei frei."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        if not folder:
            return jsonify({"error": "Kein Speicherordner gewählt."}), 400
        name = (request.get_json(silent=True) or {}).get("name", "")
        count, archive_name = archive_as_file(folder, name)
        if count == 0:
            return jsonify({"error": "Die Sammeldatei ist leer – nichts zu archivieren."}), 400
        delete_in_csv_cases(cases_dir)  # die zugehörigen bearbeitbaren Fälle sind nun archiviert
        return jsonify({"ok": True, "moved": count, "filename": archive_name})

    @app.post("/api/open-csv")
    def open_csv():
        """Öffnet die eBay-Sammeldatei im Standardprogramm (z. B. Numbers/Excel)."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        if not folder:
            return jsonify({"error": "Kein Speicherordner gewählt."}), 400
        path = os.path.join(folder, DEFAULT_FILENAME)
        if not os.path.exists(path):
            return jsonify({"error": "Die Sammeldatei wurde noch nicht erstellt."}), 404
        try:
            _open_in_os(path)
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Konnte die Datei nicht öffnen: {e}"}), 500
        return jsonify({"ok": True, "path": path})

    @app.post("/api/open-folder")
    def open_folder():
        """Öffnet den Speicherordner im Datei-Manager (Finder/Explorer), damit man die
        Sammeldatei für den eBay-Upload leicht findet."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        if not folder:
            return jsonify({"error": "Kein Speicherordner gewählt. "
                                     "Bitte zuerst auf 'Ordner wählen' klicken."}), 400
        if not os.path.isdir(folder):
            return jsonify({"error": "Der Speicherordner existiert nicht mehr."}), 404
        try:
            _open_in_os(folder)
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Konnte den Ordner nicht öffnen: {e}"}), 500
        return jsonify({"ok": True, "path": folder})

    @app.post("/api/update")
    def update_app():
        """Aktualisiert den Helfer auf den neuesten Stand von GitHub (mit Sicherung
        und automatischem Zurückrollen bei Fehlern). Danach ist ein Neustart nötig."""
        from updater import run_update
        projekt = os.path.dirname(os.path.abspath(__file__))
        try:
            ergebnis = run_update(projekt)
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return jsonify({"error": "Aktualisierung fehlgeschlagen (es wurde nichts "
                                     f"verändert): {e}"}), 502
        return jsonify({"ok": True, **ergebnis})

    @app.post("/api/generate")
    def generate():
        settings = load_settings(config_path)
        if settings["ki_backend"] != "abo" and not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "Keine Fotos ausgewählt."}), 400
        # Sicherheitsnetz: höchstens 5 Fotos analysieren (jedes Foto kostet Token).
        # Welche Fotos das sind, wählt normalerweise die Oberfläche; hier nur die Grenze.
        images = [f.read() for f in files][:5]
        try:
            book = analyze_book(images, api_key=settings["anthropic_api_key"],
                                model=settings["model_text"],
                                prompt=build_system_prompt(settings),
                                backend=settings["ki_backend"])
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return _ki_fehlerantwort(e)
        return jsonify(book.model_dump())

    @app.post("/api/price")
    def price():
        settings = load_settings(config_path)
        if settings["ki_backend"] != "abo" and not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        data = request.get_json(force=True) or {}
        try:
            result = analyze_price(
                api_key=settings["anthropic_api_key"], model=settings["model_price"],
                author=data.get("author", ""), book_title=data.get("book_title", ""),
                title=data.get("title", ""), language=data.get("language", ""),
                publication_year=data.get("publication_year", ""),
                publisher=data.get("publisher", ""), book_format=data.get("book_format", ""),
                condition=data.get("condition", ""),
                backend=settings["ki_backend"])
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return _ki_fehlerantwort(e, kontext="Preis-Recherche fehlgeschlagen")
        return jsonify(result.model_dump())

    @app.post("/api/derive-instructions")
    def derive_instructions_route():
        settings = load_settings(config_path)
        if settings["ki_backend"] != "abo" and not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        data = request.get_json(force=True) or {}
        example = (data.get("example") or "").strip()
        if not example:
            return jsonify({"error": "Bitte zuerst eine Beispiel-Beschreibung eingeben."}), 400
        try:
            result = derive_from_example(example, api_key=settings["anthropic_api_key"],
                                         model=settings["model_text"],
                                         backend=settings["ki_backend"])
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return _ki_fehlerantwort(e, kontext="Anweisungen erzeugen fehlgeschlagen")
        return jsonify(result.model_dump())

    @app.post("/api/chat")
    def chat_route():
        """Einfacher Frage-Chat (freier Text). Erwartet {messages:[{role,content}…]}
        und nutzt das eingestellte Chat-Modell (Standard Haiku)."""
        settings = load_settings(config_path)
        if settings["ki_backend"] != "abo" and not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        data = request.get_json(force=True) or {}
        messages = data.get("messages") or []
        if not messages:
            return jsonify({"error": "Keine Frage gestellt."}), 400
        # Wissen = feste App-Beschreibung + aktueller Stand der gespeicherten Einträge.
        folder = settings.get("save_folder", "")
        wissen = _chat_wissen() + "\n\n" + _chat_kontext(folder, cases_dir)
        modell = settings.get("model_chat", "claude-haiku-4-5")
        try:
            antwort = chat(api_key=settings["anthropic_api_key"], model=modell,
                           messages=messages, wissen=wissen,
                           modellname=CHAT_MODELLNAMEN.get(modell, ""),
                           backend=settings["ki_backend"])
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return _ki_fehlerantwort(e, kontext="Chat fehlgeschlagen")
        return jsonify({"answer": antwort})

    @app.post("/api/choose-folder")
    def choose_folder():
        path = _pick_folder_dialog()
        current = load_settings(config_path)
        if path:
            current["save_folder"] = path
            save_settings(current, config_path)
        return jsonify({"folder": current.get("save_folder", "")})

    @app.post("/api/create-csv")
    def create_csv():
        settings = load_settings(config_path)
        if not settings["imgbb_api_key"]:
            return jsonify({"error": "Kein imgbb-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        folder = settings.get("save_folder", "")
        if not folder:
            return jsonify({"error": "Kein Speicherordner gewählt. "
                                     "Bitte zuerst auf 'Ordner wählen' klicken."}), 400
        form = request.form
        # Schon eine Anzeige mit gleichem Autor + Buchtitel? Dann erst nachfragen
        # (noch VOR dem Foto-Upload, damit der Abbruch nichts kostet). Der Abgleich
        # läuft über Autor+Buchtitel, nicht über den Anzeigentitel.
        title = form.get("title", "")
        author = form.get("author", "")
        book_title = form.get("book_title", "")
        if form.get("overwrite") != "true" and entry_exists(folder, author, book_title):
            label = " – ".join(p for p in (book_title.strip(), author.strip()) if p) \
                or title_for(title)
            return jsonify({"duplicate": True, "title": label}), 200
        files = request.files.getlist("images")
        try:
            urls = [upload_image(f.read(), settings["imgbb_api_key"]) for f in files]
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Foto-Upload fehlgeschlagen: {e}"}), 502
        if not urls:
            return jsonify({"error": "Keine Fotos für die Anzeige vorhanden."}), 400
        # Einstellung: als Entwurf anlegen (Standard) oder sofort einstellen.
        aktion = "Add" if settings.get("upload_action") == "add" else "Draft"
        try:
            path, count = append_listing(
                folder, action=aktion,
                title=form.get("title", ""), author=form.get("author", ""),
                book_title=form.get("book_title", ""), language=form.get("language", ""),
                description=form.get("description", ""), price=form.get("price", ""),
                condition_id=form.get("condition_id", ""), picture_urls=urls,
                publisher=form.get("publisher", ""),
                publication_year=form.get("publication_year", ""),
                book_format=form.get("book_format", ""),
                location=settings["location"],
                shipping_service=settings["shipping_service"],
                shipping_cost=settings["shipping_cost"],
                dispatch_time_max=settings["dispatch_time_max"],
            )
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Datei konnte nicht gespeichert werden: {e}"}), 500
        mark_completed(draft_path)  # Fall gilt jetzt als abgeschlossen (wird nicht geparkt)
        # Den Fall als „in Sammeldatei" behalten (mit allen Feldern + Fotos), damit er
        # sich später vollständig bearbeiten lässt. Gleichen Titel vorher ersetzen.
        csv_title = title_for(form.get("title", ""))
        if csv_title:
            alt = find_csv_case_id(csv_title, cases_dir)
            if alt:
                delete_case(alt, cases_dir)
            case_fields = {k: form.get(k, "") for k in
                           ("title", "author", "book_title", "language", "publisher",
                            "publication_year", "book_format", "description",
                            "price", "condition_id")}
            d = load_draft(draft_path)
            save_case({"fields": case_fields, "images": d.get("images", []),
                       "result_visible": True},
                      cases_dir, status="in_csv", csv_title=csv_title)
        return jsonify({"ok": True, "folder": folder,
                        "filename": DEFAULT_FILENAME, "path": path, "count": count})

    return app

def _lan_ip() -> str:
    """Ermittelt die IP-Adresse dieses Rechners im lokalen Netzwerk (WLAN).

    Trick: eine UDP-Verbindung zu einer öffentlichen Adresse „vorbereiten" (es werden
    KEINE Daten gesendet) und die dabei gewählte lokale Adresse ablesen. Klappt das
    nicht (z. B. offline), wird leer zurückgegeben."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()

def _server_laeuft_schon(port: int) -> bool:
    """True, wenn auf diesem PC bereits ein Server auf dem Port antwortet.
    So starten wir keinen zweiten (konkurrierenden) Server."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()

def _zeige_handy_zugang(port: int) -> None:
    """Zeigt beim Start die Adresse fürs Handy an – und, wenn möglich, einen QR-Code
    zum Abscannen. Fehlt das QR-Paket, wird nur die Adresse angezeigt (kein Abbruch)."""
    ip = _lan_ip()
    if not ip:
        print("Hinweis: Keine Netzwerk-Adresse gefunden – das Handy kann nur im "
              "selben Netzwerk (WLAN oder Kabel am selben Router) zugreifen.")
        return
    url = f"http://{ip}:{port}"
    print("\n" + "=" * 52)
    print("  AUF DEM HANDY (gleiches Netzwerk) DIESE ADRESSE OEFFNEN:")
    print(f"  {url}")
    print("  Tipp: einfach den QR-Code unten mit der Handy-Kamera scannen.")
    print("=" * 52)
    try:
        import qrcode
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)
    except Exception:  # noqa: BLE001 - QR ist Komfort, kein Muss
        print("(Kein QR-Code verfügbar – bitte die Adresse oben am Handy eintippen.)")
    print()

def _browserfenster_nach_vorne() -> bool:
    """Bestmöglich: holt das bereits offene Helfer-Fenster im Browser nach vorne,
    erkannt am Fenstertitel „Buch-Anzeigen-Helfer". Gibt True zurück, wenn ein
    passendes Fenster gefunden und nach vorne geholt wurde – sonst False (dann öffnet
    der Aufrufer ersatzweise ein Tab). Wirft nie einen Fehler nach außen.

    macOS fragt beim ersten Mal nach der Erlaubnis „Bedienungshilfen" (Accessibility);
    Windows braucht keine Erlaubnis (eingebautes AppActivate)."""
    import subprocess
    titel = "Buch-Anzeigen-Helfer"
    try:
        if sys.platform == "darwin":
            # System Events sucht ein sichtbares Fenster mit diesem Titel und hebt es an.
            applescript = (
                'tell application "System Events"\n'
                ' set ok to false\n'
                ' repeat with p in (processes whose background only is false)\n'
                '  try\n'
                '   repeat with w in windows of p\n'
                f'    if name of w contains "{titel}" then\n'
                '     set frontmost of p to true\n'
                '     try\n perform action "AXRaise" of w\n end try\n'
                '     set ok to true\n exit repeat\n'
                '    end if\n'
                '   end repeat\n'
                '  end try\n'
                '  if ok then exit repeat\n'
                ' end repeat\n'
                ' if ok then return "OK"\n'
                ' return "NO"\n'
                'end tell'
            )
            out = subprocess.run(["osascript", "-e", applescript],
                                 capture_output=True, text=True, timeout=5)
            return out.stdout.strip() == "OK"
        if sys.platform.startswith("win"):
            # AppActivate holt ein Fenster anhand des (Anfangs vom) Titel nach vorne.
            ps = ("$ws = New-Object -ComObject WScript.Shell\n"
                  f"if ($ws.AppActivate('{titel}')) {{ 'OK' }} else {{ 'NO' }}")
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=8)
            return "OK" in out.stdout
    except Exception:  # noqa: BLE001 - Fokus ist Komfort, kein Muss
        return False
    return False

if __name__ == "__main__":
    import webbrowser
    # Port 5050 statt 5000: 5000 ist unter macOS oft vom AirPlay-Empfänger belegt.
    # Einzelinstanz: Läuft schon ein Server auf diesem PC, KEINEN zweiten starten.
    # Statt ein zweites Tab zu öffnen, holen wir das schon offene Fenster nach vorne;
    # klappt das nicht, öffnen wir ersatzweise wie bisher ein Tab.
    if _server_laeuft_schon(PORT):
        if _browserfenster_nach_vorne():
            print("Das Programm läuft bereits – ich habe das offene Fenster nach vorne geholt.")
        else:
            print("Das Programm läuft bereits – ich öffne nur das Fenster.")
            webbrowser.open(f"http://127.0.0.1:{PORT}")
        sys.exit(0)
    app = create_app()
    _zeige_handy_zugang(PORT)
    webbrowser.open(f"http://127.0.0.1:{PORT}")  # öffnet das Programm auf DIESEM PC
    # host="0.0.0.0": auch von anderen Geräten im selben WLAN erreichbar (z. B. Handy
    # zum Fotografieren). threaded=True: mehrere Anfragen gleichzeitig, sonst friert
    # die Seite während der ~1-minütigen Anzeige-Erstellung ein.
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
