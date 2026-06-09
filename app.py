import subprocess
import sys
from flask import Flask, request, jsonify, render_template
from config import load_settings, save_settings, build_system_prompt
from ai_client import analyze_book
from image_host import upload_image
from ebay_csv import append_listing, DEFAULT_FILENAME

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

def create_app(config_path: str = "config.json") -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

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
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"KI-Fehler: {e}"}), 502
        return jsonify(book.model_dump())

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
    app = create_app()
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
