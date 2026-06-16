"""Erzeugt eine eBay-File-Exchange-CSV (Kategorie-Vorlage Bücher).

Unterstützt eine einzelne Anzeige (build_csv) sowie das Sammeln mehrerer
Anzeigen in einer gemeinsamen Datei (append_listing)."""
import os
import re
from datetime import date

ACTION = "*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)"
INFO_LINE = "Info;Version=1.0.0;Template=fx_category_template_EBAY_DE"
DEFAULT_FILENAME = "ebay-anzeigen.csv"

COLUMNS = [
    ACTION, "CustomLabel", "*Category", "StoreCategory", "*Title", "Subtitle",
    "Relationship", "RelationshipDetails", "ScheduleTime", "*ConditionID", "VAT%",
    "*C:Autor", "*C:Buchtitel", "*C:Sprache", "C:Thematik", "C:Buchreihe", "C:Genre",
    "C:Verlag", "C:Erscheinungsjahr", "C:Originalsprache", "C:Format", "C:Ursprungsland",
    "C:Produktart", "C:Literarische Gattung", "C:Signiert von", "C:Zielgruppe",
    "C:Ausgabe", "C:Literarische Bewegung", "C:Vintage", "C:Signiert", "C:Personalisiert",
    "C:Personalisieren", "C:Beschriftet", "C:Exlibris", "C:Besonderheiten", "C:Illustrator",
    "C:Epoche", "C:Herstellungszeitraum", "C:Anzahl der Einheiten", "C:Anzahl der Seiten",
    "C:Breite", "C:Gewicht", "C:Höhe", "C:Länge", "C:Maßeinheit",
    "C:Anleitung für Personalisierung", "PicURL", "GalleryType", "VideoID", "*Description",
    "*Format", "*Duration", "*StartPrice", "BuyItNowPrice", "BestOfferEnabled",
    "BestOfferAutoAcceptPrice", "MinimumBestOfferPrice", "*Quantity", "ImmediatePayRequired",
    "*Location", "ShippingType", "ShippingService-1:Option", "ShippingService-1:Cost",
    "ShippingService-2:Option", "ShippingService-2:Cost", "*DispatchTimeMax",
    "PromotionalShippingDiscount", "ShippingDiscountProfileID", "DomesticRateTable",
    "*ReturnsAcceptedOption", "ReturnsWithinOption", "RefundOption",
    "ShippingCostPaidByOption", "AdditionalDetails", "Product Safety Pictograms",
    "Product Safety Statements", "Product Safety Component", "Regulatory Document Ids",
    "Manufacturer Name", "Manufacturer AddressLine1", "Manufacturer AddressLine2",
    "Manufacturer City", "Manufacturer Country", "Manufacturer PostalCode",
    "Manufacturer StateOrProvince", "Manufacturer Phone", "Manufacturer Email",
    "Manufacturer ContactURL", "Responsible Person 1", "Responsible Person 1 Type",
    "Responsible Person 1 AddressLine1", "Responsible Person 1 AddressLine2",
    "Responsible Person 1 City", "Responsible Person 1 Country",
    "Responsible Person 1 PostalCode", "Responsible Person 1 StateOrProvince",
    "Responsible Person 1 Phone", "Responsible Person 1 Email",
    "Responsible Person 1 ContactURL",
]

# Erlaubte Aktionen: "Add" stellt sofort ein, "Draft" legt einen Entwurf an.
GUELTIGE_AKTIONEN = ("Add", "Draft")

def _ist_angebotszeile(line: str) -> bool:
    """True, wenn die Zeile eine Anzeige ist – egal ob sofort eingestellt (Add) oder
    als Entwurf (Draft). So zählen/erkennen alle Funktionen beide Aktionen."""
    return line.startswith("Add;") or line.startswith("Draft;")

def _clean(value) -> str:
    """Entfernt Trennzeichen/Umbrüche, damit die Spaltenanzahl stabil bleibt."""
    if value is None:
        return ""
    text = str(value)
    for ch in (";", "\r", "\n"):
        text = text.replace(ch, " ")
    return text.strip()

def _limit(text: str, max_len: int) -> str:
    """Kürzt auf max. max_len Zeichen, möglichst an der letzten Wortgrenze."""
    if len(text) <= max_len:
        return text
    cut = text[:max_len].rstrip()
    if " " in cut:
        cut = cut[:cut.rfind(" ")].rstrip()
    return cut or text[:max_len]

def _preis_punkt(text: str) -> str:
    """Macht aus einem Preis mit Dezimal-Komma einen mit Punkt (9999,99 -> 9999.99).

    eBay erwartet den Punkt als Dezimaltrenner. Insbesondere der Entwurf-Prozessor
    lehnt „9999,99" sonst ab („Could not serialize field [manifest.msrp]").
    Deutsches Tausender-Format (1.234,56) wird dabei korrekt zu 1234.56."""
    t = (text or "").strip()
    if "," in t and "." in t:
        t = t.replace(".", "")          # Tausenderpunkte entfernen
    return t.replace(",", ".")          # Dezimalkomma -> Punkt

# eBay-Längengrenzen: Anzeigentitel 80, Artikelmerkmale (C:...) je 65 Zeichen.
SPECIFIC_MAX = 65

def title_for(title) -> str:
    """Der Anzeigentitel genau so, wie er in der CSV landet (für den Dubletten-Abgleich)."""
    return _limit(_clean(title), 80)

HEADER = ";".join(COLUMNS)

def _values(*, title, author, book_title, language, description, price,
            condition_id, picture_urls, publisher="", publication_year="",
            book_format="", location="Berlin", shipping_service="DE_DHLPaket",
            shipping_cost="5.49", dispatch_time_max="3", custom_label="",
            action="Add") -> dict:
    return {
        ACTION: action if action in GUELTIGE_AKTIONEN else "Add",
        "CustomLabel": _clean(custom_label),
        "*Category": "29223",  # eBay.de „Antiquitäten & Kunst › Antiquarische Bücher"
        "*Title": title_for(title),
        "*ConditionID": _clean(condition_id),
        "*C:Autor": _limit(_clean(author), SPECIFIC_MAX),
        "*C:Buchtitel": _limit(_clean(book_title), SPECIFIC_MAX),
        "*C:Sprache": _limit(_clean(language), SPECIFIC_MAX),
        "C:Verlag": _limit(_clean(publisher), SPECIFIC_MAX),
        "C:Erscheinungsjahr": _clean(publication_year),
        "C:Format": _limit(_clean(book_format), SPECIFIC_MAX),
        "PicURL": "|".join(picture_urls[:12]),
        "*Description": _clean(description),
        "*Format": "FixedPrice",
        "*Duration": "GTC",
        "*StartPrice": _preis_punkt(_clean(price)),
        "*Quantity": "1",
        "*Location": _clean(location),
        "ShippingType": "Flat",
        "ShippingService-1:Option": _clean(shipping_service),
        "ShippingService-1:Cost": _clean(shipping_cost),
        "*DispatchTimeMax": _clean(dispatch_time_max),
        "*ReturnsAcceptedOption": "ReturnsNotAccepted",
    }

def build_row(**kwargs) -> str:
    """Baut die Datenzeile (99 Spalten, mit ; getrennt) für ein Buch."""
    values = _values(**kwargs)
    return ";".join(values.get(col, "") for col in COLUMNS)

def build_csv(**kwargs) -> bytes:
    """Erzeugt eine komplette CSV (Info + Kopfzeile + eine Datenzeile) als Bytes."""
    text = "\r\n".join([INFO_LINE, HEADER, build_row(**kwargs)]) + "\r\n"
    return ("﻿" + text).encode("utf-8")

# Dubletten werden über Autor + Buchtitel erkannt (nicht über den Anzeigentitel) –
# so erzeugen kleine Änderungen am Anzeigentitel keine zweite Zeile.
_AUTOR_INDEX = COLUMNS.index("*C:Autor")
_BUCHTITEL_INDEX = COLUMNS.index("*C:Buchtitel")

def _norm(value) -> str:
    """Vergleichsform: Trennzeichen/Umbrüche weg, Kleinbuchstaben, Mehrfach-Leerzeichen
    zusammengefasst. So zählen Groß-/Kleinschreibung und Leerzeichen nicht als Unterschied."""
    return " ".join(_clean(value).lower().split())

def _row_key(row: str) -> tuple:
    """(Autor, Buchtitel) einer Datenzeile in Vergleichsform."""
    cells = row.split(";")
    return (_norm(cells[_AUTOR_INDEX]), _norm(cells[_BUCHTITEL_INDEX]))

def entry_exists(folder: str, author, book_title, filename: str = DEFAULT_FILENAME) -> bool:
    """True, wenn schon eine Anzeige mit gleichem Autor UND Buchtitel existiert.

    Buchtitel + Autor sind der Schlüssel. Ohne Buchtitel gibt es keinen verlässlichen
    Abgleich – dann nie eine Dublette."""
    key = (_norm(author), _norm(book_title))
    if not key[1]:
        return False
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8-sig") as f:
        return any(_ist_angebotszeile(line) and _row_key(line.rstrip("\r\n")) == key
                   for line in f)

def _safe_name(name: str) -> str:
    """Macht aus der Nutzereingabe einen sicheren Dateinamen-Bestandteil:
    nur Buchstaben (inkl. Umlaute), Ziffern, Leerzeichen, - und _ ; Leerzeichen
    werden zu Unterstrichen."""
    name = (name or "").strip()
    name = re.sub(r"[^\wäöüÄÖÜß \-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name

def archive_as_file(folder: str, custom_name: str = "",
                    filename: str = DEFAULT_FILENAME):
    """Benennt die aktive Sammeldatei in eine datierte Archivdatei um und gibt so
    den Platz für eine frische Datei frei (die nächste Anzeige legt sie neu an).

    Der Archivname ist immer ``eBayClient_<JJJJ-MM-TT>[_<Name>].csv``; bei
    Namensgleichheit wird _2, _3 … angehängt. Gibt (Anzahl Anzeigen, Archivname)
    zurück – (0, "") wenn nichts zu archivieren war."""
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return 0, ""
    with open(path, "r", encoding="utf-8-sig") as f:
        count = sum(1 for line in f if _ist_angebotszeile(line))
    if count == 0:
        return 0, ""
    base = f"eBayClient_{date.today().isoformat()}"
    extra = _safe_name(custom_name)
    if extra:
        base = f"{base}_{extra}"
    archive_name = f"{base}.csv"
    n = 2
    while os.path.exists(os.path.join(folder, archive_name)):  # Kollision vermeiden
        archive_name = f"{base}_{n}.csv"
        n += 1
    os.rename(path, os.path.join(folder, archive_name))  # ganze Datei wandert ins Archiv
    return count, archive_name

def recent_listings(folder: str, filename: str = DEFAULT_FILENAME, limit: int = 10):
    """Liest die zuletzt gespeicherten Anzeigen aus der Sammeldatei.

    Gibt eine Liste von {title, author, price} zurück – neueste zuerst, höchstens
    `limit` Stück. Fehlt die Datei, kommt eine leere Liste zurück."""
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return []
    idx_title = COLUMNS.index("*Title")
    idx_author = COLUMNS.index("*C:Autor")
    idx_price = COLUMNS.index("*StartPrice")
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            if _ist_angebotszeile(line):
                cells = line.rstrip("\r\n").split(";")
                rows.append({"title": cells[idx_title], "author": cells[idx_author],
                             "price": cells[idx_price]})
    rows.reverse()  # neueste zuerst
    return rows[:limit]

def listing_stats(folder: str, filename: str = DEFAULT_FILENAME) -> dict:
    """Überblick über die Sammeldatei: Anzahl der Anzeigen und Summe der Startpreise.

    Gibt {"count": int, "total": float} zurück. Fehlt die Datei, sind beide 0."""
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return {"count": 0, "total": 0.0}
    idx_price = COLUMNS.index("*StartPrice")
    count = 0
    total = 0.0
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            if not _ist_angebotszeile(line):
                continue
            count += 1
            cells = line.rstrip("\r\n").split(";")
            text = cells[idx_price] if idx_price < len(cells) else ""
            m = re.search(r"\d+(?:[.,]\d+)?", text)
            if m:
                total += float(m.group(0).replace(",", "."))
    return {"count": count, "total": round(total, 2)}

def list_archives(folder: str) -> list:
    """Listet die archivierten Sammeldateien (eBayClient_<Datum>…csv), neueste zuerst.

    Pro Datei {filename, count, total}. Da der Dateiname mit ISO-Datum beginnt,
    sortiert eine absteigende Namenssortierung zugleich chronologisch."""
    if not os.path.isdir(folder):
        return []
    out = []
    for fn in os.listdir(folder):
        if fn.startswith("eBayClient_") and fn.endswith(".csv"):
            s = listing_stats(folder, fn)
            out.append({"filename": fn, "count": s["count"], "total": s["total"]})
    out.sort(key=lambda a: a["filename"], reverse=True)
    return out

def remove_listing(folder: str, author, book_title,
                   filename: str = DEFAULT_FILENAME) -> bool:
    """Entfernt die Anzeige mit gleichem Autor + Buchtitel aus der Sammeldatei.

    Nutzt denselben Schlüssel wie der Dubletten-Abgleich. Schreibt die Datei mit
    den übrigen Zeilen neu (Info- und Kopfzeile bleiben erhalten, auch wenn keine
    Anzeige mehr übrig ist). Gibt True zurück, wenn etwas entfernt wurde."""
    key = (_norm(author), _norm(book_title))
    if not key[1]:                       # ohne Buchtitel kein verlässlicher Treffer
        return False
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = [line.rstrip("\r\n") for line in f if _ist_angebotszeile(line)]
    rest = [r for r in rows if _row_key(r) != key]
    if len(rest) == len(rows):           # nichts gefunden
        return False
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\r\n" + HEADER + "\r\n")
        for r in rest:
            f.write(r + "\r\n")
    return True

def append_listing(folder: str, filename: str = DEFAULT_FILENAME, **kwargs):
    """Fügt eine Anzeige zur gemeinsamen CSV im Ordner hinzu.

    Gibt es bereits eine Anzeige mit GLEICHEM Autor UND Buchtitel, wird sie
    ersetzt statt eine zweite Zeile anzuhängen – so erzeugen kleine Änderungen am
    Anzeigentitel keine Dublette. Legt die Datei mit BOM, Info- und Kopfzeile an,
    falls sie noch nicht existiert. Gibt (Pfad, Anzahl der Anzeigen) zurück."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    new_row = build_row(**kwargs)
    new_key = _row_key(new_row)

    # Vorhandene Datenzeilen einlesen (Info-/Kopfzeile werden neu geschrieben).
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            rows = [line.rstrip("\r\n") for line in f if _ist_angebotszeile(line)]

    # Bei gleichem Autor + Buchtitel die alte Zeile entfernen (sie wird ersetzt).
    if new_key[1]:   # nur bei vorhandenem Buchtitel
        rows = [r for r in rows if _row_key(r) != new_key]
    rows.append(new_row)

    # Die aktuelle Aktion (Add/Draft der neuen Zeile) gilt für ALLE Zeilen, damit
    # die ganze Datei immer der aktuellen Einstellung entspricht – auch ältere Zeilen.
    aktion = new_row.split(";")[0]
    rows = [_mit_aktion(_mit_preis_punkt(r), aktion) for r in rows]

    # Komplette Datei neu schreiben: BOM + Info + Kopf + alle Datenzeilen.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\r\n" + HEADER + "\r\n")
        for r in rows:
            f.write(r + "\r\n")
    return path, len(rows)

def _mit_aktion(row: str, action: str) -> str:
    """Ersetzt die Aktion (erste Spalte) einer Datenzeile durch <action>."""
    cells = row.split(";")
    cells[0] = action
    return ";".join(cells)

_PREIS_INDEX = COLUMNS.index("*StartPrice")

def _mit_preis_punkt(row: str) -> str:
    """Normt den Preis (Spalte *StartPrice) einer bestehenden Datenzeile auf Punkt.

    So heilen sich auch ältere Zeilen mit Dezimal-Komma, sobald die Datei neu
    geschrieben wird – Komma kann dann nirgends mehr überleben."""
    cells = row.split(";")
    if _PREIS_INDEX < len(cells):
        cells[_PREIS_INDEX] = _preis_punkt(cells[_PREIS_INDEX])
    return ";".join(cells)

# ---------------------------------------------------------------------------
# eBay-Entwurf-Vorlage (eigene, kleinere Datei)
#
# eBay nimmt ECHTE Entwürfe nur über eine eigene, begrenzte Vorlage an – NICHT
# über die volle Kategorie-Vorlage oben. Unterschiede: die Aktionsspalte heißt
# `Action(...)` OHNE führendes `*`, und der Wert ist „Draft". Versand, Rücknahme
# und Standort trägt eBay im Entwurf NICHT (ergänzt man später bei eBay). Die volle
# Beschreibung kommt mit – und Artikelmerkmale lassen sich als `C:...`-Spalten OHNE
# Stern anhängen (von eBay bei Entwürfen unterstützt), darum die C:-Spalten unten.
#
# Diese Datei wird aus der vollen Sammeldatei abgeleitet (alle Werte stecken dort
# schon drin), damit Dubletten-Abgleich/Liste/Statistik unverändert auf der vollen
# Datei arbeiten können.
DRAFT_FILENAME = "ebay-entwuerfe.csv"
DRAFT_INFO_LINE = "#INFO;Version=0.0.2;Template= eBay-draft-listings-template_DE"
# Die Basis-Spalten der Entwurfs-Vorlage …
DRAFT_BASE_COLUMNS = [
    "Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)",
    "Custom label (SKU)", "Category ID", "Title", "UPC", "Price", "Quantity",
    "Item photo URL", "Condition ID", "Description", "Format",
]
# … plus die Artikelmerkmale, die wir tatsächlich füllen. Paar (Entwurf-Spalte ohne
# Stern → Quellspalte in der vollen Vorlage).
DRAFT_SPECIFICS = [
    ("C:Autor", "*C:Autor"),
    ("C:Buchtitel", "*C:Buchtitel"),
    ("C:Sprache", "*C:Sprache"),
    ("C:Verlag", "C:Verlag"),
    ("C:Erscheinungsjahr", "C:Erscheinungsjahr"),
    ("C:Format", "C:Format"),
]
DRAFT_COLUMNS = DRAFT_BASE_COLUMNS + [ziel for ziel, _ in DRAFT_SPECIFICS]
DRAFT_HEADER = ";".join(DRAFT_COLUMNS)

def _full_to_draft_row(row: str) -> str:
    """Wandelt eine volle Datenzeile in eine Entwurf-Zeile (11 Spalten) um.

    Alle benötigten Werte stecken bereits in der vollen Zeile – wir lesen sie
    über ihre Spaltennamen aus und ordnen sie der Entwurf-Reihenfolge zu."""
    cells = row.split(";")
    def hol(col: str) -> str:
        i = COLUMNS.index(col)
        return cells[i] if i < len(cells) else ""
    werte = [
        "Draft",                       # Action
        hol("CustomLabel"),            # Custom label (SKU)
        hol("*Category"),              # Category ID
        hol("*Title"),                 # Title
        "",                            # UPC (haben wir nicht)
        _preis_punkt(hol("*StartPrice")),  # Price (Punkt statt Komma)
        hol("*Quantity"),              # Quantity
        hol("PicURL"),           # Item photo URL (mehrere mit | getrennt)
        hol("*ConditionID"),     # Condition ID (Zahl, z. B. 5000)
        hol("*Description"),     # Description
        hol("*Format"),          # Format (FixedPrice)
    ]
    # Artikelmerkmale (C:...) anhängen – kommen so auch im eBay-Entwurf an.
    werte += [hol(quelle) for _, quelle in DRAFT_SPECIFICS]
    return ";".join(werte)

def build_draft_file(folder: str, src_filename: str = DEFAULT_FILENAME,
                     dest_filename: str = DRAFT_FILENAME):
    """Erzeugt aus der vollen Sammeldatei die eBay-Entwurf-Datei (begrenzte Vorlage).

    Gibt (Pfad, Anzahl) zurück. Fehlt die Quelle oder ist sie leer, wird eine evtl.
    vorhandene Entwurf-Datei entfernt und (None, 0) zurückgegeben."""
    src = os.path.join(folder, src_filename)
    dest = os.path.join(folder, dest_filename)
    rows = []
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8-sig") as f:
            rows = [line.rstrip("\r\n") for line in f if _ist_angebotszeile(line)]
    if not rows:
        if os.path.exists(dest):
            os.remove(dest)
        return None, 0
    with open(dest, "w", encoding="utf-8-sig", newline="") as f:
        f.write(DRAFT_INFO_LINE + "\r\n" + DRAFT_HEADER + "\r\n")
        for r in rows:
            f.write(_full_to_draft_row(r) + "\r\n")
    return dest, len(rows)

def remove_draft_file(folder: str, dest_filename: str = DRAFT_FILENAME) -> bool:
    """Entfernt die abgeleitete Entwurf-Datei (z. B. beim Wechsel auf „sofort
    einstellen" oder nach dem Archivieren). True, wenn etwas gelöscht wurde."""
    dest = os.path.join(folder, dest_filename)
    if os.path.exists(dest):
        os.remove(dest)
        return True
    return False

def set_action_all(folder: str, action: str, filename: str = DEFAULT_FILENAME) -> int:
    """Setzt die Aktion (Add/Draft) ALLER Anzeigen in der Sammeldatei auf <action>.

    So gilt die aktuell eingestellte Upload-Art immer für die ganze Datei – auch
    für Anzeigen, die früher mit einer anderen Einstellung erzeugt wurden. Ein
    ungültiger Wert wird sicherheitshalber zu "Draft". Gibt die Anzahl der Zeilen
    zurück (0, wenn es die Datei nicht gibt)."""
    if action not in GUELTIGE_AKTIONEN:
        action = "Draft"
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = [line.rstrip("\r\n") for line in f if _ist_angebotszeile(line)]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\r\n" + HEADER + "\r\n")
        for r in rows:
            f.write(_mit_aktion(_mit_preis_punkt(r), action) + "\r\n")
    return len(rows)
