"""Erzeugt eine eBay-File-Exchange-CSV (Kategorie-Vorlage Bücher).

Unterstützt eine einzelne Anzeige (build_csv) sowie das Sammeln mehrerer
Anzeigen in einer gemeinsamen Datei (append_listing)."""
import os

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

HEADER = ";".join(COLUMNS)

def _values(*, title, author, book_title, language, description, price,
            condition_id, picture_urls, publisher="", publication_year="",
            book_format="", location="Berlin", shipping_service="DE_DHLPaket",
            shipping_cost="5.49", dispatch_time_max="3", custom_label="") -> dict:
    return {
        ACTION: "Add",
        "CustomLabel": _clean(custom_label),
        "*Category": "261186",
        "*Title": _limit(_clean(title), 80),
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

def _count_listings(path: str) -> int:
    """Zählt die enthaltenen Anzeigen (Datenzeilen) in einer Sammel-CSV."""
    with open(path, "r", encoding="utf-8-sig") as f:
        return sum(1 for line in f if line.startswith("Add;"))

def append_listing(folder: str, filename: str = DEFAULT_FILENAME, **kwargs):
    """Hängt eine Anzeige an die gemeinsame CSV im Ordner an.

    Legt die Datei mit BOM, Info- und Kopfzeile an, falls sie noch nicht
    existiert. Gibt (Pfad, Anzahl der Anzeigen) zurück."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    new_file = not os.path.exists(path)
    encoding = "utf-8-sig" if new_file else "utf-8"
    with open(path, "a", encoding=encoding, newline="") as f:
        if new_file:
            f.write(INFO_LINE + "\r\n" + HEADER + "\r\n")
        f.write(build_row(**kwargs) + "\r\n")
    return path, _count_listings(path)
