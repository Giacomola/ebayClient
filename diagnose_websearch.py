"""Diagnose: testet die Claude-Websuche ISOLIERT vom Rest der App.

Aufruf (im Projektordner):
    . .venv/bin/activate && python diagnose_websearch.py

Nutzt den in config.json gespeicherten Anthropic-Schlüssel und das gewählte
Modell. Kurzer Timeout (90 s) und KEINE Wiederholungen, damit sich nichts
„aufsummiert" – so sehen wir schnell, ob es hängt, nur langsam ist, oder ob die
Werkzeug-Version abgelehnt wird. Dieses Skript ist nur zum Prüfen und kann danach
gelöscht werden."""
import time
import anthropic
from config import load_settings

PROMPT = ("Suche kurz im Netz nach dem Buch 'Der Hobbit' von J.R.R. Tolkien "
          "und nenne in einem Satz das ursprüngliche Erscheinungsjahr.")

def try_tool(client, model, tool):
    t0 = time.time()
    messages = [{"role": "user", "content": [{"type": "text", "text": PROMPT}]}]
    rounds = 0
    resp = None
    while rounds < 4:
        rounds += 1
        print(f"   … Runde {rounds} läuft (Modell antwortet/sucht) …", flush=True)
        resp = client.messages.create(model=model, max_tokens=1024,
                                      tools=[tool], messages=messages)
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    dt = time.time() - t0
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return dt, resp.stop_reason, rounds, text

def main():
    s = load_settings()
    key = s.get("anthropic_api_key", "")
    model = s.get("model", "")
    if not key:
        print("FEHLER: kein anthropic_api_key in config.json gefunden.")
        return
    print(f"Modell laut config.json: {model}")
    print("(Timeout 90 s, keine Wiederholungen)")
    client = anthropic.Anthropic(api_key=key, max_retries=0, timeout=90.0)
    for tool in ({"type": "web_search_20260209", "name": "web_search"},
                 {"type": "web_search_20250305", "name": "web_search"}):
        print(f"\n--- teste Werkzeug {tool['type']} ---", flush=True)
        try:
            dt, stop, rounds, text = try_tool(client, model, tool)
            print(f"OK in {dt:.1f}s · stop_reason={stop} · Runden={rounds}")
            print("Antwort:", (text[:300] or "(kein Text)"))
        except anthropic.APIStatusError as e:
            print(f"API-Fehler {e.status_code}: {getattr(e, 'message', e)}")
        except anthropic.APITimeoutError:
            print("ZEITÜBERSCHREITUNG nach 90 s – der Aufruf hängt bzw. ist zu langsam.")
        except Exception as e:  # noqa: BLE001
            print(f"Fehler: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
