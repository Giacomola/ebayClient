from ebay_csv import (build_csv, append_listing, title_exists,
                      recent_listings, archive_listings, ARCHIVE_FILENAME, COLUMNS)

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
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    path, count = append_listing(folder, title="Buch 1", **gemeinsam)
    assert count == 1
    path2, count2 = append_listing(folder, title="Buch 2", **gemeinsam)
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

def test_append_listing_ueberschreibt_bei_gleichem_titel(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    # Gleiche Anzeige zweimal mit unterschiedlichem Preis speichern.
    _, count1 = append_listing(folder, title="Gleicher Titel", price="9.99", **gemeinsam)
    path, count2 = append_listing(folder, title="Gleicher Titel", price="14.99", **gemeinsam)
    assert count1 == 1
    assert count2 == 1                               # nicht angehängt, sondern ersetzt
    lines = open(path, "rb").read().decode("utf-8-sig").splitlines()
    assert len(lines) == 3                           # Info + Kopf + EINE Anzeige
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert row["*StartPrice"] == "14.99"             # der neueste Stand gewann

def test_append_listing_leerer_titel_wird_nicht_zusammengefasst(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    _, c1 = append_listing(folder, title="", **gemeinsam)
    path, c2 = append_listing(folder, title="", **gemeinsam)
    assert c1 == 1 and c2 == 2                        # leere Titel zählen nicht als Dublette

def test_title_exists(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    assert title_exists(folder, "Irgendwas") is False     # Datei existiert noch nicht
    append_listing(folder, title="Mein Buch", **gemeinsam)
    assert title_exists(folder, "Mein Buch") is True
    assert title_exists(folder, "Anderes Buch") is False
    assert title_exists(folder, "") is False              # leerer Titel nie eine Dublette

def test_recent_listings_neueste_zuerst(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     condition_id="5000", picture_urls=["https://x/1.jpg"])
    assert recent_listings(folder) == []                  # noch keine Datei
    append_listing(folder, title="Erstes", price="1.00", **gemeinsam)
    append_listing(folder, title="Zweites", price="2.00", **gemeinsam)
    recent = recent_listings(folder)
    assert [r["title"] for r in recent] == ["Zweites", "Erstes"]   # neueste zuerst
    assert recent[0]["price"] == "2.00"
    assert recent[0]["author"] == "A"

def test_recent_listings_limit(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="1.00", condition_id="5000", picture_urls=["https://x/1.jpg"])
    for i in range(15):
        append_listing(folder, title=f"Buch {i}", **gemeinsam)
    assert len(recent_listings(folder, limit=10)) == 10

def test_archive_listings_verschiebt_und_leert(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Buch 1", **gemeinsam)
    append_listing(folder, title="Buch 2", **gemeinsam)
    moved = archive_listings(folder)
    assert moved == 2
    assert recent_listings(folder) == []                  # aktive Datei ist weg/leer
    arch = recent_listings(folder, filename=ARCHIVE_FILENAME, limit=50)
    assert {r["title"] for r in arch} == {"Buch 1", "Buch 2"}

def test_archive_listings_haengt_an_bestehendes_archiv_an(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    append_listing(folder, title="Erst", **gemeinsam)
    archive_listings(folder)
    append_listing(folder, title="Zweit", **gemeinsam)
    archive_listings(folder)
    arch = recent_listings(folder, filename=ARCHIVE_FILENAME, limit=50)
    assert {r["title"] for r in arch} == {"Erst", "Zweit"}

def test_archive_listings_leer_macht_nichts(tmp_path):
    assert archive_listings(str(tmp_path)) == 0           # gar keine Datei
