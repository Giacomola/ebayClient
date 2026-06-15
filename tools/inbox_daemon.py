#!/usr/bin/env python3
"""INBOX-Daemon (smart): sortiert beim Speichern automatisch in den Backlog.

Beobachtet `INBOX.md` ereignisgesteuert (watchdog/FSEvents, kein Pollen). Bei jedem
Speichern wird – falls der Abschnitt `### Push` Einträge enthält (Tab-Unterüber-
schriften `# Eingabe/Fotos`/`# KI-Anzeigentext`/… geben den Ziel-Tab) – ein Headless-
`claude` (günstiges Haiku-Modell) gestartet, der die Einträge in die passenden
BACKLOG-Tabs sortiert. `claude` rührt INBOX NICHT an. `### Keep` bleibt liegen.

**Verlustsichere Reihenfolge:** (1) claude sortiert → BACKLOG, (2) Daemon committet
BACKLOG (Einträge jetzt sicher), (3) ERST DANACH leert der Daemon genau die
übertragenen Zeilen aus INBOX und committet das. Ein Abbruch vor Schritt 2 lässt
INBOX unangetastet → nichts verloren; ein Abbruch zwischen 2 und 3 erzeugt höchstens
ein Duplikat (Eintrag in BACKLOG *und* INBOX), nie einen Verlust.
`claude` bekommt nur Datei-Edit-Rechte (`acceptEdits`), kein Bash, kein „alles erlauben".

Sicherheits-/Verhaltensgrenzen:
- `claude` ändert NUR die zwei md-Dateien (Prompt + acceptEdits, im Repo).
- KEINE Code-Änderung, KEINE Aufgabe wird gestartet (das macht ein interaktiver Agent).
- Entprellt: mehrere Save-Events → ein Lauf. Lock serialisiert Läufe.

Start:  .venv/bin/python tools/inbox_daemon.py   (oder start-inbox-daemon.command)
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INBOX = REPO / "INBOX.md"
LOG = REPO / "logs" / "inbox_daemon.log"
MODEL = "claude-haiku-4-5-20251001"   # günstig/schnell, reicht zum Sortieren
DEBOUNCE_S = 2.0

PROMPT = (
    'In INBOX.md gibt es einen Abschnitt "### Push" (darunter Tab-Unterüberschriften '
    'wie "# Eingabe/Fotos", "# KI-Anzeigentext", …) und einen Abschnitt "### Keep". '
    'Sortiere ALLE Einträge unter "### Push" in die passenden Tabs von BACKLOG.md — die '
    '"# …"-Unterüberschrift gibt den Ziel-Tab an, sonst aus Text/Architektur erraten — als '
    '"- [ ] <Text>  `→ <datei>`" (Regeln: CLAUDE.md → "Backlog-Workflow"). '
    'WICHTIG: Ändere NUR BACKLOG.md — INBOX.md NICHT anfassen (das Leeren übernimmt der '
    'Daemon). Lasse "### Keep" außer Acht. KEIN Code, KEINE Aufgabe, KEIN Commit.'
)

_lock = threading.Lock()


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def notify(text: str, title: str = "INBOX-Daemon") -> None:
    """Kurze macOS-Mitteilung (best effort). Schlägt sie fehl, stört das nichts."""
    safe = text.replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{safe}" with title "{title}"'],
            capture_output=True, timeout=10)
    except Exception:
        pass


def push_entries() -> list[str]:
    """Einträge unter '### Push' (bis '### Keep'/Ende). Tab-Unterüberschriften (# …),
    Leerzeilen, kursive Beschreibungen (_..._) und Trennlinien (---) zählen nicht."""
    if not INBOX.exists():
        return []
    out, in_push = [], False
    for ln in INBOX.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("###"):
            in_push = "push" in s.lower()   # '### Push' an, '### Keep'/andere aus
            continue
        if in_push and s and not s.startswith("#") and not s.startswith("_") and s != "---":
            out.append(s)
    return out


def _clean_push_text(text: str, entries: list[str]) -> str:
    """Übertragene Zeilen aus '### Push' entfernen und das Layout wiederherstellen.

    Es werden ganze Zeilen entfernt (nicht nur deren Text), Mehrfach-Leerzeilen zu
    einer zusammengefasst UND vor jeder Überschrift im Push-Bereich genau eine
    Leerzeile sichergestellt — so kleben nach dem Entfernen eines Eintrags, der
    direkt zwischen zwei Überschriften stand, die Überschriften nicht aneinander,
    und der Posteingang sieht wieder aus wie das leere Ausgangs-Layout.

    Nur exakt diese Einträge werden entfernt — neu hinzugekommene Zeilen bleiben für
    den nächsten Lauf. '### Keep' (inkl. dessen Leerzeilen) bleibt unangetastet.
    """
    targets = set(entries)
    trailing_nl = text.endswith("\n")
    out: list[str] = []
    in_push = False
    for ln in text.split("\n"):
        s = ln.strip()
        is_section = s.startswith("###")     # '### Push' / '### Keep'
        is_heading = s.startswith("#")        # Tab-Überschrift (##) oder Sektion (###)
        if in_push and not is_section:
            if s in targets:
                continue                      # genau diese übertragene Zeile ganz entfernen
            if s == "" and out and out[-1].strip() == "":
                continue                      # zweite Leerzeile in Folge weglassen
        # Layout: vor einer Überschrift im Push-Bereich (oder vor '### Keep') genau
        # eine Trenn-Leerzeile, falls die vorige Zeile keine Leerzeile ist.
        if is_heading and (in_push or is_section) and out and out[-1].strip() != "":
            out.append("")
        out.append(ln)
        if is_section:
            in_push = "push" in s.lower()     # '### Push' an, '### Keep'/andere aus
    result = "\n".join(out)
    return result + "\n" if (trailing_nl and not result.endswith("\n")) else result


def clear_pushed(entries: list[str]) -> None:
    """Übertragene Zeilen aus INBOX entfernen + Push-Abschnitt aufräumen (nach Commit)."""
    if not INBOX.exists() or not entries:
        return
    INBOX.write_text(
        _clean_push_text(INBOX.read_text(encoding="utf-8"), entries),
        encoding="utf-8")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO),
                          capture_output=True, text=True)


def run_push() -> None:
    if not _lock.acquire(blocking=False):
        return  # ein Lauf läuft bereits
    try:
        entries = push_entries()
        if not entries:
            log("Speichern erkannt — '### Push' leer, nichts zu tun.")
            return
        log(f"Push: {len(entries)} Eintrag/Einträge → sortiere ({MODEL}) …")

        # 1) claude sortiert NUR nach BACKLOG (INBOX bleibt unangetastet).
        try:
            r = subprocess.run(
                ["claude", "-p", "--model", MODEL,
                 "--permission-mode", "acceptEdits", PROMPT],
                cwd=str(REPO), capture_output=True, text=True, timeout=180)
        except Exception as e:
            log(f"claude-Fehler: {e} — INBOX unverändert, nichts verloren.")
            notify("Sortieren fehlgeschlagen — INBOX unverändert.")
            return
        if r.returncode != 0:
            log(f"claude exit={r.returncode}: {(r.stderr or '').strip()[:160]} "
                f"— INBOX unverändert.")
            notify(f"Sortieren fehlgeschlagen (exit {r.returncode}) — INBOX unverändert.")
            return

        # 2) BACKLOG committen → Einträge sind JETZT sicher persistiert.
        _git("add", "BACKLOG.md")
        c = _git("commit", "-m",
                 "docs: inbox push (auto-daemon)\n\n"
                 "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>")
        if c.returncode != 0:
            log("BACKLOG-Commit leer/fehlgeschlagen (claude hat nichts geändert?) "
                f"— INBOX NICHT geleert: {(c.stdout + c.stderr).strip()[:140]}")
            notify("Nichts sortiert — INBOX NICHT geleert.")
            return
        log("BACKLOG committet.")

        # 3) ERST JETZT INBOX leeren (deterministisch) + committen.
        try:
            clear_pushed(entries)
            _git("add", "INBOX.md")
            ic = _git("commit", "-m",
                      "docs: inbox geleert nach push (auto-daemon)\n\n"
                      "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>")
            log("INBOX geleert + committet."
                if ic.returncode == 0 else f"INBOX-Commit: {(ic.stdout + ic.stderr).strip()[:140]}")
            n = len(entries)
            notify(f"{n} Eintrag{'e' if n != 1 else ''} → Backlog sortiert.")
        except Exception as e:
            log(f"INBOX-Leeren fehlgeschlagen: {e} (Einträge sind aber im Backlog).")
            notify("Im Backlog, aber INBOX-Leeren fehlgeschlagen — bitte prüfen.")
    finally:
        _lock.release()


def main() -> int:
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        log("FEHLER: 'watchdog' fehlt. Installieren: .venv/bin/python -m pip install watchdog")
        return 1

    class _Handler(FileSystemEventHandler):
        def __init__(self) -> None:
            self._timer: threading.Timer | None = None

        def _schedule(self) -> None:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_S, run_push)
            self._timer.daemon = True
            self._timer.start()

        def on_modified(self, event) -> None:
            if not event.is_directory and Path(event.src_path).name == "INBOX.md":
                self._schedule()

        on_created = on_modified

    log(f"INBOX-Daemon läuft. Beobachte {INBOX.name} im Repo. (Strg-C beendet)")
    obs = Observer()
    obs.schedule(_Handler(), str(REPO), recursive=False)
    obs.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Daemon beendet.")
    finally:
        obs.stop()
        obs.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
