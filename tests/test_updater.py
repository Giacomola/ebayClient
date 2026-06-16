import os
import pytest
from updater import apply_update, _ist_geschuetzt


def _schreib(pfad, inhalt):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt)


def _lies(pfad):
    with open(pfad, encoding="utf-8") as f:
        return f.read()


def test_ist_geschuetzt():
    assert _ist_geschuetzt("config.json") is True
    assert _ist_geschuetzt("anweisungen.txt") is True
    assert _ist_geschuetzt("cases/abc.json") is True
    assert _ist_geschuetzt(".venv/bin/python") is True
    assert _ist_geschuetzt("app.py") is False
    assert _ist_geschuetzt("static/app.js") is False


def test_apply_update_ueberschreibt_und_schuetzt(tmp_path):
    projekt = tmp_path / "projekt"
    quelle = tmp_path / "neu"
    # Vorher: alte App + private Daten + Anpassung.
    _schreib(str(projekt / "app.py"), "ALT")
    _schreib(str(projekt / "config.json"), "GEHEIM")
    _schreib(str(projekt / "anweisungen.txt"), "MEINE REGELN")
    _schreib(str(projekt / "cases" / "fall.json"), "FALL")
    # Neues Paket: neue app.py, neue Datei, will config/anweisungen überschreiben.
    _schreib(str(quelle / "app.py"), "NEU")
    _schreib(str(quelle / "static" / "app.js"), "JS-NEU")
    _schreib(str(quelle / "config.json"), "BOESE")
    _schreib(str(quelle / "anweisungen.txt"), "STANDARD")

    count = apply_update(str(projekt), str(quelle))

    assert _lies(str(projekt / "app.py")) == "NEU"           # Code aktualisiert
    assert _lies(str(projekt / "static" / "app.js")) == "JS-NEU"  # neue Datei angelegt
    assert _lies(str(projekt / "config.json")) == "GEHEIM"   # Schlüssel unangetastet
    assert _lies(str(projekt / "anweisungen.txt")) == "MEINE REGELN"  # Anpassung bleibt
    assert _lies(str(projekt / "cases" / "fall.json")) == "FALL"      # Fälle bleiben
    assert count == 2                                        # app.py + static/app.js


def test_apply_update_rollback_bei_fehler(tmp_path, monkeypatch):
    projekt = tmp_path / "projekt"
    quelle = tmp_path / "neu"
    _schreib(str(projekt / "app.py"), "ALT")
    _schreib(str(quelle / "app.py"), "NEU")
    _schreib(str(quelle / "static" / "app.js"), "JS-NEU")

    # copy2 beim ZWEITEN Aufruf (zweite Datei) scheitern lassen -> Rollback.
    import updater
    echte_copy = updater.shutil.copy2
    zaehler = {"n": 0}

    def fies(src, dst, *a, **k):
        # Sicherungs-Kopien (ins .update-backups) zulassen, nur das echte Schreiben zählen.
        if updater.BACKUP_ORDNER not in str(dst):
            zaehler["n"] += 1
            if zaehler["n"] == 2:
                raise OSError("Schreibfehler (Test)")
        return echte_copy(src, dst, *a, **k)

    monkeypatch.setattr(updater.shutil, "copy2", fies)

    with pytest.raises(OSError):
        apply_update(str(projekt), str(quelle))

    # Nach dem Rollback ist der alte Stand wieder da und nichts Neues übrig.
    assert _lies(str(projekt / "app.py")) == "ALT"
    assert not os.path.exists(str(projekt / "static" / "app.js"))

def test_apply_update_macht_command_skripte_ausfuehrbar(tmp_path):
    # Im „Paket" liegt ein .command-Skript ohne Ausführbar-Bit (so kommt es aus
    # dem entpackten ZIP). Nach dem Update muss es ausführbar sein.
    projekt = tmp_path / "projekt"
    quelle = tmp_path / "neu"
    _schreib(str(quelle / "Start.command"), "#!/bin/bash\necho hi\n")
    os.chmod(str(quelle / "Start.command"), 0o644)        # nicht ausführbar
    _schreib(str(quelle / "app.py"), "NEU")               # normale Datei bleibt wie sie ist
    os.chmod(str(quelle / "app.py"), 0o644)

    apply_update(str(projekt), str(quelle))

    assert os.access(str(projekt / "Start.command"), os.X_OK)      # jetzt ausführbar
    assert not os.access(str(projekt / "app.py"), os.X_OK)         # .py unverändert
