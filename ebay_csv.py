"""Erzeugt eine eBay-File-Exchange-CSV (Kategorie-Vorlage Bücher) für genau ein Buch."""

ACTION = "*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)"
INFO_LINE = "Info;Version=1.0.0;Template=fx_category_template_EBAY_DE"

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

def build_csv(*, title, author, book_title, language, description, price,
              condition_id, picture_urls, publisher="", publication_year="",
              book_format="", location="Berlin", shipping_service="DE_DHLPaket",
              shipping_cost="5.49", dispatch_time_max="3", custom_label="") -> bytes:
    values = {
        ACTION: "Add",
        "CustomLabel": _clean(custom_label),
        "*Category": "261186",
        "*Title": _clean(title)[:80],
        "*ConditionID": _clean(condition_id),
        "*C:Autor": _clean(author),
        "*C:Buchtitel": _clean(book_title),
        "*C:Sprache": _clean(language),
        "C:Verlag": _clean(publisher),
        "C:Erscheinungsjahr": _clean(publication_year),
        "C:Format": _clean(book_format),
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
    header = ";".join(COLUMNS)
    row = ";".join(values.get(col, "") for col in COLUMNS)
    text = "\r\n".join([INFO_LINE, header, row]) + "\r\n"
    return ("﻿" + text).encode("utf-8")
