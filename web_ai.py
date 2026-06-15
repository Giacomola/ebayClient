"""Gemeinsamer Helfer: schickt einen Auftrag mit aktiver Websuche an Claude und
gibt das zurückgegebene JSON-Objekt als dict zurück.

Das server-seitige Websuche-Werkzeug kann die Antwort mit stop_reason "pause_turn"
unterbrechen; dann wird der Aufruf fortgesetzt, bis die KI fertig ist."""
import json
import os
import sys
import time
import anthropic

# Websuche-Werkzeug. max_uses begrenzt die Einzelsuchen PRO Aufruf. WICHTIG für die
# Kosten: Jede Suche lädt die Trefferseiten in den Kontext und bläht die Eingabe um
# ~15.000 Token auf (gemessen). Darum ist das Limit bewusst niedrig (2): ein Buch, bei
# dem das Modell sonst viele Male suchen würde, kann so nie unverhältnismäßig teuer
# werden. Das hält auch die Wartezeit kurz.
# allowed_callers=["direct"]: Das Werkzeug wird direkt aufgerufen (nicht über
# „programmatic tool calling"). Ohne diese Angabe lehnen Modelle wie Haiku 4.5 den
# Aufruf mit einem 400-Fehler ab; mit der Angabe funktioniert die Websuche bei allen
# Modellen (Opus, Sonnet, Haiku).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search",
                   "max_uses": 2, "allowed_callers": ["direct"]}

def _repair_json(s: str) -> str:
    """Repariert die zwei häufigsten JSON-Fehler von Sprachmodellen in EINEM Durchlauf,
    zeichenkettenbewusst (Inhalte in "…" bleiben sonst unangetastet):

    1. Überzählige Kommas direkt vor } oder ] werden weggelassen.
    2. Echte Steuerzeichen INNERHALB einer Zeichenkette (Zeilenumbruch, Tab) sind in
       JSON nicht erlaubt – sie werden in die gültigen Schreibweisen \\n / \\t / \\r
       umgewandelt. Das passiert oft, wenn die KI eine HTML-Beschreibung mit echten
       Zeilenumbrüchen in ein JSON-Textfeld schreibt."""
    out = []
    in_string = False
    escaped = False
    for i, ch in enumerate(s):
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.append("\\n")   # echter Zeilenumbruch → gültiges \n
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            continue
        if ch == ",":
            j = i + 1
            while j < len(s) and s[j] in " \t\r\n":
                j += 1
            if j < len(s) and s[j] in "}]":
                continue  # überzähliges Komma vor schließender Klammer weglassen
        out.append(ch)
    return "".join(out)

def _extract_json(text: str) -> dict:
    """Holt das erste JSON-Objekt aus dem Antworttext (von erster { bis letzter }).

    Toleriert den häufigsten Modell-Fehler (überzähliges Komma vor einer schließenden
    Klammer): erst streng parsen, bei Misserfolg einmal reparieren, sonst klar melden."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Die KI hat keine verwertbare JSON-Antwort geliefert.")
    chunk = text[start:end + 1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        try:
            return json.loads(_repair_json(chunk))
        except json.JSONDecodeError as e:
            raise ValueError(
                "Die KI hat kein gültiges JSON geliefert (auch nach Reparatur)."
            ) from e

MAX_ROUNDS = 4   # Obergrenze für pause_turn-Runden (Websuche), damit es nicht ausufert

def _log(msg: str) -> None:
    """Kurze Fortschrittsmeldung ins Server-Terminal (für den Vater unsichtbar,
    aber beim Mitschauen/Debuggen hilfreich)."""
    print(f"[web_ai] {msg}", file=sys.stderr, flush=True)

def complete_json(*, api_key: str, model: str, content: list, max_tokens: int = 4000,
                   max_searches: int | None = None, use_search: bool = True) -> dict:
    # max_retries klein halten, damit sich bei Hängern nichts minutenlang aufsummiert.
    # timeout mit Luft über der Realdauer (~60–90 s pro Aufruf), sonst greift der
    # Timeout zu früh und löst unnötige Wiederholungen aus.
    #
    # max_searches: überschreibt die erlaubte Anzahl Einzelsuchen (None = Standardwert
    # aus WEB_SEARCH_TOOL). use_search=False schaltet die Websuche ganz ab – nützlich,
    # um die reine Modellgeschwindigkeit ohne Recherche zu messen.
    if use_search:
        tool = dict(WEB_SEARCH_TOOL)
        if max_searches is not None:
            tool["max_uses"] = max_searches
        tools = [tool]
    else:
        tools = []
    client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=150.0)
    messages = [{"role": "user", "content": content}]
    resp = None
    for runde in range(1, MAX_ROUNDS + 1):
        _log(f"Runde {runde}/{MAX_ROUNDS}: warte auf Modell (Modell={model}) …")
        t0 = time.time()
        resp = client.messages.create(
            model=model, max_tokens=max_tokens,
            tools=tools, messages=messages,
        )
        _log(f"Runde {runde} fertig in {time.time() - t0:.1f}s · stop_reason={resp.stop_reason}")
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    if resp.stop_reason == "pause_turn":
        raise RuntimeError("Die KI hat die Recherche nach mehreren Runden nicht "
                           "abgeschlossen. Bitte erneut versuchen.")
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    _log(f"Antworttext: {len(text)} Zeichen · Anfang={text[:160]!r}")
    try:
        return _extract_json(text)
    except ValueError as e:
        _log(f"JSON-Auslesen fehlgeschlagen: {e} · Ende={text[-300:]!r}")
        _dump_bad_json(text)
        raise

def _dump_bad_json(text: str) -> None:
    """Sichert die komplette KI-Rohantwort in logs/last_bad_json.txt, damit man die
    genaue ungültige Stelle nachsehen kann (logs/ ist per .gitignore ausgenommen)."""
    try:
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "last_bad_json.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        _log("Komplette Rohantwort gesichert: logs/last_bad_json.txt")
    except OSError as e:
        _log(f"Konnte Rohantwort nicht sichern: {e}")
