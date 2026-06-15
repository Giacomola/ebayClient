"""Gemeinsamer Helfer: schickt einen Auftrag mit aktiver Websuche an Claude und
gibt das zurückgegebene JSON-Objekt als dict zurück.

Das server-seitige Websuche-Werkzeug kann die Antwort mit stop_reason "pause_turn"
unterbrechen; dann wird der Aufruf fortgesetzt, bis die KI fertig ist."""
import json
import anthropic

# Websuche-Werkzeug. Hinweis: Sollte die API diese Version ablehnen, auf
# {"type": "web_search_20250305", "name": "web_search"} ausweichen (beim Bauen prüfen).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

def _strip_trailing_commas(s: str) -> str:
    """Entfernt überzählige Kommas direkt vor } oder ] – der häufigste JSON-Fehler
    von Sprachmodellen. String-bewusst: Kommas INNERHALB von Zeichenketten (auch
    "…, }") bleiben unangetastet, nur ein echtes Komma vor der schließenden Klammer
    wird weggelassen."""
    out = []
    in_string = False
    escaped = False
    for i, ch in enumerate(s):
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
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
            return json.loads(_strip_trailing_commas(chunk))
        except json.JSONDecodeError as e:
            raise ValueError(
                "Die KI hat kein gültiges JSON geliefert (auch nach Reparatur)."
            ) from e

def complete_json(*, api_key: str, model: str, content: list, max_tokens: int = 4000) -> dict:
    client = anthropic.Anthropic(api_key=api_key, max_retries=4, timeout=180.0)
    messages = [{"role": "user", "content": content}]
    resp = None
    for _ in range(6):  # genug Runden für mehrere Websuchen, aber endlich
        resp = client.messages.create(
            model=model, max_tokens=max_tokens,
            tools=[WEB_SEARCH_TOOL], messages=messages,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    if resp.stop_reason == "pause_turn":
        raise RuntimeError("Die KI hat die Recherche nach mehreren Runden nicht "
                           "abgeschlossen. Bitte erneut versuchen.")
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return _extract_json(text)
