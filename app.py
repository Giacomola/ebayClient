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
from derive_instructions import derive_from_example
from image_host import upload_image
from ebay_csv import (append_listing, title_exists, title_for,
                      recent_listings, archive_as_file, DEFAULT_FILENAME)
from draft import load_draft, update_fields, update_images, clear_draft

# Port, auf dem das Programm läuft (auch in der Handy-Adresse verwendet).
PORT = 5050

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
               draft_path: str = "draft.json") -> Flask:
    app = Flask(__name__)
    ensure_anweisungen(config_path)  # anweisungen.txt anlegen, falls sie fehlt

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/draft")
    def get_draft():
        return jsonify(load_draft(draft_path))

    @app.post("/api/draft")
    def post_draft():
        data = request.get_json(force=True)
        update_fields(data.get("fields", {}),
                      bool(data.get("result_visible", False)), draft_path)
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
        clear_draft(draft_path)
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
        return jsonify({"ok": True})

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
        """Liefert die zuletzt gespeicherten Anzeigen aus der Sammeldatei."""
        settings = load_settings(config_path)
        folder = settings.get("save_folder", "")
        return jsonify({"listings": recent_listings(folder) if folder else []})

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

    @app.post("/api/generate")
    def generate():
        settings = load_settings(config_path)
        if settings["ki_backend"] != "abo" and not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "Keine Fotos ausgewählt."}), 400
        images = [f.read() for f in files]
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
        # Gibt es schon eine Anzeige mit gleichem Titel? Dann erst nachfragen
        # (noch VOR dem Foto-Upload, damit der Abbruch nichts kostet).
        title = form.get("title", "")
        if form.get("overwrite") != "true" and title_exists(folder, title):
            return jsonify({"duplicate": True, "title": title_for(title)}), 200
        files = request.files.getlist("images")
        try:
            urls = [upload_image(f.read(), settings["imgbb_api_key"]) for f in files]
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Foto-Upload fehlgeschlagen: {e}"}), 502
        if not urls:
            return jsonify({"error": "Keine Fotos für die Anzeige vorhanden."}), 400
        try:
            path, count = append_listing(
                folder,
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

if __name__ == "__main__":
    import webbrowser
    # Port 5050 statt 5000: 5000 ist unter macOS oft vom AirPlay-Empfänger belegt.
    app = create_app()
    _zeige_handy_zugang(PORT)
    webbrowser.open(f"http://127.0.0.1:{PORT}")  # öffnet das Programm auf DIESEM PC
    # host="0.0.0.0": auch von anderen Geräten im selben WLAN erreichbar (z. B. Handy
    # zum Fotografieren). threaded=True: mehrere Anfragen gleichzeitig, sonst friert
    # die Seite während der ~1-minütigen Anzeige-Erstellung ein.
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
