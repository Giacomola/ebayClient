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

# eBay-Längengrenzen: Anzeigentitel 80, Artikelmerkmale (C:...) je 65 Zeichen.
SPECIFIC_MAX = 65

def title_for(title) -> str:
    """Der Anzeigentitel genau so, wie er in der CSV landet (für den Dubletten-Abgleich)."""
    return _limit(_clean(title), 80)

HEADER = ";".join(COLUMNS)

def _values(*, title, author, book_title, language, description, price,
            condition_id, picture_urls, publisher="", publication_year="",
            book_format="", location="Berlin", shipping_service="DE_DHLPaket",
            shipping_cost="5.49", dispatch_time_max="3", custom_label="") -> dict:
    return {
        ACTION: "Add",
        "CustomLabel": _clean(custom_label),
        "*Category": "261186",
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
        "*StartPrice": _clean(price),
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

# Position der Titel-Spalte in einer Datenzeile (0-basiert) – für den Dubletten-Abgleich.
_TITLE_INDEX = COLUMNS.index("*Title")

def title_exists(folder: str, title, filename: str = DEFAULT_FILENAME) -> bool:
    """Sagt, ob in der Sammeldatei schon eine Anzeige mit diesem Titel steht.

    Leerer Titel zählt nie als Dublette."""
    target = title_for(title)
    if not target:
        return False
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8-sig") as f:
        return any(line.startswith("Add;")
                   and line.rstrip("\r\n").split(";")[_TITLE_INDEX] == target
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
        count = sum(1 for line in f if line.startswith("Add;"))
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
            if line.startswith("Add;"):
                cells = line.rstrip("\r\n").split(";")
                rows.append({"title": cells[idx_title], "author": cells[idx_author],
                             "price": cells[idx_price]})
    rows.reverse()  # neueste zuerst
    return rows[:limit]

def append_listing(folder: str, filename: str = DEFAULT_FILENAME, **kwargs):
    """Fügt eine Anzeige zur gemeinsamen CSV im Ordner hinzu.

    Gibt es bereits eine Anzeige mit GLEICHEM (nicht-leerem) Titel, wird sie
    ersetzt statt eine zweite Zeile anzuhängen – so sammeln sich keine Dubletten.
    Legt die Datei mit BOM, Info- und Kopfzeile an, falls sie noch nicht
    existiert. Gibt (Pfad, Anzahl der Anzeigen) zurück."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    new_row = build_row(**kwargs)
    new_title = new_row.split(";")[_TITLE_INDEX]

    # Vorhandene Datenzeilen einlesen (Info-/Kopfzeile werden neu geschrieben).
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig") as f:
            rows = [line.rstrip("\r\n") for line in f if line.startswith("Add;")]

    # Bei gleichem, nicht-leerem Titel die alte Zeile entfernen (sie wird ersetzt).
    if new_title:
        rows = [r for r in rows if r.split(";")[_TITLE_INDEX] != new_title]
    rows.append(new_row)

    # Komplette Datei neu schreiben: BOM + Info + Kopf + alle Datenzeilen.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\r\n" + HEADER + "\r\n")
        for r in rows:
            f.write(r + "\r\n")
    return path, len(rows)
