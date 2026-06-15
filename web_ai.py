"""Gemeinsamer Helfer: schickt einen Auftrag mit aktiver Websuche an Claude und
gibt das zurückgegebene JSON-Objekt als dict zurück.

Das server-seitige Websuche-Werkzeug kann die Antwort mit stop_reason "pause_turn"
unterbrechen; dann wird der Aufruf fortgesetzt, bis die KI fertig ist."""
import json
import anthropic

# Websuche-Werkzeug. Hinweis: Sollte die API diese Version ablehnen, auf
# {"type": "web_search_20250305", "name": "web_search"} ausweichen (beim Bauen prüfen).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

def _extract_json(text: str) -> dict:
    """Holt das erste JSON-Objekt aus dem Antworttext (von erster { bis letzter })."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Die KI hat keine verwertbare JSON-Antwort geliefert.")
    return json.loads(text[start:end + 1])

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
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return _extract_json(text)
