import os
from datetime import date
from ebay_csv import (build_csv, append_listing, entry_exists, remove_listing,
                      recent_listings, archive_as_file, COLUMNS)

def _parse(data: bytes):
    assert data[:3] == b"\xef\xbb\xbf"            # BOM vorhanden
    text = data.decode("utf-8-sig")
    return text.splitlines()

def test_struktur_bom_und_99_spalten():
    data = build_csv(
        title="Der Hobbit guter Zustand", author="J.R.R. Tolkien",
        book_title="Der Hobbit", language="Deutsch", description="Gut erhalten.",
        price="9.99", condition_id="5000",
        picture_urls=["https://i.ibb.co/abc/1.jpg"],
    )
    lines = _parse(data)
    assert lines[0].startswith("Info;Version=1.0.0;Template=fx_category_template_EBAY_DE")
    header = lines[1].split(";")
    row = lines[2].split(";")
    assert len(header) == 99
    assert len(row) == 99
    assert row[0] == "Add"

def test_felder_an_richtiger_stelle():
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch",
        description="D", price="12.50", condition_id="4000",
        picture_urls=["https://x/1.jpg", "https://x/2.jpg"],
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert row["*Category"] == "261186"
    assert row["*ConditionID"] == "4000"
    assert row["*C:Autor"] == "A"
    assert row["*StartPrice"] == "12.50"
    assert row["PicURL"] == "https://x/1.jpg|https://x/2.jpg"
    assert row["*ReturnsAcceptedOption"] == "ReturnsNotAccepted"

def test_semikolon_und_titel_werden_bereinigt():
    langer_titel = "X" * 100
    data = build_csv(
        title=langer_titel, author="A", book_title="B", language="Deutsch",
        description="Zeile1; mit Semikolon\nund Umbruch", price="9.99",
        condition_id="5000", picture_urls=["https://x/1.jpg"],
    )
    lines = _parse(data)
    assert len(lines[2].split(";")) == 99
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert ";" not in row["*Description"]
    assert len(row["*Title"]) <= 80

def test_formatierung_bleibt_im_export_erhalten():
    # Fett/Kursiv/Unterstrichen aus dem Beschreibungsfeld muss in der CSV ankommen.
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch",
        description="<p><b>Fett</b> und <i>kursiv</i> und <u>unterstrichen</u>.</p>",
        price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"],
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert "<b>" in row["*Description"]
    assert "<i>" in row["*Description"]
    assert "<u>" in row["*Description"]

def test_lange_artikelmerkmale_werden_auf_65_gekuerzt():
    langer_titel = ("Fünfftes Supplement zu seinen Historischen und Genealogischen "
                    "wie auch Geographischen Fragen so viel sich im Jahre 1712 zugetragen hat")
    data = build_csv(
        title="T", author="A", book_title=langer_titel, language="Deutsch",
        description="D", price="9.99", condition_id="5000",
        picture_urls=["https://x/1.jpg"], publisher="X" * 80,
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert len(row["*C:Buchtitel"]) <= 65
    assert len(row["C:Verlag"]) <= 65
    assert " " not in row["*C:Buchtitel"][-1]   # nicht mitten im Wort abgeschnitten

def test_append_listing_sammelt_in_einer_datei(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    path, count = append_listing(folder, title="Buch 1", book_title="Buch 1", **gemeinsam)
    assert count == 1
    path2, count2 = append_listing(folder, title="Buch 2", book_title="Buch 2", **gemeinsam)
    assert path == path2           # gleiche Sammeldatei
    assert count2 == 2
    data = open(path, "rb").read()
    assert data[:3] == b"\xef\xbb\xbf"             # BOM nur einmal am Anfang
    lines = data.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("Info;")
    assert len(lines[1].split(";")) == 99          # genau eine Kopfzeile
    assert lines[2].split(";")[0] == "Add"
    assert lines[3].split(";")[0] == "Add"
    assert len(lines) == 4                          # Info + Kopf + 2 Anzeigen

def test_append_listing_ueberschreibt_bei_gleichem_autor_buchtitel(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="Goethe", book_title="Faust", language="Deutsch",
                     description="D", condition_id="5000", picture_urls=["https://x/1.jpg"])
    # Gleiches Buch (Autor+Buchtitel), aber LEICHT anderer Anzeigentitel + anderer Preis.
    _, count1 = append_listing(folder, title="Faust gebraucht", price="9.99", **gemeinsam)
    path, count2 = append_listing(folder, title="Faust – sehr gut", price="14.99", **gemeinsam)
    assert count1 == 1
    assert count2 == 1                               # ersetzt trotz anderem Anzeigentitel
    lines = open(path, "rb").read().decode("utf-8-sig").splitlines()
    assert len(lines) == 3                           # Info + Kopf + EINE Anzeige
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert row["*StartPrice"] == "14.99"             # der neueste Stand gewann

def test_append_listing_ohne_buchtitel_wird_nicht_zusammengefasst(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    _, c1 = append_listing(folder, title="X", **gemeinsam)
    path, c2 = append_listing(folder, title="Y", **gemeinsam)
    assert c1 == 1 and c2 == 2                        # ohne Buchtitel kein Abgleich

def test_entry_exists(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(language="Deutsch", description="D", price="9.99",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    assert entry_exists(folder, "Goethe", "Faust") is False     # Datei existiert noch nicht
    append_listing(folder, title="Faust gebraucht", author="Goethe",
                   book_title="Faust", **gemeinsam)
    assert entry_exists(folder, "Goethe", "Faust") is True      # gleicher Autor+Buchtitel
    assert entry_exists(folder, "goethe", "  faust ") is True   # Groß/Klein + Leerzeichen egal
    assert entry_exists(folder, "Schiller", "Faust") is False   # anderer Autor
    assert entry_exists(folder, "Goethe", "Werther") is False   # anderer Buchtitel
    assert entry_exists(folder, "Goethe", "") is False          # ohne Buchtitel nie Dublette

def test_remove_listing_entfernt_passende_zeile(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", language="Deutsch", description="D", price="1.00",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Eins", book_title="Eins", **gemeinsam)
    append_listing(folder, title="Zwei", book_title="Zwei", **gemeinsam)
    # Schlüssel ist Autor+Buchtitel, Groß/Klein + Leerzeichen egal.
    assert remove_listing(folder, "a", "  eins ") is True
    titel = {r["title"] for r in recent_listings(folder)}
    assert titel == {"Zwei"}                              # nur "Eins" ist weg
    assert remove_listing(folder, "A", "Eins") is False   # schon entfernt -> nichts mehr

def test_remove_listing_ohne_treffer_und_ohne_datei(tmp_path):
    folder = str(tmp_path)
    assert remove_listing(folder, "A", "Egal") is False   # Datei existiert nicht
    append_listing(folder, title="Da", book_title="Da", author="A", language="Deutsch",
                   description="D", price="1.00", condition_id="5000",
                   picture_urls=["https://x/1.jpg"])
    assert remove_listing(folder, "A", "Anderer") is False  # kein passender Eintrag
    assert remove_listing(folder, "A", "") is False         # ohne Buchtitel kein Treffer
    assert len(recent_listings(folder)) == 1                # nichts gelöscht

def test_recent_listings_neueste_zuerst(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", language="Deutsch", description="D",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    assert recent_listings(folder) == []                  # noch keine Datei
    append_listing(folder, title="Erstes", book_title="Erstes", price="1.00", **gemeinsam)
    append_listing(folder, title="Zweites", book_title="Zweites", price="2.00", **gemeinsam)
    recent = recent_listings(folder)
    assert [r["title"] for r in recent] == ["Zweites", "Erstes"]   # neueste zuerst
    assert recent[0]["price"] == "2.00"
    assert recent[0]["author"] == "A"

def test_recent_listings_limit(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", language="Deutsch", description="D",
                     price="1.00", condition_id="5000", picture_urls=["https://x/1.jpg"])
    for i in range(15):
        append_listing(folder, title=f"Buch {i}", book_title=f"Buch {i}", **gemeinsam)
    assert len(recent_listings(folder, limit=10)) == 10

def test_archive_as_file_benennt_um_und_macht_platz(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Buch 1", book_title="Buch 1", **gemeinsam)
    append_listing(folder, title="Buch 2", book_title="Buch 2", **gemeinsam)
    count, name = archive_as_file(folder, "Romane")
    assert count == 2
    heute = date.today().isoformat()
    assert name == f"eBayClient_{heute}_Romane.csv"
    assert os.path.exists(os.path.join(folder, name))     # Archivdatei da
    assert recent_listings(folder) == []                  # aktive Datei ist weg
    arch = recent_listings(folder, filename=name, limit=50)
    assert {r["title"] for r in arch} == {"Buch 1", "Buch 2"}

def test_archive_as_file_ohne_name_nur_datum(tmp_path):
    folder = str(tmp_path)
    append_listing(folder, title="X", author="A", book_title="B", language="Deutsch",
                   description="D", price="9.99", condition_id="5000",
                   picture_urls=["https://x/1.jpg"])
    _, name = archive_as_file(folder)
    assert name == f"eBayClient_{date.today().isoformat()}.csv"

def test_archive_as_file_vermeidet_namenskollision(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Erst", **gemeinsam)
    _, erste = archive_as_file(folder)
    append_listing(folder, title="Zweit", **gemeinsam)
    _, zweite = archive_as_file(folder)
    assert erste != zweite                                # zweiter Name weicht aus (_2)
    assert zweite.endswith("_2.csv")

def test_listing_stats_zaehlt_und_summiert(tmp_path):
    from ebay_csv import listing_stats
    folder = str(tmp_path)
    assert listing_stats(folder) == {"count": 0, "total": 0.0}   # keine Datei
    gemeinsam = dict(author="A", language="Deutsch", description="D",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Eins", book_title="Eins", price="9.99", **gemeinsam)
    append_listing(folder, title="Zwei", book_title="Zwei", price="14.50", **gemeinsam)
    s = listing_stats(folder)
    assert s["count"] == 2
    assert s["total"] == 24.49

def test_archive_as_file_leer_macht_nichts(tmp_path):
    assert archive_as_file(str(tmp_path)) == (0, "")      # gar keine Datei

def test_action_draft_steht_in_der_zeile():
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch", description="D",
        price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"],
        action="Draft",
    )
    lines = _parse(data)
    assert lines[2].split(";")[0] == "Draft"              # Entwurf statt Add

def test_ungueltige_action_faellt_auf_add_zurueck():
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch", description="D",
        price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"],
        action="Quatsch",
    )
    assert _parse(data)[2].split(";")[0] == "Add"

def test_draft_zeilen_werden_mitgezaehlt_und_erkannt(tmp_path):
    from ebay_csv import listing_stats
    folder = str(tmp_path)
    gemeinsam = dict(language="Deutsch", description="D", condition_id="5000",
                     picture_urls=["https://x/1.jpg"], action="Draft")
    append_listing(folder, title="Eins", author="A", book_title="Eins",
                   price="9.99", **gemeinsam)
    # Draft-Zeilen müssen genauso zählen/erkannt werden wie Add-Zeilen.
    assert listing_stats(folder)["count"] == 1
    assert recent_listings(folder)[0]["title"] == "Eins"
    assert entry_exists(folder, "A", "Eins") is True

def _aktionen(folder, filename="ebay-anzeigen.csv"):
    import os
    with open(os.path.join(folder, filename), encoding="utf-8-sig") as f:
        return [ln.split(";")[0] for ln in f.read().splitlines()
                if ln.startswith(("Add;", "Draft;"))]

def test_append_listing_vereinheitlicht_aktion(tmp_path):
    folder = str(tmp_path)
    g = dict(language="Deutsch", description="D", price="1.00", condition_id="5000",
             picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Alt", author="A", book_title="Alt", action="Add", **g)
    # Neue Zeile als Draft -> die alte Add-Zeile wird ebenfalls auf Draft gesetzt.
    append_listing(folder, title="Neu", author="B", book_title="Neu", action="Draft", **g)
    assert set(_aktionen(folder)) == {"Draft"}

def test_set_action_all_setzt_alle_zeilen(tmp_path):
    from ebay_csv import set_action_all
    folder = str(tmp_path)
    g = dict(language="Deutsch", description="D", price="1.00", condition_id="5000",
             picture_urls=["https://x/1.jpg"], action="Add")
    append_listing(folder, title="A", author="A", book_title="A", **g)
    append_listing(folder, title="B", author="B", book_title="B", **g)
    assert _aktionen(folder) == ["Add", "Add"]
    assert set_action_all(folder, "Draft") == 2
    assert set(_aktionen(folder)) == {"Draft"}
    assert set_action_all(folder, "Quatsch") == 2          # ungültig -> sicher Draft
    assert set(_aktionen(folder)) == {"Draft"}
    assert set_action_all(str(tmp_path / "leer"), "Add") == 0   # ohne Datei: 0

def test_build_draft_file_erzeugt_ebay_entwurf_vorlage(tmp_path):
    from ebay_csv import (build_draft_file, DRAFT_FILENAME, DRAFT_HEADER,
                          DRAFT_INFO_LINE)
    folder = str(tmp_path)
    append_listing(folder, title="Der Hobbit", author="Tolkien", book_title="Der Hobbit",
                   language="Deutsch", description="Gut erhalten.", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg", "https://x/2.jpg"],
                   action="Draft")
    path, count = build_draft_file(folder)
    assert count == 1
    assert path.endswith(DRAFT_FILENAME)
    lines = open(path, "r", encoding="utf-8-sig").read().splitlines()
    assert lines[0] == DRAFT_INFO_LINE                 # #INFO-Zeile von eBay
    assert lines[1] == DRAFT_HEADER                    # Action(...) OHNE *, 11 Spalten
    assert len(DRAFT_HEADER.split(";")) == 11
    row = lines[2].split(";")
    assert len(row) == 11
    assert row[0] == "Draft"                           # Aktion = Draft
    assert row[2] == "261186"                          # Category ID (Bücher)
    assert row[3] == "Der Hobbit"                      # Title
    assert row[5] == "9.99"                            # Price
    assert row[6] == "1"                               # Quantity
    assert row[7] == "https://x/1.jpg|https://x/2.jpg" # Fotos mit | getrennt
    assert row[8] == "5000"                            # Condition ID (Zahl)
    assert row[10] == "FixedPrice"                     # Format

def test_build_draft_file_ohne_quelle_entfernt_zieldatei(tmp_path):
    from ebay_csv import build_draft_file, DRAFT_FILENAME
    folder = str(tmp_path)
    # Eine veraltete Entwurf-Datei liegt noch da, aber es gibt keine Sammeldatei.
    ziel = os.path.join(folder, DRAFT_FILENAME)
    open(ziel, "w").write("alt")
    path, count = build_draft_file(folder)
    assert (path, count) == (None, 0)
    assert not os.path.exists(ziel)                    # veraltete Datei ist weg

def test_remove_draft_file(tmp_path):
    from ebay_csv import remove_draft_file, DRAFT_FILENAME
    folder = str(tmp_path)
    ziel = os.path.join(folder, DRAFT_FILENAME)
    assert remove_draft_file(folder) is False          # nichts da -> False
    open(ziel, "w").write("x")
    assert remove_draft_file(folder) is True
    assert not os.path.exists(ziel)

def test_build_draft_file_preis_komma_wird_punkt(tmp_path):
    from ebay_csv import build_draft_file
    folder = str(tmp_path)
    append_listing(folder, title="T", author="A", book_title="T", language="Deutsch",
                   description="D", price="9999,99", condition_id="5000",
                   picture_urls=["https://x/1.jpg"], action="Draft")
    path, _ = build_draft_file(folder)
    row = open(path, "r", encoding="utf-8-sig").read().splitlines()[2].split(";")
    assert row[5] == "9999.99"          # Komma -> Punkt (eBay braucht Punkt)

def test_preis_punkt_varianten():
    from ebay_csv import _preis_punkt
    assert _preis_punkt("9,99") == "9.99"
    assert _preis_punkt("9.99") == "9.99"
    assert _preis_punkt("1.234,56") == "1234.56"   # deutsches Tausenderformat
    assert _preis_punkt("  12,50 ") == "12.50"

def test_volle_datei_speichert_preis_mit_punkt(tmp_path):
    # Preis mit Komma eingegeben -> in der vollen Datei steht er mit Punkt.
    from ebay_csv import COLUMNS
    folder = str(tmp_path)
    append_listing(folder, title="T", author="A", book_title="T", language="Deutsch",
                   description="D", price="12,50", condition_id="5000",
                   picture_urls=["https://x/1.jpg"])
    i = COLUMNS.index("*StartPrice")
    zeile = [ln for ln in open(folder + "/ebay-anzeigen.csv", encoding="utf-8-sig")
             .read().splitlines() if ln.startswith(("Add;", "Draft;"))][0]
    assert zeile.split(";")[i] == "12.50"

def test_set_action_all_heilt_komma_preis(tmp_path):
    # Eine alte Zeile mit Komma-Preis wird beim Neuschreiben auf Punkt geheilt.
    from ebay_csv import set_action_all, COLUMNS, INFO_LINE, HEADER, build_row
    folder = str(tmp_path)
    row = build_row(title="T", author="A", book_title="T", language="Deutsch",
                    description="D", price="9.99", condition_id="5000",
                    picture_urls=["https://x/1.jpg"])
    i = COLUMNS.index("*StartPrice")
    cells = row.split(";"); cells[i] = "9999,99"          # künstlich Komma einsetzen
    with open(folder + "/ebay-anzeigen.csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(INFO_LINE + "\r\n" + HEADER + "\r\n" + ";".join(cells) + "\r\n")
    set_action_all(folder, "Draft")
    zeile = [ln for ln in open(folder + "/ebay-anzeigen.csv", encoding="utf-8-sig")
             .read().splitlines() if ln.startswith(("Add;", "Draft;"))][0]
    assert zeile.split(";")[i] == "9999.99"
