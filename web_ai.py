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

def complete_json(*, api_key: str | None = None, model: str, content: list,
                   max_tokens: int = 4000, max_searches: int | None = None,
                   use_search: bool = True, backend: str = "api_key") -> dict:
    """Schickt den Auftrag an Claude und gibt das zurückgegebene JSON als dict zurück.

    backend="api_key": über den Anthropic-API-Schlüssel (pro Nutzung bezahlt).
    backend="abo":     über das Claude-Abo via Agent SDK / Claude-Code-CLI – der
                       Verbrauch geht aufs Monatsguthaben des Abos, KEIN API-Schlüssel.

    Beide Wege liefern denselben Antworttext; die JSON-Auswertung darunter ist gleich."""
    if backend == "abo":
        text = _via_abo(model=model, content=content, use_search=use_search,
                        max_searches=max_searches)
    else:
        text = _via_api(api_key=api_key, model=model, content=content,
                        max_tokens=max_tokens, max_searches=max_searches,
                        use_search=use_search)
    _log(f"Antworttext: {len(text)} Zeichen · Anfang={text[:160]!r}")
    try:
        return _extract_json(text)
    except ValueError as e:
        _log(f"JSON-Auslesen fehlgeschlagen: {e} · Ende={text[-300:]!r}")
        _dump_bad_json(text)
        raise

def _via_api(*, api_key: str | None, model: str, content: list, max_tokens: int,
             max_searches: int | None, use_search: bool) -> str:
    """Weg über den Anthropic-API-Schlüssel (bisheriges Verhalten).

    max_retries klein halten, damit sich bei Hängern nichts minutenlang aufsummiert.
    timeout mit Luft über der Realdauer (~60–90 s pro Aufruf), sonst greift der
    Timeout zu früh und löst unnötige Wiederholungen aus.

    max_searches: überschreibt die erlaubte Anzahl Einzelsuchen (None = Standardwert
    aus WEB_SEARCH_TOOL). use_search=False schaltet die Websuche ganz ab – nützlich,
    um die reine Modellgeschwindigkeit ohne Recherche zu messen."""
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
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

def _find_claude_cli() -> str | None:
    """Sucht den 'claude'-Befehl robust – erst über PATH, dann an üblichen Orten.
    Wichtig, weil eine per Doppelklick gestartete .app/Verknüpfung oft einen kargen
    PATH hat und unter Windows der frische Installpfad erst in einer neuen Konsole
    im PATH steht."""
    import shutil
    found = shutil.which("claude")
    if found:
        return found
    # Windows: der native Installer legt claude unter %USERPROFILE%\.local\bin ab
    # (als .exe/.cmd). macOS/Linux: ~/.local/bin bzw. Homebrew/usr-Pfade.
    kandidaten = (
        os.path.expanduser(r"~\.local\bin\claude.exe"),
        os.path.expanduser(r"~\.local\bin\claude.cmd"),
        os.path.expanduser("~/.local/bin/claude"),
        "/opt/homebrew/bin/claude", "/usr/local/bin/claude",
    )
    for p in kandidaten:
        if os.path.exists(p):
            return p
    return None

ABO_SYSTEM_EBAY = ("Du fuellst eBay-Buchanzeigen aus Fotos. Folge den "
                   "Anweisungen im Auftrag genau und antworte wie verlangt. "
                   "Halte dich strikt an genannte Such-Obergrenzen.")

def _via_abo(*, model: str, content: list, use_search: bool,
             max_searches: int | None = None,
             system_prompt: str = ABO_SYSTEM_EBAY) -> str:
    """Weg über das Claude-Abo (Agent SDK steuert die Claude-Code-CLI). Kein API-Schlüssel –
    der Verbrauch geht aufs Monatsguthaben. Es werden bewusst nur die Websuche und keine
    Datei-/Shell-Werkzeuge erlaubt, damit die KI ausschließlich analysiert und JSON liefert.

    WICHTIG zur Websuche: Anders als der API-Weg (Tool-Limit max_uses) kennt die Agent-CLI
    keine harte Such-Obergrenze. Ohne Bremse sucht die KI auf vielen Seiten und läuft in die
    Schritt-Obergrenze (Abbruch) oder dauert minutenlang. Darum (a) begrenzen wir die Suchen
    per klarer Anweisung und (b) geben passend dazu genug Schritte (max_turns)."""
    try:
        import anyio
        from claude_agent_sdk import (query, ClaudeAgentOptions,
                                      AssistantMessage, TextBlock)
    except ImportError as e:
        raise RuntimeError(
            "Der Abo-Weg braucht das Paket 'claude-agent-sdk'. Bitte in der .venv "
            "installieren: pip install claude-agent-sdk"
        ) from e

    cli = _find_claude_cli()
    if not cli:
        raise RuntimeError(
            "Claude Code (Befehl 'claude') wurde nicht gefunden. Für den Abo-Weg muss "
            "Claude Code installiert und eingeloggt sein."
        )

    # Erlaubte Suchen (Standard 2, wie das API-Tool); daraus ein großzügiges Schritt-Budget.
    n = max_searches if (max_searches and max_searches > 0) else 2
    run_content = content
    if use_search:
        cap = ("\n\nWICHTIG: Führe insgesamt HÖCHSTENS %d Websuchen aus. Antworte danach "
               "SOFORT mit dem geforderten JSON, auch wenn du nur wenige oder keine Treffer "
               "hast. Suche nicht auf weiteren Seiten und wiederhole keine Suchen." % n)
        run_content = content + [{"type": "text", "text": cap}]
        max_turns = 6 + 3 * n      # genug Luft für die Suchen + die finale JSON-Antwort
    else:
        max_turns = 4              # ohne Suche reicht eine knappe Runde

    async def _run() -> str:
        async def messages():
            yield {"type": "user", "message": {"role": "user", "content": run_content}}
        options = ClaudeAgentOptions(
            model=model,
            allowed_tools=["WebSearch"] if use_search else [],
            disallowed_tools=["Bash", "Edit", "Write", "Read", "Glob", "Grep"],
            max_turns=max_turns,
            cli_path=cli,
            system_prompt=system_prompt,
        )
        text = ""
        async for msg in query(prompt=messages(), options=options):
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        text += b.text
        return text

    _log(f"Abo-Weg (Agent SDK): Modell={model}, Websuche={use_search}")
    t0 = time.time()
    text = anyio.run(_run)
    _log(f"Abo-Weg fertig in {time.time() - t0:.1f}s")
    return text

# --- Einfacher Chat (freie Text-Antwort, mehrere Runden) --------------------
# Grundhaltung des Fragen-Fensters. Das eigentliche App-Wissen kommt aus
# chat_wissen.txt und wird unten angehängt (siehe _chat_system).
CHAT_BASIS = (
    "Du bist der eingebaute Helfer im Programm Buch-Anzeigen-Helfer. Deine Aufgabe "
    "ist es, dem Nutzer bei der Bedienung dieses Programms und beim Erstellen von "
    "eBay-Buchanzeigen zu helfen. Gehe davon aus, dass sich jede Frage auf dieses "
    "Programm oder seine Aufgabe bezieht (Bücher fotografieren und beschreiben, "
    "Preise, eBay, die Bedienung) – auch wenn das Programm nicht ausdrücklich genannt "
    "wird. Antworte auf Deutsch, sachlich und freundlich, vor allem aber "
    "lösungsorientiert: nenne konkret den nächsten Schritt oder den richtigen Knopf, "
    "statt allgemein zu bleiben. Fasse dich kurz und ohne Fachjargon; der Nutzer ist "
    "kein Computerfachmann. Fehlt dir eine Information, frage kurz nach. Stütze dich "
    "auf das folgende Wissen über das Programm und erfinde keine Funktionen, die dort "
    "nicht stehen. "
    "Halte deine Antworten kurz – in der Regel zwei bis vier Sätze, nur wenn nötig "
    "mehr. Verzichte auf Überschriften und lange Aufzählungen. Hervorhebungen nur "
    "sparsam mit **fett** oder *kursiv* (wird im Fenster als echtes Fett/Kursiv "
    "angezeigt); benutze keine sonstigen Sonderzeichen zur Gestaltung."
)

def _chat_system(wissen: str = "") -> str:
    """Baut den System-Prompt fürs Fragen-Fenster: Grundhaltung + App-Wissen."""
    if wissen.strip():
        return CHAT_BASIS + "\n\n=== WISSEN ÜBER DAS PROGRAMM ===\n" + wissen.strip()
    return CHAT_BASIS

def chat(*, api_key: str | None = None, model: str, messages: list, wissen: str = "",
         use_search: bool = True, backend: str = "api_key",
         max_tokens: int = 1000, max_searches: int = 2) -> str:
    """Beantwortet eine Chat-Frage als freien Text. messages = Liste aus
    {"role": "user"|"assistant", "content": "..."}. wissen = App-Wissen für den
    System-Prompt. Gibt den Antworttext zurück."""
    system = _chat_system(wissen)
    if backend == "abo":
        # Die Agent-CLI bekommt einen Prompt – den Verlauf in einen Text gießen.
        teile = [("Frage" if m["role"] == "user" else "Antwort") + ": " + str(m.get("content", ""))
                 for m in messages]
        content = [{"type": "text", "text": "\n".join(teile) + "\n\nAntwort:"}]
        return _via_abo(model=model, content=content, use_search=use_search,
                        max_searches=max_searches, system_prompt=system)
    return _chat_via_api(api_key=api_key, model=model, messages=messages, system=system,
                         use_search=use_search, max_searches=max_searches,
                         max_tokens=max_tokens)

def _chat_via_api(*, api_key, model, messages, system, use_search, max_searches, max_tokens) -> str:
    """Chat über den Anthropic-API-Schlüssel (echte Mehrrunden-Unterhaltung)."""
    tools = []
    if use_search:
        tool = dict(WEB_SEARCH_TOOL)
        if max_searches is not None:
            tool["max_uses"] = max_searches
        tools = [tool]
    client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=150.0)
    conv = [dict(m) for m in messages]
    resp = None
    for _ in range(MAX_ROUNDS):
        resp = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            tools=tools, messages=conv,
        )
        if resp.stop_reason == "pause_turn":   # Websuche läuft noch → fortsetzen
            conv.append({"role": "assistant", "content": resp.content})
            continue
        break
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

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
