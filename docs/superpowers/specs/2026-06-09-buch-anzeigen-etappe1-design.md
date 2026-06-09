# Konzept: Buch-Anzeigen-Helfer

**Datum:** 2026-06-09
**Status:** Konzept abgestimmt; eBay-Weg über **CSV-Manager (File Exchange)** für ein
**privates** Konto **erfolgreich getestet und bestätigt** (siehe Abschnitt 11).

---

## 1. Hintergrund & Ziel

Der Vater des Nutzers verkauft Bücher über **eBay.de** (privates Verkäuferkonto). Heute lädt
er Fotos manuell bei einem KI-Chat hoch und lässt sich daraus Anzeigentexte erstellen. Das
soll eine eigene, einfache Anwendung übernehmen, damit sein Arbeitsablauf **möglichst
effizient** wird.

**Bediener:** der Vater **allein** → oberste Regel: Oberfläche extrem einfach und
narrensicher (große Knöpfe, wenige Schritte, Technik unsichtbar).

---

## 2. Der gewählte Gesamtweg (nach Machbarkeitsprüfung)

> Fotos → KI erzeugt Anzeigentext → bearbeitbare Vorschau → **fertige eBay-CSV-Datei** →
> der Vater lädt sie selbst im eBay-CSV-Manager hoch.

**Wichtige Architektur-Entscheidung:** Der eBay-Eintrag läuft **nicht** über die offizielle
API (die ist für **private** Konten gesperrt), sondern über den **CSV-Manager / File
Exchange**. Dieser Weg funktioniert für private Konten – das wurde am 2026-06-09 mit einer
echten Test-Anzeige bewiesen (Abschnitt 11). Dadurch entfällt die komplette OAuth-/
Verkaufsregeln-/API-Komplexität.

**Etappen:**
- **Etappe 1 (MVP):** Fotos → KI-Text → bearbeitbare Vorschau → **eBay-CSV exportieren** +
  kopieren/speichern.
- **Etappe 2 (später):** Komfort (z. B. Stapelbetrieb mehrerer Bücher in einer CSV,
  automatisches Hosten der Fotos).
- **Etappe 3 (später):** Preisanalyse.

---

## 3. Umfang von Etappe 1

**Enthalten:**
- Genau **ein Buch pro Durchgang**.
- Fotos per **Drag & Drop** ins Fenster ziehen (zusätzlich Knopf „Fotos auswählen").
- KI erzeugt aus den Fotos: **Titel**, **Artikeldetails** (Autor, Buchtitel, Sprache + weitere
  Buchangaben) und eine **Beschreibung**.
- Ergebnis in **bearbeitbaren Feldern** anzeigen.
- Ausgabe als **fertige eBay-CSV-Datei** (zum Hochladen im CSV-Manager) **und** zum Kopieren.
- KI-Modell per Schalter wählbar (Start: günstigeres Modell).
- Verständliche Fehlermeldungen auf Deutsch.

**Nicht enthalten (bewusst):**
- Keine Preisanalyse (Etappe 3).
- Kein Stapelbetrieb (mehrere Bücher gleichzeitig).
- Kein automatisches Hochladen zu eBay (der Vater lädt die CSV selbst hoch – gewollt, gibt ihm
  Kontrolle und vermeidet Risiko).

---

## 4. Ablauf aus Sicht des Nutzers

1. App per Desktop-Symbol öffnen.
2. Fotos eines Buches ins Fenster ziehen → Vorschaubildchen erscheinen.
3. Knopf **„Anzeige erstellen"** klicken.
4. Kurz warten → Felder Titel/Details/Beschreibung erscheinen.
5. Bei Bedarf Texte direkt in den Feldern bearbeiten, Preis/Zustand prüfen.
6. **„eBay-Datei speichern"** → die App erzeugt die CSV.
7. Im eBay-CSV-Manager hochladen. „Neues Buch" → von vorn.

---

## 5. Technische Bauform

- **Lokale Web-App:** läuft auf dem PC des Vaters; er öffnet sie im Browser über ein
  Desktop-Symbol. Plattformunabhängig, Drag & Drop natürlich, gutes Aussehen.
- **Motor (Backend):** kleines Python-Programm mit der offiziellen Anthropic-Bibliothek.
- **Oberfläche (Frontend):** HTML/CSS/etwas JavaScript, gestaltet nach **ui-ux-pro-max**.
- **Zielsystem:** Windows-PC. Entwicklung & Tests laufen auf dem Mac im Browser.
- **Verpackung für Windows:** am Ende ein Doppelklick-Start.
  - *Ehrlicher Hinweis:* Das Windows-Paket lässt sich am Mac nicht direkt erzeugen; dafür ist
    am Schluss kurz ein Windows-Rechner (oder ein Automatik-Dienst) nötig. Für die Bauphase
    reicht der Mac.

---

## 6. Bausteine (klar getrennte Aufgaben)

| Baustein | Aufgabe | Hängt ab von |
|---|---|---|
| Oberfläche | Fotos annehmen, Knöpfe, Ergebnisfelder anzeigen/bearbeiten | Motor |
| Foto-Aufnahme | Bilder entgegennehmen, Vorschau, fürs Senden vorbereiten | – |
| KI-Anbindung | Fotos + Prompt an Claude schicken, Antwort in Felder zerlegen | API-Schlüssel |
| Foto-Upload (imgbb) | Fotos zu imgbb hochladen, öffentliche Bild-Adressen für PicURL holen | imgbb-Schlüssel |
| CSV-Erzeugung | Felder in das exakte eBay-CSV-Format schreiben (siehe Abschnitt 11) | – |
| Ergebnis-Ausgabe | CSV speichern, Texte kopieren | – |
| Einstellungen | API-Schlüssel + Modellwahl lokal speichern | – |

---

## 7. KI-Teil

- Claude liest die Fotos und schreibt deutschen Anzeigentext.
- Antwort kommt in **klar getrennten Feldern** zurück, passend zu den eBay-CSV-Spalten:
  Titel, Beschreibung sowie die Buchangaben (Autor, Buchtitel, Sprache, optional Verlag,
  Erscheinungsjahr, Format, Genre, Seitenzahl …).
- **Modellwahl (umschaltbar):** Start mit günstigerem/schnellem Modell (~3–5 Cent/Buch),
  bei Bedarf stärkeres Modell (~5–8 Cent/Buch).
- **Prompt:** wird vom Nutzer geliefert (beim Programmieren) und ist leicht austauschbar.

---

## 8. Oberfläche (grob)

Eine aufgeräumte Seite: oben „Fotos hierher ziehen" (+ Knopf), Mitte „Anzeige erstellen",
unten die bearbeitbaren Felder + Eingaben für Preis/Zustand, dann „eBay-Datei speichern" und
Kopier-Knöpfe. Große Schrift, wenig Ablenkung. Feindesign nach ui-ux-pro-max.

---

## 9. Speichern, Kopieren & API-Schlüssel

- **„eBay-Datei speichern"** → erzeugt die fertige CSV im richtigen Format.
- **Kopier-Knöpfe** pro Feld (für manuelles Einfügen, falls gewünscht).
- **API-Schlüssel (Anthropic):** einmalig in einem kleinen Einstellungs-Feld eingeben; die App
  merkt ihn sich **lokal** (nicht im Code, nicht in der Cloud). Abrechnung nach Verbrauch.

---

## 10. Fehlerbehandlung (verständliche deutsche Meldungen)

Kein Internet · API-Schlüssel fehlt/falsch · keine Fotos · KI antwortet nicht. Jeder Fall
zeigt eine klare Meldung statt eines Absturzes.

---

## 11. eBay-Machbarkeit: GETESTET & BESTÄTIGT (2026-06-09)

**Ergebnis: GO.** Ein **privates** eBay.de-Konto kann über den **CSV-Manager (File Exchange)**
Anzeigen einstellen. Bewiesen mit einer echten Test-Anzeige (ItemID `267694404256`, danach
beendet).

**Wichtige technische Erkenntnisse für die CSV-Erzeugung:**
- Datei muss **UTF-8 mit BOM** sein, Trennzeichen **`;`** (Semikolon). Ohne BOM ignoriert eBay
  die Datei (0 Datensätze).
- Aufbau: Zeile 1 = `Info;Version=1.0.0;Template=fx_category_template_EBAY_DE`,
  Zeile 2 = exakte Kopfzeile (99 Spalten), ab Zeile 3 = Datenzeilen.
- Aktion `Add` erstellt eine Anzeige. (`VerifyAdd` als reiner Probelauf wurde **nicht**
  verarbeitet – dieser CSV-Manager unterstützt es offenbar nicht.)
- **Keine Verkaufsregeln (Business Policies) nötig:** Versand, Rücknahme und Bearbeitungszeit
  werden **direkt in der Datei** angegeben (`ShippingType`, `ShippingService-1:Option/Cost`,
  `ReturnsAcceptedOption`, `DispatchTimeMax`). Genau das macht den Weg für private Konten frei.
- Pflichtfelder (`*`): Action, Category, Title (≤80 Z.), ConditionID, C:Autor, C:Buchtitel,
  C:Sprache, Description, Format, Duration, StartPrice, Quantity, Location, DispatchTimeMax,
  ReturnsAcceptedOption.
- Bewährte Beispielwerte: Buch-Kategorie `261186`; Zustand Bücher = **1000** Neu, **2750** Wie
  neu, **4000** Sehr gut, **5000** Gut, **6000** Akzeptabel (`3000` ist ungültig für Bücher);
  Format `FixedPrice`; Duration `GTC`; Preis mit Punkt (`9.99`); Versandart `DE_DHLPaket`;
  `ReturnsNotAccepted` für Privatverkauf.
- Fotos: Spalte **`PicURL`** erwartet **öffentliche Bild-Adressen** (eBay holt das Bild ab) –
  Fotos werden NICHT in der CSV mitgeschickt. → Siehe offener Punkt unten.
- Ergebnis-/Antwortdatei von eBay: Spalte `Status` (`Success`/`Warning`/`Failure`),
  `ErrorMessage`, und bei Erfolg eine `ItemID`.

---

## 12. Offene Punkte

- **Fotos zu eBay (PicURL): ENTSCHIEDEN → imgbb.** Die App lädt jedes Foto automatisch zu
  **imgbb** hoch und schreibt die zurückgegebene öffentliche Bild-Adresse in `PicURL` (mehrere
  per `|` getrennt, max. 12). Für den Vater unsichtbar. Kniff: eBay **kopiert** das Bild beim
  Einstellen auf seine eigenen Server (EPS), daher muss die imgbb-Adresse nur **kurz** während
  des Hochladens erreichbar sein – Dauerhaftigkeit egal, Foto kann danach gelöscht werden.
  Bildgröße ~800×800 px ideal. Braucht einen (kostenlosen) imgbb-API-Schlüssel.
- **Genauer KI-Prompt** vom Nutzer (beim Programmieren).
- **Windows-Verpackung** am Schluss (Windows-Rechner oder Automatik-Dienst).
- Feinheiten der CSV (z. B. weitere optionale Buchfelder) ergeben sich beim Bauen.
