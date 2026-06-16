"""Selbst-Aktualisierung des Buch-Anzeigen-Helfers.

Lädt den aktuellen Stand als ZIP vom öffentlichen GitHub-Repo, ersetzt die
Code-Dateien im Projektordner und frischt die Pakete auf. Private Daten und
Anpassungen bleiben unberührt (siehe GESCHUETZT_*). Vor dem Überschreiben wird
eine Sicherung angelegt; schlägt etwas fehl, wird automatisch zurückgerollt.

Bewusst ohne Zusatzpakete (nur Standardbibliothek), damit das Update auch dann
läuft, wenn die Paket-Installation gerade nicht möglich ist."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

REPO_ZIP = "https://github.com/Giacomola/ebayClient/archive/refs/heads/{branch}.zip"

# Diese Dateien werden NIE überschrieben (private Daten bzw. eigene Anpassungen).
GESCHUETZT_DATEIEN = {"config.json", "draft.json", "anweisungen.txt"}
# Diese Ordner werden beim Kopieren komplett übersprungen.
GESCHUETZT_ORDNER = {".venv", "cases", "logs", ".git", ".update-backups", "__pycache__"}

BACKUP_ORDNER = ".update-backups"


def _ist_geschuetzt(relpath: str) -> bool:
    """True, wenn dieser (relative) Pfad nicht angefasst werden darf."""
    rel = relpath.replace("\\", "/").strip("/")
    if not rel:
        return False
    erste = rel.split("/")[0]
    if erste in GESCHUETZT_ORDNER:
        return True
    return rel in GESCHUETZT_DATEIEN


def apply_update(project_dir: str, source_root: str) -> int:
    """Kopiert alle Dateien aus source_root über project_dir – ohne geschützte
    Dateien/Ordner und ohne vorhandene Dateien zu löschen (nur überschreiben/neu).

    Legt vorher eine Sicherung der zu ändernden Dateien an. Tritt ein Fehler auf,
    wird der vorherige Stand wiederhergestellt (Rollback) und der Fehler erneut
    ausgelöst. Gibt die Anzahl geschriebener Dateien zurück."""
    backup_basis = os.path.join(project_dir, BACKUP_ORDNER)
    # Nur die jeweils letzte Sicherung behalten – alte vorher wegräumen.
    shutil.rmtree(backup_basis, ignore_errors=True)
    backup_root = os.path.join(backup_basis, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(backup_root, exist_ok=True)

    aktionen = []   # ("restore", rel) = alte Datei zurückspielen; ("delete", rel) = neue löschen
    count = 0
    try:
        for root, dirs, files in os.walk(source_root):
            rel_dir = os.path.relpath(root, source_root)
            rel_dir = "" if rel_dir == "." else rel_dir
            # Geschützte Unterordner gar nicht erst betreten.
            dirs[:] = [d for d in dirs
                       if not _ist_geschuetzt(os.path.join(rel_dir, d) if rel_dir else d)]
            for fn in files:
                rel = os.path.join(rel_dir, fn) if rel_dir else fn
                if _ist_geschuetzt(rel):
                    continue
                ziel = os.path.join(project_dir, rel)
                quelle = os.path.join(root, fn)
                if os.path.exists(ziel):
                    bpath = os.path.join(backup_root, rel)
                    os.makedirs(os.path.dirname(bpath) or ".", exist_ok=True)
                    shutil.copy2(ziel, bpath)
                    aktionen.append(("restore", rel))
                else:
                    aktionen.append(("delete", rel))
                os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
                shutil.copy2(quelle, ziel)
                count += 1
        return count
    except Exception:
        # Rollback: in umgekehrter Reihenfolge zurückspielen bzw. neu Erstelltes löschen.
        for art, rel in reversed(aktionen):
            ziel = os.path.join(project_dir, rel)
            if art == "restore":
                try:
                    shutil.copy2(os.path.join(backup_root, rel), ziel)
                except OSError:
                    pass
            else:
                try:
                    os.remove(ziel)
                except OSError:
                    pass
        raise


def _download(url: str, dest: str) -> None:
    """Lädt eine Datei herunter (nur Standardbibliothek)."""
    with urllib.request.urlopen(url, timeout=60) as antwort, open(dest, "wb") as f:
        shutil.copyfileobj(antwort, f)


def run_update(project_dir: str, branch: str = "main") -> dict:
    """Führt die komplette Aktualisierung durch: herunterladen → entpacken →
    (mit Sicherung) überschreiben → Pakete auffrischen.

    Gibt {"updated": Anzahl, "pip_ok": bool} zurück. Bei einem Fehler wird eine
    Ausnahme ausgelöst (Aufrufer wandelt sie in eine verständliche Meldung)."""
    tmp = tempfile.mkdtemp(prefix="bah-update-")
    try:
        zip_path = os.path.join(tmp, "update.zip")
        _download(REPO_ZIP.format(branch=branch), zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(tmp)
        unter = [d for d in os.listdir(tmp)
                 if os.path.isdir(os.path.join(tmp, d))]
        if not unter:
            raise RuntimeError("Das Update-Paket hat einen unerwarteten Aufbau.")
        source_root = os.path.join(tmp, unter[0])
        count = apply_update(project_dir, source_root)
        # Pakete auffrischen – best effort, ein Fehler hier bricht das Update nicht ab.
        pip_ok = True
        req = os.path.join(project_dir, "requirements.txt")
        if os.path.exists(req):
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                                "-r", req], check=True, timeout=300)
            except Exception:  # noqa: BLE001
                pip_ok = False
        return {"updated": count, "pip_ok": pip_ok}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
