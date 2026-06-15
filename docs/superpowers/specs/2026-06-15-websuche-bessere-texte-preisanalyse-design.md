# Konzept: Bessere KI-Texte + Websuche + Preisanalyse

**Datum:** 2026-06-15
**Status:** Konzept abgestimmt (Variante A). Baut auf dem bestehenden Buch-Anzeigen-Helfer auf.

---

## 1. Hintergrund & Ziel

Der Buch-Anzeigen-Helfer erzeugt heute aus Fotos eines Buches per Claude einen
eBay-Anzeigentext und eine File-Exchange-CSV. Drei Schwächen sollen behoben werden:

1. **Texte zu unvollständig** — Felder bleiben leer, weil auf den Fotos nichts steht.
2. **Falscher Ton** — der Text soll antiquarisch korrekt **und** ein ansprechender
   Verkaufstext sein (der Leser ist ein potenzieller Käufer).
3. **Keine Preisanalyse** — der Vater wünscht eine Preisempfehlung als Hilfe.

Lösung: Claude bekommt eine **Websuche**, um fehlende Buchdaten zu ergänzen und Preise
zu recherchieren; der Prompt wird auf Verkaufston umgeschrieben; Standardmodell wird
**Opus 4.8** (Sonnet bleibt umschaltbar).

Bediener bleibt der Vater allein → oberste Regel weiterhin: **eine einfache,
narrensichere Oberfläche, ein Knopf**.

---

## 2. Gewählter Weg (Variante A)

**Zwei fokussierte Such-Aufrufe, für den Vater ein Knopf:**

1. **Aufruf 1 (Text):** Fotos + Websuche → Claude bestimmt die **exakte Ausgabe**,
   füllt Lücken, schreibt den verkaufsstarken Text → strukturierte Felder, plus
   Quellen-Links und Markierung, welche Felder aus dem Netz stammen.
2. **Aufruf 2 (Preis):** Websuche allein für den Preis → Preisspanne +
   Vergleichsangebote mit Links.

Die Oberfläche ruft beide **nacheinander** auf: Der Text erscheint zuerst, die
Preisempfehlung füllt sich ein paar Sekunden später dazu. Vorteile: jeder Teil ist
einfach und einzeln testbar (passt zur bestehenden Modulstruktur), der Text ist sofort
sichtbar, und eine fehlgeschlagene Preissuche blockiert den Text nicht.

**Bewusst verworfen:** ein kombinierter Aufruf (Text+Preis in einem) — spart zwar eine
Recherche, ist aber technisch kniffliger und schwerer zu debuggen; ein Fehler träfe
beides. Variante A folgt „Einfachheit vor Cleverness".

---

## 3. Umfang

**Enthalten:**
- Websuche im Text-Aufruf zur Ausgaben-Bestimmung und Lücken-Ergänzung.
- Neuer Prompt: antiquarisch korrekt **und** verkaufsstark/käuferorientiert.
- Web-ergänzte Felder werden in der Oberfläche markiert; Quellen-Links anklickbar.
- Preisanalyse: Spanne + Vergleichsangebote mit Links, **nur als Empfehlung**.
- Standardmodell Opus 4.8, Sonnet umschaltbar.

**Nicht enthalten:**
- Kein automatisches Eintragen des Preises ins Preisfeld (nur optionaler Knopf zum
  manuellen Übernehmen).
- Keine eigene eBay-Verkauft-Schnittstelle (siehe ehrliche Hinweise, Abschnitt 9).
- Keine Änderung am CSV-Format oder am bestehenden Speicher-/Entwurf-Mechanismus.

---

## 4. Ablauf aus Sicht des Vaters

1. Fotos eines Buches reinziehen → **„Anzeige erstellen"**.
2. Status **„🔎 recherchiere im Netz …"** → nach ~30–60 s erscheinen Felder +
   Beschreibung (Text nutzt bereits die Web-Recherche).
3. Status **„💶 prüfe Preise …"** → die **Preisempfehlung** füllt sich dazu.
4. Felder prüfen/bearbeiten, Quellen bei Bedarf anklicken, Preis selbst setzen
   (optional „in Preisfeld übernehmen").
5. Wie bisher: „eBay-Datei speichern" → CSV im eBay-CSV-Manager hochladen.

---

## 5. Module (was neu, was geändert)

| Modul | Änderung |
|---|---|
| `ai_client.py` | Websuche-Werkzeug aktiviert; neue strukturierte Rückgabe (s. u.); nutzt den neuen Verkaufs-Prompt. |
| `price_analysis.py` (**neu**) | `analyze_price(...)` → eigener Such-Aufruf für Preisspanne + Vergleichsangebote. |
| `config.py` | Standardmodell `claude-opus-4-8`; neue Prompt-Texte (Text + Preis); Sonnet bleibt wählbar. |
| `app.py` | `/api/generate` (Aufruf 1) bleibt, liefert jetzt erweiterte Daten; neuer `/api/price` (Aufruf 2). |
| `templates/index.html`, `static/app.js`, `static/style.css` | 🌐-Abzeichen, Abschnitt „Quellen", Abschnitt „Preisempfehlung", zweite Fortschrittsmeldung. |

Jedes Modul hat weiterhin **eine** Aufgabe und ist einzeln testbar; `app.py` verdrahtet nur.

---

## 6. KI-Teil (Technik)

### 6.1 Aufruf 1 — Text mit Websuche (`ai_client.analyze_book`)
- Werkzeug: `web_search_20260209` (unterstützt automatisches Vorfiltern auf Opus 4.8).
- Claude erhält Fotos + Prompt + Websuche und liefert die Anzeigenfelder zurück.
- **Erweiterte Rückgabe** (`BookFields` wird ergänzt):
  - bestehende Felder: `title, author, book_title, language, description,
    publisher, publication_year, book_format`
  - `web_sourced_fields: list[str]` — Schlüssel der Felder, deren Inhalt aus dem Netz
    stammt (für das Oberflächen-Abzeichen; die Feldwerte selbst bleiben sauber, damit
    die CSV nicht verschmutzt wird).
  - `sources: list[{title, url}]` — anklickbare Quellen-Links.
- Prompt-Leitlinien: exakte Ausgabe bestimmen (Auflage/Druck/Jahr); großzügig
  ergänzen, aber Web-Herkunft transparent machen; antiquarisch korrekt **und**
  verkaufsstark, Käufer direkt ansprechend; bestehende Regeln (kein Semikolon,
  HTML-Beschreibung, Titel ≤ 80 Zeichen) bleiben.

### 6.2 Aufruf 2 — Preis (`price_analysis.analyze_price`)
- Eingabe: die in Aufruf 1 bestimmten Buchdaten (Autor, Titel, Jahr, Ausgabe).
- Werkzeug: `web_search_20260209`.
- Rückgabe `PriceAnalysis`: `price_low, price_high, currency (EUR),
  comparables: list[{title, price, url, source}], note`.
- Prompt: bevorzugt ZVAB/Booklooker/AbeBooks (aktuelle Angebote) und eBay-Verkauft,
  soweit auffindbar; ehrlich bleiben, wenn wenig gefunden wird (`note`).

### 6.3 Modell & Aufruf-Form
- Standard `claude-opus-4-8`; Sonnet (`claude-sonnet-4-6`) bleibt in den Einstellungen
  wählbar.
- Server-seitiges Websuche-Werkzeug → die Antwort kann `stop_reason: "pause_turn"`
  liefern; der Aufruf muss in einer kleinen Schleife fortgesetzt werden, bis
  `end_turn`.
- **Strukturierte Ausgabe:** primär `output_config.format` (JSON-Schema) zusammen mit
  dem Websuche-Werkzeug. **Plan B (technisches Risiko):** Sollte sich erzwungenes
  JSON-Format mit dem Websuche-Werkzeug als nicht kompatibel erweisen, gibt der Aufruf
  die Felder als JSON-Block per Prompt-Anweisung zurück und der Code liest sie mit
  `json.loads` (mit robuster Fehlerbehandlung). Diese Entscheidung wird beim Bauen
  einmal verifiziert.

---

## 7. Oberfläche

- An jedem web-ergänzten Feld ein kleines Abzeichen **„🌐 aus Websuche"**.
- Abschnitt **„Quellen"**: Liste anklickbarer Links (öffnen in neuem Tab).
- Abschnitt **„Preisempfehlung"**: Spanne (`von – bis €`), darunter Vergleichsangebote
  als anklickbare Liste (Titel, Preis, Quelle), plus Hinweistext. Ein kleiner Knopf
  **„in Preisfeld übernehmen"** (Mittelwert) — optional, manuell.
- Zwei Fortschrittsmeldungen: „🔎 recherchiere im Netz …", dann „💶 prüfe Preise …".
- Großschrift/Einfachheit wie bisher; keine Pflicht-Eingaben dazu.

---

## 8. Fehlerbehandlung (verständliche deutsche Meldungen)

- Bestehende Fälle bleiben: kein/falscher Schlüssel, keine Verbindung, Server
  überlastet (5xx), KI-Fehler.
- **Preissuche scheitert oder findet nichts** → Text bleibt erhalten; Preisbereich
  zeigt „Keine Preise gefunden" statt eines Absturzes.
- **Websuche im Text-Aufruf scheitert** → Claude soll trotzdem aus den Fotos
  antworten (Felder ggf. unvollständig), kein Absturz.

---

## 9. Ehrliche Hinweise / Grenzen

- **eBay-Verkauft eingeschränkt:** Die Verkauft-Seite ist über eine normale Websuche
  nur teils zugänglich. Die Spanne stützt sich realistisch v. a. auf **aktuelle
  Angebote**; eBay-Verkauft nur, wo Claude es findet. Es ist eine **Empfehlung**, kein
  exakter Marktwert.
- **Kosten & Wartezeit:** Opus 4.8 kostet pro Buch spürbar mehr als Sonnet, Websuche
  kostet zusätzlich pro Suche, und ein Durchgang dauert mit Recherche ~30–90 s statt
  weniger Sekunden. Bewusst akzeptiert für „deutlich bessere" Ergebnisse; Sonnet bleibt
  als günstige Option umschaltbar.
- **Falsche Ausgabe:** Trotz „exakte Ausgabe bestimmen" kann Claude eine falsche
  Ausgabe erwischen. Deshalb Web-Markierung + Quellen-Links, damit der Vater prüfen
  kann (transparente Variante, kein blindes Vertrauen).

---

## 10. Tests

- `tests/test_ai_client.py`: erweitert — Websuche-Werkzeug ist im Aufruf enthalten;
  erweiterte Rückgabe (`web_sourced_fields`, `sources`) wird korrekt durchgereicht
  (anthropic gemockt).
- `tests/test_price_analysis.py` (**neu**): `analyze_price` gibt `PriceAnalysis` mit
  Spanne und Vergleichsangeboten zurück (anthropic gemockt).
- `tests/test_app.py`: erweitert — `/api/generate` liefert die erweiterten Felder;
  neuer `/api/price` ruft `analyze_price` auf und gibt die Preisdaten zurück; ohne
  Schlüssel klare Fehlermeldung.
- Manueller End-to-End-Test mit echten Schlüsseln (ein reales Buch) bleibt der
  Schlussschritt.

---

## 11. Offene Detail-Entscheidungen (beim Bauen)

- Verifizieren, ob `output_config.format` + Websuche zusammen funktionieren, sonst
  Plan B (Abschnitt 6.3).
- Genaue Prompt-Formulierungen (Text & Preis) — Startfassung im Plan, Feinschliff mit
  dem Nutzer.
