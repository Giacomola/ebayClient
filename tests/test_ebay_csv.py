import os
from datetime import date
from ebay_csv import (build_csv, append_listing, entry_exists,
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
