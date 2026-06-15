#!/usr/bin/env python3
"""Lokaler Vergleichs-Test für die Textgenerierung.

Probiert dasselbe Buchfoto mit verschiedenen Modellen und Such-Parametern durch und
misst je Variante: Dauer, stop_reason, Anzahl Runden, ob die KI gültiges JSON liefert
und ob sich daraus die erwarteten Felder (BookFields) bauen lassen. Die komplette
Rohantwort jeder Variante wird unter logs/bench/ gespeichert, damit man eine kaputte
JSON-Stelle nachsehen kann.

Aufruf (aus dem Projektordner):
    .venv/bin/python tools/bench_text.py
    .venv/bin/python tools/bench_text.py --models opus,sonnet --searches 5,3,0
    .venv/bin/python tools/bench_text.py --image pfad/zum/foto.jpg

--searches versteht: eine Zahl = erlaubte Einzelsuchen; 0 = Websuche ganz aus.
Achtung: jeder Lauf ist ein echter (kostenpflichtiger) API-Aufruf von ~30–100 s.
"""
import argparse
import base64
import json
import os
import sys
import time

# Projektordner in den Importpfad, egal von wo gestartet wird.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from web_ai import WEB_SEARCH_TOOL, MAX_ROUNDS, _extract_json
from ai_client import JSON_INSTRUCTIONS, BookFields
from config import load_settings, build_system_prompt

# Kurznamen → echte Modell-IDs.
MODELLE = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}

def lade_bilder(image_arg: str | None) -> list[bytes]:
    """Bilder entweder aus einer angegebenen Datei oder aus dem aktuellen Entwurf."""
    if image_arg:
        with open(image_arg, "rb") as f:
            return [f.read()]
    if not os.path.exists("draft.json"):
        sys.exit("Kein --image angegeben und keine draft.json gefunden.")
    draft = json.load(open("draft.json", encoding="utf-8"))
    imgs = []
    for im in draft.get("images", []):
        data_url = im.get("data_url", "")
        if "," in data_url:
            imgs.append(base64.b64decode(data_url.split(",", 1)[1]))
    if not imgs:
        sys.exit("In draft.json sind keine Bilder gespeichert. Bitte --image nutzen.")
    return imgs

def baue_inhalt(images: list[bytes], prompt: str) -> list:
    """Genau derselbe Aufbau wie in ai_client.analyze_book (Bilder + Prompt)."""
    content = []
    for img in images:
        media = "image/png" if img[:8].startswith(b"\x89PNG") else "image/jpeg"
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": media,
            "data": base64.standard_b64encode(img).decode("ascii")}})
    content.append({"type": "text", "text": prompt + JSON_INSTRUCTIONS})
    return content

# Preise in US-Dollar pro 1 Mio. Token (Stand laut Modell-Tabelle).
PREISE = {
    "claude-opus-4-8":   {"in": 5.0, "out": 25.0},
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
    "claude-haiku-4-5":  {"in": 1.0, "out": 5.0},
}
# Anthropic berechnet die Websuche zusätzlich: ca. 10 $ pro 1000 Suchen = 0,01 $/Suche.
SUCHE_PREIS = 0.01

def lauf(api_key: str, model: str, content: list, max_searches: int, use_search: bool) -> dict:
    """Ein einzelner Versuch. Gibt Messwerte und die Rohantwort zurück (keine Ausnahme,
    damit die Tabelle auch bei Fehlern vollständig bleibt)."""
    if use_search:
        tool = dict(WEB_SEARCH_TOOL)
        tool["max_uses"] = max_searches
        tools = [tool]
    else:
        tools = []
    client = anthropic.Anthropic(api_key=api_key, max_retries=1, timeout=150.0)
    messages = [{"role": "user", "content": content}]
    t0 = time.time()
    runden = 0
    resp = None
    tok_in = tok_out = suchen = 0
    try:
        for runden in range(1, MAX_ROUNDS + 1):
            resp = client.messages.create(model=model, max_tokens=4000,
                                           tools=tools, messages=messages)
            u = resp.usage
            tok_in += getattr(u, "input_tokens", 0) or 0
            tok_out += getattr(u, "output_tokens", 0) or 0
            stu = getattr(u, "server_tool_use", None)
            if stu is not None:
                suchen += getattr(stu, "web_search_requests", 0) or 0
            if resp.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": resp.content})
                continue
            break
    except Exception as e:  # API-Fehler vollständig auffangen
        return {"dauer": time.time() - t0, "runden": runden, "stop": "FEHLER",
                "json_ok": False, "felder_ok": False, "fehler": str(e)[:200], "text": "",
                "tok_in": tok_in, "tok_out": tok_out, "suchen": suchen, "kosten": 0.0}
    dauer = time.time() - t0
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    json_ok, felder_ok, fehler = False, False, ""
    try:
        data = _extract_json(text)
        json_ok = True
        BookFields(**data)
        felder_ok = True
    except Exception as e:
        fehler = str(e)[:200]
    preis = PREISE.get(model, {"in": 0, "out": 0})
    kosten = (tok_in / 1e6) * preis["in"] + (tok_out / 1e6) * preis["out"] + suchen * SUCHE_PREIS
    return {"dauer": dauer, "runden": runden, "stop": resp.stop_reason,
            "json_ok": json_ok, "felder_ok": felder_ok,
            "fehler": fehler, "text": text,
            "tok_in": tok_in, "tok_out": tok_out, "suchen": suchen, "kosten": kosten}

def main():
    ap = argparse.ArgumentParser(description="Vergleichs-Test der Textgenerierung")
    ap.add_argument("--models", default="opus,sonnet",
                    help="Komma-Liste aus opus,sonnet,haiku (Standard: opus,sonnet)")
    ap.add_argument("--searches", default="5,3,0",
                    help="Komma-Liste erlaubter Einzelsuchen; 0 = Websuche aus (Standard: 5,3,0)")
    ap.add_argument("--image", default=None, help="Pfad zu einem Foto (sonst aus draft.json)")
    args = ap.parse_args()

    settings = load_settings("config.json")
    api_key = settings.get("anthropic_api_key", "")
    if not api_key:
        sys.exit("Kein Anthropic-API-Schlüssel in config.json.")
    prompt = build_system_prompt(settings)
    images = lade_bilder(args.image)
    content = baue_inhalt(images, prompt)

    modelle = [m.strip() for m in args.models.split(",") if m.strip()]
    suchen = [int(s.strip()) for s in args.searches.split(",") if s.strip() != ""]
    os.makedirs(os.path.join("logs", "bench"), exist_ok=True)

    print(f"\nFoto(s): {len(images)} · Modelle: {modelle} · Suchen: {suchen}")
    print("Jeder Lauf ist ein echter API-Aufruf (~30–100 s). Bitte Geduld …\n")
    kopf = (f"{'Variante':<18}{'Dauer':>7}{'JSON':>6}{'Token-ein':>10}{'Token-aus':>10}"
            f"{'Suchen':>7}{'~Kosten':>10}")
    print(kopf)
    print("-" * len(kopf))

    for mk in modelle:
        model = MODELLE.get(mk, mk)
        for s in suchen:
            use_search = s > 0
            label = f"{mk}/such{s}" if use_search else f"{mk}/ohne-suche"
            r = lauf(api_key, model, content, s, use_search)
            # Rohantwort sichern (auch bei Erfolg – zum Vergleich der Textqualität).
            with open(os.path.join("logs", "bench", f"{label.replace('/', '_')}.txt"),
                      "w", encoding="utf-8") as f:
                f.write(r["text"] or f"(kein Text) Fehler: {r['fehler']}")
            cent = r["kosten"] * 100
            print(f"{label:<18}{r['dauer']:>6.1f}s"
                  f"{('ja' if r['felder_ok'] else 'NEIN'):>6}"
                  f"{r['tok_in']:>10}{r['tok_out']:>10}{r['suchen']:>7}"
                  f"{cent:>8.1f}¢")
            if r["fehler"]:
                print(f"    → {r['fehler']}")
    print("\nRohantworten liegen unter logs/bench/ (zum Nachlesen der Textqualität "
          "und kaputter JSON-Stellen).")

if __name__ == "__main__":
    main()
