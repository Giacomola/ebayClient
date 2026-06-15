let selectedFiles = [];

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

// Zeigt die 🌐-Abzeichen nur an den Feldern, die aus der Websuche stammen.
function applyBadges(keys) {
  document.querySelectorAll(".web-badge").forEach((b) => {
    b.hidden = !keys.includes(b.dataset.key);
  });
}
// Listet die Quellen als anklickbare Links.
function renderSources(sources) {
  const box = $("sources-box");
  const list = $("sources-list");
  list.innerHTML = "";
  for (const s of sources || []) {
    if (!s.url) continue;
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = s.url; a.target = "_blank"; a.rel = "noopener";
    a.textContent = s.title || s.url;
    li.appendChild(a);
    list.appendChild(li);
  }
  box.hidden = list.children.length === 0;
}
// Zeigt zwei anklickbare Titelvorschläge. Ein Klick übernimmt den Titel ins Feld.
// Sind beide gleich (oder fehlt einer), werden keine Vorschläge angezeigt.
function renderTitleOptions(t1, t2) {
  const box = $("title-suggestions");
  const uniq = [...new Set([t1, t2].map((s) => (s || "").trim()).filter(Boolean))];
  if (uniq.length < 2) { box.hidden = true; return; }
  $("title-opt-1").textContent = uniq[0];
  $("title-opt-2").textContent = uniq[1];
  box.hidden = false;
}
function chooseTitle(el) {
  $("f-title").value = el.textContent;
  saveFieldsSoon();
}
// Zeigt nur die gefundenen Beispielpreise mit Quelle – bewusst keine Empfehlung.
function renderPrice(d) {
  $("price-box").hidden = false;
  const body = $("price-comparables");   // <tbody> der Preistabelle
  body.innerHTML = "";
  const items = d.comparables || [];
  for (const c of items) {
    const tr = document.createElement("tr");
    // Spalte 1: Preis (fett, in einer Zeile).
    const tdPreis = document.createElement("td");
    tdPreis.className = "price-cell";
    tdPreis.textContent = c.price || "—";
    // Spalte 2: Angebot als anklickbarer Link (Titel).
    const tdAngebot = document.createElement("td");
    const titel = c.title || "Angebot";
    if (c.url) {
      const a = document.createElement("a");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = titel;
      tdAngebot.appendChild(a);
    } else {
      tdAngebot.textContent = titel;
    }
    // Spalte 3: Quelle (z. B. ZVAB).
    const tdQuelle = document.createElement("td");
    tdQuelle.textContent = c.source || "";
    tr.appendChild(tdPreis);
    tr.appendChild(tdAngebot);
    tr.appendChild(tdQuelle);
    body.appendChild(tr);
  }
  // Leere Tabelle ausblenden, damit nur der Hinweistext sichtbar bleibt.
  $("price-table").hidden = items.length === 0;
  $("price-status").textContent =
    items.length === 0 ? "Keine Beispielpreise gefunden." : "";
  $("price-note").textContent = d.note || "";
}
// Holt die Beispielpreise anhand der aktuellen Feldwerte.
async function fetchPrice() {
  const btn = $("price-btn");
  if (btn) btn.disabled = true;  // Doppelklick während der Suche verhindern
  $("price-box").hidden = false;
  $("price-status").textContent = "💶 suche Beispielpreise …";
  $("price-comparables").innerHTML = "";
  $("price-note").textContent = "";
  const body = {};
  for (const key of ["title", "author", "book_title", "language",
                     "publication_year", "publisher", "book_format"]) {
    body[key] = $("f-" + key).value;
  }
  let r, d;
  try {
    r = await fetch("/api/price", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    d = await r.json();
  } catch (e) {
    $("price-status").textContent = "Preissuche nicht möglich.";
    return;
  } finally {
    if (btn) btn.disabled = false;
  }
  if (!r.ok) { $("price-status").textContent = d.error || "Preise nicht ermittelbar."; return; }
  renderPrice(d);
  status("");  // Hauptzeile leeren – die Preisbox zeigt das Ergebnis selbst
}

// Hängt einen Listener nur an, wenn das Element existiert. So legt ein einzelnes
// fehlendes Element (z. B. nach einer veralteten Seite) nie die ganze Seite lahm.
function on(id, event, handler) {
  const el = $(id);
  if (el) el.addEventListener(event, handler);
}

// Lässt ein Textfeld in der Höhe automatisch mit dem Inhalt wachsen.
function autosize(el) {
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
}

// Schriftgröße der ganzen App – einfach per A−/A+ verstellbar, bleibt gespeichert.
const FONT_KEY = "fontPx";
let fontPx = parseInt(localStorage.getItem(FONT_KEY) || "18", 10);
function applyFont() {
  document.documentElement.style.fontSize = fontPx + "px";
  localStorage.setItem(FONT_KEY, fontPx);
}
applyFont();
$("font-inc").addEventListener("click", () => { fontPx = Math.min(30, fontPx + 2); applyFont(); });
$("font-dec").addEventListener("click", () => { fontPx = Math.max(12, fontPx - 2); applyFont(); });

// Inhaltsbreite – wie die Schrift per ↔−/↔+ in festen Stufen verstellbar,
// bleibt im Browser gespeichert. Stufen in Pixeln (720 = wie ursprünglich).
const WIDTH_KEY = "pageWidthPx";
const WIDTH_STEPS = [720, 900, 1100, 1400];
let widthPx = parseInt(localStorage.getItem(WIDTH_KEY) || "720", 10);
function applyWidth() {
  document.documentElement.style.setProperty("--page-width", widthPx + "px");
  localStorage.setItem(WIDTH_KEY, widthPx);
}
function stepWidth(dir) {
  // zur nächsten Stufe in Richtung dir (+1 breiter, −1 schmaler) springen
  let i = WIDTH_STEPS.indexOf(widthPx);
  if (i === -1) i = 0;                       // unbekannter Wert → von vorn
  i = Math.min(WIDTH_STEPS.length - 1, Math.max(0, i + dir));
  widthPx = WIDTH_STEPS[i];
  applyWidth();
}
applyWidth();
on("width-inc", "click", () => stepWidth(1));
on("width-dec", "click", () => stepWidth(-1));

// --- Automatisches Speichern des Arbeitsstands (Entwurf) -------------------
const RESULT_FIELDS = ["title", "author", "book_title", "language", "publisher",
                       "publication_year", "book_format"];

// Sammelt alle Textfelder und speichert sie (kurz verzögert, damit nicht bei
// jedem Tastendruck gespeichert wird).
let saveTimer = null;
function saveFieldsSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveFieldsNow, 600);
}
function currentFields() {
  const fields = {};
  for (const key of RESULT_FIELDS) fields[key] = $("f-" + key).value;
  fields.description = $("f-description").innerHTML;
  fields.price = $("f-price").value;
  fields.condition_id = $("f-condition").value;
  return fields;
}
async function saveFieldsNow() {
  await fetch("/api/draft", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields: currentFields(),
                           result_visible: !$("result").hidden }),
  });
}
// Speichert die aktuellen Fotos als Entwurf (nur bei Änderung der Fotoauswahl).
// Merkt sich die zuletzt bekannte Foto-Version. So lösen eigene Änderungen am PC
// keine unnötige Neu-Ladung aus – nur Änderungen von anderswo (Handy) tun das.
let knownImagesRev = 0;
async function saveImagesNow() {
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  const r = await fetch("/api/draft/images", { method: "POST", body: fd });
  try { knownImagesRev = (await r.json()).images_rev ?? knownImagesRev; } catch (e) {}
}

// Holt die Fotos aus dem Entwurf in die Ansicht (für die Live-Übernahme vom Handy).
async function reloadImagesFromDraft() {
  const draft = await (await fetch("/api/draft")).json();
  knownImagesRev = draft.images_rev ?? knownImagesRev;
  selectedFiles = (draft.images || []).map((im, i) =>
    dataURLtoFile(im.data_url, "foto-" + (i + 1)));
  renderThumbs();
}

// Fragt regelmäßig die leichte Foto-Version ab. Hat sich etwas geändert (z. B. ein
// Foto vom Handy), werden die Fotos in die Computerseite übernommen.
async function pollPhoneImages() {
  try {
    const d = await (await fetch("/api/draft/images-rev")).json();
    if (d.images_rev !== knownImagesRev) {
      await reloadImagesFromDraft();
      status("📱 Foto vom Handy übernommen.");
    }
  } catch (e) { /* offline o. Ä. – einfach beim nächsten Mal erneut versuchen */ }
}
setInterval(pollPhoneImages, 2500);
// Baut aus einem gespeicherten Base64-Foto wieder eine Datei (für den Upload).
function dataURLtoFile(dataURL, name) {
  const [head, b64] = dataURL.split(",");
  const mime = (head.match(/:(.*?);/) || [])[1] || "image/jpeg";
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new File([bytes], name, { type: mime });
}

// Ab wie vielen Fotos die Analyse-Auswahl erscheint, und wie viele höchstens
// analysiert werden (jedes Foto kostet Token – darum die Obergrenze).
const ANALYSE_AB = 2;     // mehr als 2 Fotos → Auswahl anzeigen
const ANALYSE_MAX = 5;    // höchstens 5 Fotos analysieren
const ANALYSE_STD = 3;    // beim Start die ersten 3 vorauswählen

// Setzt für neue Fotos (ohne gesetzte Wahl) den Standard: erste 3 an, Rest aus.
function setzeAnalyseStandards() {
  selectedFiles.forEach((f, i) => { if (f.analyze === undefined) f.analyze = i < ANALYSE_STD; });
}
// Wie viele Fotos sind aktuell zum Analysieren angehakt?
function anzahlAnalyse() { return selectedFiles.filter((f) => f.analyze).length; }
// Welche Fotos gehen an die KI? Bei ≤2 Fotos einfach alle, sonst nur die angehakten.
function fotosFuerAnalyse() {
  if (selectedFiles.length <= ANALYSE_AB) return selectedFiles;
  return selectedFiles.filter((f) => f.analyze);
}
// „Anzeige erstellen" nur freigeben, wenn mindestens ein Foto analysiert wird.
function aktualisiereGenerateKnopf() {
  $("generate-btn").disabled = fotosFuerAnalyse().length === 0;
}

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  const auswahl = selectedFiles.length > ANALYSE_AB;   // Häkchen erst ab >2 Fotos
  if (auswahl) setzeAnalyseStandards();
  selectedFiles.forEach((file, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "thumb";
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    const del = document.createElement("button");
    del.type = "button";
    del.className = "thumb-del";
    del.textContent = "×";
    del.title = "Foto entfernen";
    del.addEventListener("click", () => removeFile(idx));
    wrap.appendChild(img);
    wrap.appendChild(del);
    if (auswahl) {
      // Kleines Häkchen „analysieren" unten auf dem Bild.
      const lab = document.createElement("label");
      lab.className = "thumb-analyze";
      lab.title = "Dieses Foto von der KI analysieren lassen";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = !!file.analyze;
      cb.addEventListener("change", () => toggleAnalyse(idx, cb));
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode("🔍"));
      wrap.appendChild(lab);
      if (!file.analyze) wrap.classList.add("analyze-off");   // nicht gewählte abblenden
    }
    box.appendChild(wrap);
  });
  $("analyze-hint").hidden = !auswahl;
  aktualisiereGenerateKnopf();
}

// Häkchen umschalten – aber nie mehr als ANALYSE_MAX Fotos gleichzeitig anhaken.
function toggleAnalyse(idx, cb) {
  if (cb.checked && anzahlAnalyse() >= ANALYSE_MAX) {
    cb.checked = false;
    status(`Es werden höchstens ${ANALYSE_MAX} Fotos analysiert. `
           + "Nimm zuerst bei einem anderen Foto das Häkchen weg.");
    return;
  }
  selectedFiles[idx].analyze = cb.checked;
  renderThumbs();   // Abblendung/Knopf-Status auffrischen
}

// Entfernt ein einzelnes Foto (Klick auf das ×) und hält den Entwurf synchron.
function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  renderThumbs();
  saveImagesNow();
}

function addFiles(fileList) {
  for (const f of fileList) if (f.type.startsWith("image/")) selectedFiles.push(f);
  renderThumbs();
  saveImagesNow();  // Fotos sofort in den Entwurf übernehmen
}

const dz = $("drop-zone");
// Verhindert, dass der Browser ein Foto, das NEBEN die Ablagefläche gezogen wird,
// einfach als ganze Seite öffnet. Fällt das Foto irgendwo ins Fenster, nehmen wir
// es trotzdem auf – so kann der Vater nicht „danebenziehen".
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  e.preventDefault();
  // Treffer in die Ablagefläche wird dort eigens behandelt (sonst doppelt).
  if (dz.contains(e.target)) return;
  if (e.dataTransfer && e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
});
dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
dz.addEventListener("drop", (e) => {
  e.preventDefault(); dz.classList.remove("drag"); addFiles(e.dataTransfer.files);
});
$("choose-btn").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", (e) => addFiles(e.target.files));

// „Per Handy hochladen": zeigt QR-Code + WLAN-Adresse dieses PCs an.
on("handy-btn", "click", async () => {
  const qr = $("handy-qr"), urlEl = $("handy-url"), fehler = $("handy-fehler");
  qr.innerHTML = ""; urlEl.textContent = ""; fehler.hidden = true;
  let d;
  try {
    d = await (await fetch("/api/handy-zugang")).json();
  } catch (e) {
    d = { error: "Adresse konnte nicht ermittelt werden." };
  }
  if (!d.url) {
    fehler.textContent = d.error || "Keine WLAN-Adresse gefunden.";
    fehler.hidden = false;
  } else {
    if (d.qr_svg) qr.innerHTML = d.qr_svg;   // QR als SVG direkt einbetten
    urlEl.textContent = d.url;
  }
  $("handy-dialog").showModal();
});

const generateBtn = $("generate-btn");
generateBtn.addEventListener("click", async () => {
  // Knopf sperren, solange die Erstellung läuft – sonst stapeln sich bei einem
  // zweiten Klick mehrere minutenlange Aufrufe und die Seite scheint zu hängen.
  generateBtn.disabled = true;
  status("🔎 recherchiere im Netz … (das kann ~30–60 Sekunden dauern)");
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
  try {
    const fd = new FormData();
    fotosFuerAnalyse().forEach((f) => fd.append("images", f));  // nur ausgewählte Fotos analysieren
    const r = await fetch("/api/generate", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) { status(data.error || "Fehler bei der Analyse."); return; }
    for (const key of ["title", "author", "book_title", "language", "publisher",
                       "publication_year", "book_format"]) {
      $("f-" + key).value = data[key] || "";
    }
    $("f-description").innerHTML = data.description || "";  // HTML gerendert anzeigen
    renderTitleOptions(data.title, data.title_alt);  // zwei Titelvorschläge zur Auswahl
    applyBadges(data.web_sourced_fields || []);
    renderSources(data.sources || []);
    $("result").hidden = false;
    status("Text fertig – ich suche jetzt noch Beispielpreise …");
    saveFieldsNow();  // Ergebnis sofort in den Entwurf übernehmen
    fetchPrice();     // Preisrecherche automatisch anstoßen (läuft im Hintergrund)
  } catch (e) {
    // Bricht der Aufruf ab (Netzfehler/Timeout), bleibt die Seite bedienbar
    // und zeigt eine klare Meldung statt für immer „recherchiere …".
    status("Die Erstellung ist fehlgeschlagen. Bitte erneut versuchen.");
  } finally {
    generateBtn.disabled = false;
  }
});

// Preissuche nur auf Knopfdruck (sie dauert länger und ist nur eine Empfehlung).
on("price-btn", "click", fetchPrice);

// Klick auf einen der beiden Titelvorschläge übernimmt ihn ins Titel-Feld.
on("title-opt-1", "click", (e) => chooseTitle(e.currentTarget));
on("title-opt-2", "click", (e) => chooseTitle(e.currentTarget));

// Jede Änderung in den Ergebnis-Feldern wird (verzögert) gespeichert.
for (const key of RESULT_FIELDS) $("f-" + key).addEventListener("input", saveFieldsSoon);
$("f-price").addEventListener("input", saveFieldsSoon);
$("f-condition").addEventListener("change", saveFieldsSoon);
$("f-description").addEventListener("input", saveFieldsSoon);

// --- Formatierung der Beschreibung (Fett/Kursiv/Unterstrichen) -------------
// execCommand ist zwar veraltet, aber in allen Browsern vorhanden und für diesen
// einfachen Zweck robust. styleWithCSS=false sorgt für saubere <b>/<i>/<u>-Tags
// (statt style="..."), die eBay zuverlässig anzeigt und kein Semikolon enthalten.
try { document.execCommand("styleWithCSS", false, false); } catch (e) { /* egal */ }

const richPopup = $("rich-popup");
const richField = $("f-description");

// Gibt den markierten Bereich zurück – aber nur, wenn echter Text INNERHALB des
// Beschreibungsfeldes markiert ist (sonst null → Leiste bleibt verborgen).
function markierungImFeld() {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
  const range = sel.getRangeAt(0);
  if (!richField.contains(range.commonAncestorContainer)) return null;
  if (!sel.toString().trim()) return null;
  return range;
}

// Zeigt die Leiste über der Markierung an (oder verbirgt sie).
function aktualisiereFormatLeiste() {
  const range = markierungImFeld();
  if (!range) { richPopup.hidden = true; return; }
  richPopup.hidden = false;   // erst sichtbar machen, dann Maße messen
  const rect = range.getBoundingClientRect();
  const ph = richPopup.offsetHeight || 34;
  const pw = richPopup.offsetWidth || 120;
  let top = rect.top - ph - 6;
  if (top < 4) top = rect.bottom + 6;                       // kein Platz oben → darunter
  let left = Math.max(4, Math.min(rect.left, window.innerWidth - pw - 4));
  richPopup.style.top = top + "px";
  richPopup.style.left = left + "px";
}
document.addEventListener("selectionchange", aktualisiereFormatLeiste);
// Beim Scrollen mitführen, solange die Leiste sichtbar ist.
window.addEventListener("scroll", () => { if (!richPopup.hidden) aktualisiereFormatLeiste(); }, true);

function richBefehl(cmd) {
  document.execCommand(cmd, false, null);
  saveFieldsSoon();              // formatiertes HTML in den Entwurf übernehmen
  aktualisiereFormatLeiste();    // Leiste an die (noch bestehende) Markierung anpassen
}
// mousedown + preventDefault: der Knopf nimmt die Textmarkierung NICHT weg.
on("fmt-bold", "mousedown", (e) => { e.preventDefault(); richBefehl("bold"); });
on("fmt-italic", "mousedown", (e) => { e.preventDefault(); richBefehl("italic"); });
on("fmt-underline", "mousedown", (e) => { e.preventDefault(); richBefehl("underline"); });

// „Neuen Fall starten": alles leeren und den gespeicherten Entwurf zurücksetzen.
on("new-case-btn", "click", async () => {
  selectedFiles = [];
  renderThumbs();
  for (const key of RESULT_FIELDS) $("f-" + key).value = "";
  $("f-description").innerHTML = "";
  $("f-price").value = "9.99";
  $("f-condition").value = "5000";
  $("result").hidden = true;
  $("title-suggestions").hidden = true;
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
  $("save-success").hidden = true;
  $("show-entry-btn").hidden = true;
  await fetch("/api/draft/clear", { method: "POST" });
  status("Neuer Fall – bereit für die nächsten Fotos.");
});

// Zeigt unten die zuletzt gespeicherten Anzeigen aus der Sammeldatei.
async function loadRecent() {
  let data;
  try {
    data = await (await fetch("/api/listings")).json();
  } catch (e) {
    return;  // ohne Liste ist die App weiter benutzbar
  }
  const list = $("recent-list");
  list.innerHTML = "";
  for (const item of data.listings || []) {
    const li = document.createElement("li");
    const preis = item.price ? ` – ${item.price} EUR` : "";
    li.textContent = (item.title || "(ohne Titel)") + preis;
    list.appendChild(li);
  }
  $("recent").hidden = list.children.length === 0;
}

// Speichert die aktuelle Anzeige in die Sammeldatei. overwrite=true erst senden,
// wenn der Nutzer das Überschreiben einer gleichnamigen Anzeige bestätigt hat.
async function submitListing(overwrite) {
  status("Fotos werden hochgeladen und Datei erstellt …");
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  for (const key of ["title", "author", "book_title", "language", "publisher",
                     "publication_year", "book_format"]) {
    fd.append(key, $("f-" + key).value);
  }
  fd.append("description", $("f-description").innerHTML);  // bearbeitetes HTML übernehmen
  fd.append("price", $("f-price").value);
  fd.append("condition_id", $("f-condition").value);
  if (overwrite) fd.append("overwrite", "true");
  const r = await fetch("/api/create-csv", { method: "POST", body: fd });
  const data = await r.json();
  // Schon eine Anzeige mit gleichem Titel da? Einmal nachfragen.
  if (data.duplicate) {
    if (confirm(`Es gibt bereits einen Eintrag mit dem Titel „${data.title}".\n`
                + `Soll der alte Eintrag überschrieben werden?`)) {
      return submitListing(true);
    }
    status("Speichern abgebrochen – nichts geändert.");
    return;
  }
  if (!r.ok) { status(data.error || "Fehler."); return; }
  $("folder-path").textContent = data.folder;
  status("");
  $("save-success").textContent =
    `✓ Gespeichert – jetzt ${data.count} Anzeige(n) in „${data.filename}".`;
  $("save-success").hidden = false;
  $("show-entry-btn").hidden = false;  // „Eintrag anzeigen" jetzt verfügbar
  loadRecent();                        // Liste unten aktualisieren
}
$("save-csv-btn").addEventListener("click", () => submitListing(false));

// „Eintrag anzeigen": öffnet die eBay-Sammeldatei im Standardprogramm.
$("show-entry-btn").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/open-csv", { method: "POST" });
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      alert(d.error || "Konnte die Sammeldatei nicht öffnen.");
    }
  } catch (err) {
    alert("Konnte die Sammeldatei nicht öffnen.");
  }
});

// „Als hochgeladen markieren": archiviert die aktuelle Sammeldatei und leert sie,
// damit beim nächsten eBay-Upload nicht dieselben Anzeigen noch einmal hochgeladen werden.
on("archive-file-btn", "click", async () => {
  const name = prompt("Die aktuelle Sammeldatei wird archiviert und es beginnt eine "
    + "neue, leere.\n\nOptional: ein Name für die alte Datei (das Datum wird automatisch "
    + "vorangestellt, z. B. eBayClient_2026-06-15_DeinName.csv).\n\nName (kann leer bleiben):");
  if (name === null) return;  // Abbrechen
  try {
    const r = await fetch("/api/archive-file", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const d = await r.json();
    if (!r.ok) { alert(d.error || "Konnte nicht archivieren."); return; }
    $("save-success").hidden = true;
    $("show-entry-btn").hidden = true;
    status(`✓ ${d.moved} Eintrag/Einträge archiviert als „${d.filename}". `
           + `Die Sammeldatei beginnt nun neu.`);
    loadRecent();  // Liste ist jetzt leer → Bereich blendet sich aus
  } catch (e) {
    alert("Konnte nicht archivieren.");
  }
});

// Speicherordner wählen (öffnet ein natives Ordner-Auswahlfenster).
$("choose-folder-btn").addEventListener("click", async () => {
  status("Ordner-Auswahl geöffnet – bitte im Fenster einen Ordner wählen …");
  const d = await (await fetch("/api/choose-folder", { method: "POST" })).json();
  if (d.folder) {
    $("folder-path").textContent = d.folder;
    status("Speicherordner gesetzt.");
    loadRecent();  // anderer Ordner → andere Sammeldatei
  } else {
    status("Kein Ordner gewählt.");
  }
});

// Beim Start: gespeicherten Ordner anzeigen und den letzten Arbeitsstand laden.
(async () => {
  const s = await (await fetch("/api/settings")).json();
  if (s.save_folder) $("folder-path").textContent = s.save_folder;
  loadRecent();  // zuletzt gespeicherte Anzeigen unten zeigen

  const draft = await (await fetch("/api/draft")).json();
  knownImagesRev = draft.images_rev ?? 0;   // Ausgangsstand merken (sonst Fehl-Reload)
  // Fotos aus dem Entwurf zurückholen.
  if (Array.isArray(draft.images) && draft.images.length) {
    selectedFiles = draft.images.map((im, i) =>
      dataURLtoFile(im.data_url, "foto-" + (i + 1)));
    renderThumbs();
  }
  // Textfelder zurückholen.
  const f = draft.fields || {};
  for (const key of RESULT_FIELDS) if (f[key] != null) $("f-" + key).value = f[key];
  if (f.description != null) $("f-description").innerHTML = f.description;
  if (f.price) $("f-price").value = f.price;
  if (f.condition_id) $("f-condition").value = f.condition_id;
  if (draft.result_visible) {
    $("result").hidden = false;
    status("Letzter Stand wiederhergestellt.");
  }
})();

// Beschriftungen der KI-Felder (gleiche Reihenfolge wie in config.py).
const PROMPT_FIELDS = [
  ["title", "Titel"],
  ["author", "Autor"],
  ["book_title", "Buchtitel"],
  ["language", "Sprache"],
  ["description", "Beschreibung"],
  ["publisher", "Verlag"],
  ["publication_year", "Erscheinungsjahr"],
  ["book_format", "Format"],
];

const promptDlg = $("prompt-dialog");
$("prompt-btn").addEventListener("click", async () => {
  const s = await (await fetch("/api/settings")).json();
  $("p-general").value = s.prompt_general || "";
  $("p-examples").value = s.prompt_examples || "";
  const box = $("p-fields");
  box.innerHTML = "";
  const fields = s.prompt_fields || {};
  for (const [key, label] of PROMPT_FIELDS) {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const ta = document.createElement("textarea");
    ta.id = "p-field-" + key;
    ta.rows = 1;
    ta.value = fields[key] || "";
    ta.addEventListener("input", () => autosize(ta));
    wrap.appendChild(ta);
    box.appendChild(wrap);
  }
  promptDlg.showModal();
  // Erst nach dem Öffnen messen, sonst ist die Höhe 0.
  promptDlg.querySelectorAll("textarea").forEach(autosize);
});
$("p-general").addEventListener("input", () => autosize($("p-general")));
$("p-examples").addEventListener("input", () => autosize($("p-examples")));

// „Anweisungen aus Beispiel erzeugen": schickt die Beispiel-Beschreibung an die KI
// und füllt die Felder „Allgemeine Regeln" und „Beschreibung". Der Nutzer prüft und
// speichert danach selbst (nichts wird ungefragt gespeichert).
on("p-derive", "click", async () => {
  const st = $("p-derive-status");
  const example = $("p-examples").value.trim();
  if (!example) {
    if (st) st.textContent = "Bitte zuerst eine Beispiel-Beschreibung eingeben.";
    return;
  }
  const btn = $("p-derive");
  if (btn) btn.disabled = true;
  if (st) st.textContent = "✍️ erzeuge Anweisungen aus dem Beispiel …";
  try {
    const r = await fetch("/api/derive-instructions", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ example }),
    });
    const d = await r.json();
    if (!r.ok) {
      if (st) st.textContent = d.error || "Konnte keine Anweisungen erzeugen.";
      return;
    }
    if (d.prompt_general) $("p-general").value = d.prompt_general;
    const descField = $("p-field-description");
    if (descField && d.description) descField.value = d.description;
    promptDlg.querySelectorAll("textarea").forEach(autosize);
    if (st) st.textContent = "Fertig – bitte prüfen und dann unten speichern.";
  } catch (e) {
    if (st) st.textContent = "Erzeugen nicht möglich (Verbindung?).";
  } finally {
    if (btn) btn.disabled = false;
  }
});

$("p-save").addEventListener("click", async (e) => {
  e.preventDefault();
  const prompt_fields = {};
  for (const [key] of PROMPT_FIELDS) prompt_fields[key] = $("p-field-" + key).value;
  await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt_general: $("p-general").value,
                           prompt_examples: $("p-examples").value, prompt_fields }),
  });
  promptDlg.close();
  status("Anweisungen gespeichert.");
});

// Klick auf „anweisungen.txt" im Tipp öffnet die Datei im Standard-Editor.
$("open-anweisungen").addEventListener("click", async (e) => {
  e.preventDefault();
  try {
    const r = await fetch("/api/open-anweisungen", { method: "POST" });
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      alert(d.error || "Konnte anweisungen.txt nicht öffnen.");
    }
  } catch (err) {
    alert("Konnte anweisungen.txt nicht öffnen.");
  }
});

// „Programm beenden": stoppt den Server. Der Stand ist ohnehin gespeichert.
on("quit-btn", "click", async () => {
  if (!confirm("Programm wirklich beenden? Der aktuelle Stand bleibt gespeichert.")) return;
  try { await fetch("/api/shutdown", { method: "POST" }); } catch (e) { /* Server weg = ok */ }
  document.body.innerHTML = "<main><p style='padding:2rem;font-size:1.1rem'>" +
    "Programm beendet. Sie können diesen Tab jetzt schließen.</p></main>";
});

// Auswählbare Recherche-Quellen (gleiche Reihenfolge/Keys wie SOURCE_CATALOG in config.py).
const PRIMARY_SOURCES = [
  ["zvab", "ZVAB (zvab.com)"],
  ["dnb", "DNB (portal.dnb.de)"],
  ["ddb", "DDB (deutsche-digitale-bibliothek.de)"],
  ["abebooks", "AbeBooks (abebooks.de)"],
  ["booklooker", "Booklooker (booklooker.de)"],
  ["wikipedia", "Wikipedia (wikipedia.org)"],
];
// Zeigt je Quelle ein kleines Zahlenfeld für die Priorität. Vorbelegt nach der
// gespeicherten Reihenfolge (Position 1, 2, 3 …); leer = Quelle wird nicht genutzt.
function renderPrimarySources(selected) {
  const box = $("primary-sources");
  if (!box) return;
  const order = Array.isArray(selected) ? selected : [];
  box.innerHTML = "";
  for (const [key, label] of PRIMARY_SOURCES) {
    const pos = order.indexOf(key);          // -1 = nicht gewählt
    const row = document.createElement("label");
    row.className = "src-row";
    const num = document.createElement("input");
    num.type = "number"; num.min = "1"; num.step = "1";
    num.className = "src-prio"; num.id = "src-" + key; num.placeholder = "–";
    num.value = pos >= 0 ? String(pos + 1) : "";
    row.appendChild(num);
    row.appendChild(document.createTextNode(" " + label));
    box.appendChild(row);
  }
}
// Sammelt die Quellen mit Priorität, sortiert nach der Zahl (1 = zuerst). Bei
// gleicher Zahl entscheidet die Katalog-Reihenfolge. Leer/0 = nicht genutzt.
function collectPrimarySources() {
  const withPrio = [];
  PRIMARY_SOURCES.forEach(([key], idx) => {
    const el = $("src-" + key);
    const n = el ? parseInt(el.value, 10) : NaN;
    if (Number.isFinite(n) && n >= 1) withPrio.push({ key, n, idx });
  });
  withPrio.sort((a, b) => a.n - b.n || a.idx - b.idx);
  return withPrio.map((x) => x.key);
}

const dlg = $("settings-dialog");
// Hinweistext unter dem Rechenleistung-Schalter passend zur Auswahl setzen.
function updateKiBackendHint() {
  const sel = $("s-ki-backend");
  const hint = $("ki-backend-hint");
  if (!sel || !hint) return;   // fehlt ein Element, lieber nichts tun als abstürzen
  hint.textContent = sel.value === "abo"
    ? "Läuft über dein Claude-Abo (Claude Code muss installiert und eingeloggt sein). Der API-Schlüssel wird dann nicht gebraucht."
    : "Läuft über den Anthropic-API-Schlüssel und wird pro Nutzung abgerechnet.";
}
on("s-ki-backend", "change", updateKiBackendHint);

$("settings-btn").addEventListener("click", async () => {
  const s = await (await fetch("/api/settings")).json();
  const kbSel = $("s-ki-backend");
  if (kbSel) kbSel.value = s.ki_backend || "api_key";
  updateKiBackendHint();
  $("s-anthropic").value = s.anthropic_api_key || "";
  $("s-imgbb").value = s.imgbb_api_key || "";
  $("s-model-text").value = s.model_text || "claude-opus-4-8";
  $("s-model-price").value = s.model_price || "claude-sonnet-4-6";
  $("s-location").value = s.location;
  $("s-shipping_cost").value = s.shipping_cost;
  renderPrimarySources(s.primary_sources);
  dlg.showModal();
});
$("s-save").addEventListener("click", async (e) => {
  e.preventDefault();
  await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ki_backend: $("s-ki-backend").value,
      anthropic_api_key: $("s-anthropic").value,
      imgbb_api_key: $("s-imgbb").value,
      model_text: $("s-model-text").value,
      model_price: $("s-model-price").value,
      location: $("s-location").value,
      shipping_cost: $("s-shipping_cost").value,
      primary_sources: collectPrimarySources(),
    }),
  });
  dlg.close();
  status("Einstellungen gespeichert.");
});
