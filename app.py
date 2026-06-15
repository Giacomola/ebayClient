import base64
import subprocess
import sys
import anthropic
from flask import Flask, request, jsonify, render_template
from config import (load_settings, save_settings, build_system_prompt,
                    ensure_anweisungen)
from ai_client import analyze_book
from price_analysis import analyze_price
from image_host import upload_image
from ebay_csv import append_listing, DEFAULT_FILENAME
from draft import load_draft, update_fields, update_images, clear_draft

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
        update_images(images, draft_path)
        return jsonify({"ok": True, "count": len(images)})

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

    @app.post("/api/generate")
    def generate():
        settings = load_settings(config_path)
        if not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "Keine Fotos ausgewählt."}), 400
        images = [f.read() for f in files]
        try:
            book = analyze_book(images, api_key=settings["anthropic_api_key"],
                                model=settings["model"],
                                prompt=build_system_prompt(settings))
        except anthropic.AuthenticationError:
            return jsonify({"error": "Der Anthropic-API-Schlüssel fehlt oder ist "
                                     "ungültig. Bitte in den Einstellungen den richtigen "
                                     "Schlüssel eintragen (er beginnt mit „sk-ant-“)."}), 401
        except anthropic.APIConnectionError:
            return jsonify({"error": "Keine Verbindung zu den KI-Servern. Bitte die "
                                     "Internetverbindung prüfen und erneut versuchen."}), 503
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                # 5xx = Server überlastet/kurz weg. Kein Code-Fehler.
                return jsonify({"error": "Die KI-Server sind gerade überlastet oder kurz "
                                         "nicht erreichbar. Bitte ein paar Sekunden warten "
                                         "und erneut auf „Anzeige erstellen“ klicken."}), 503
            return jsonify({"error": f"KI-Fehler ({e.status_code}): {e.message}"}), 502
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"KI-Fehler: {e}"}), 502
        return jsonify(book.model_dump())

    @app.post("/api/price")
    def price():
        settings = load_settings(config_path)
        if not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        data = request.get_json(force=True) or {}
        try:
            result = analyze_price(
                api_key=settings["anthropic_api_key"], model=settings["model"],
                author=data.get("author", ""), book_title=data.get("book_title", ""),
                title=data.get("title", ""), language=data.get("language", ""),
                publication_year=data.get("publication_year", ""),
                publisher=data.get("publisher", ""), book_format=data.get("book_format", ""))
        except anthropic.AuthenticationError:
            return jsonify({"error": "Der Anthropic-API-Schlüssel fehlt oder ist "
                                     "ungültig."}), 401
        except anthropic.APIConnectionError:
            return jsonify({"error": "Keine Verbindung zu den KI-Servern. Bitte die "
                                     "Internetverbindung prüfen."}), 503
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                return jsonify({"error": "Die KI-Server sind gerade überlastet. Bitte "
                                         "kurz warten und erneut versuchen."}), 503
            return jsonify({"error": f"KI-Fehler ({e.status_code}): {e.message}"}), 502
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return jsonify({"error": f"Preis-Recherche fehlgeschlagen: {e}"}), 502
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

if __name__ == "__main__":
    import webbrowser
    # Port 5050 statt 5000: 5000 ist unter macOS oft vom AirPlay-Empfänger belegt.
    app = create_app()
    webbrowser.open("http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)
