let selectedFiles = [];

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

// --- Einzelinstanz: nur EIN aktives Fenster ---------------------------------
// Zwei Fenster auf demselben Server teilen sich dieselbe draft.json und würden
// sich gegenseitig überschreiben (und durch die 2,5-Sek-Abfrage „flackern").
// Über einen BroadcastChannel einigen sich die Fenster: nur eines ist aktiv,
// weitere zeigen einen Hinweis und pausieren (appActive=false → kein Speichern).
let appActive = true;
(function einzelinstanz() {
  if (!("BroadcastChannel" in window)) return;   // sehr alte Browser: einfach lassen
  const kanal = new BroadcastChannel("buch-anzeigen-helfer");
  const meineId = Math.random().toString(36).slice(2);
  const overlay = $("single-instance-overlay");

  function werdeAktiv()     { appActive = true;  if (overlay) overlay.hidden = true; }
  function werdeBlockiert() { appActive = false; if (overlay) overlay.hidden = false; }

  kanal.onmessage = (e) => {
    const m = e.data || {};
    if (m.id === meineId) return;                 // eigene Nachrichten ignorieren
    if (m.type === "hallo" && appActive) {
      kanal.postMessage({ type: "hier", id: meineId });   // „ich bin schon aktiv"
    } else if (m.type === "fokus" && appActive) {
      try { window.focus(); } catch (_) {}        // bestmöglich nach vorne (oft blockiert)
    } else if (m.type === "hier" || m.type === "uebernahme") {
      werdeBlockiert();                           // anderes aktives Fenster / Übernahme
    }
  };
  // Beim Start fragen: ist schon ein aktives Fenster da? (Antwort kommt in ms.)
  kanal.postMessage({ type: "hallo", id: meineId });

  // Orange: „Zum geöffneten Fenster wechseln". Ein Tab kann das andere Fenster
  // nicht zuverlässig nach vorne holen und sich selbst meist nicht schließen –
  // darum: anderes Fenster bestmöglich anstupsen, dieses schließen versuchen,
  // sonst klare Bitte anzeigen, dieses Fenster zu schließen.
  const switchBtn = $("si-switch");
  if (switchBtn) switchBtn.addEventListener("click", () => {
    kanal.postMessage({ type: "fokus", id: meineId });
    window.close();   // klappt nur bei per Skript geöffneten Fenstern
    const t = $("si-text");
    if (t) t.textContent = "Bitte schließen Sie dieses Fenster (Tab). " +
      "Der Buch-Anzeigen-Helfer läuft im anderen Fenster weiter.";
  });

  // Grau: „Neues Fenster öffnen": dieses Fenster wird das aktive,
  // die anderen treten zurück.
  const newBtn = $("si-new");
  if (newBtn) newBtn.addEventListener("click", () => {
    kanal.postMessage({ type: "uebernahme", id: meineId });
    werdeAktiv();
    location.reload();   // frischen Stand laden und sauber weiterarbeiten
  });
})();

// Deutliche Rückmeldung als großes Banner oben. typ: "success" | "error" | "info".
// dauer > 0 blendet es nach so vielen Millisekunden automatisch wieder aus.
let bannerTimer = null;
function banner(typ, text, dauer = 0) {
  const b = $("banner");
  if (!b) return;
  b.className = "banner " + typ;
  b.textContent = text;
  b.hidden = false;
  if (bannerTimer) { clearTimeout(bannerTimer); bannerTimer = null; }
  if (dauer > 0) bannerTimer = setTimeout(() => { b.hidden = true; }, dauer);
}
function bannerAus() { const b = $("banner"); if (b) b.hidden = true; }

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
// Zieht die Zahl aus einem Preistext (z. B. "ca. 12,50 €" → 12.5) zum Sortieren.
// Findet keine Zahl → NaN (solche Einträge wandern ans Ende).
function preisZahl(text) {
  const m = String(text || "").replace(/\s/g, "").match(/\d+(?:[.,]\d+)?/);
  return m ? parseFloat(m[0].replace(",", ".")) : NaN;
}

// Zeigt nur die gefundenen Beispielpreise mit Quelle – bewusst keine Empfehlung.
// Aufsteigend nach Preis sortiert; Spalten: Angebot · Quelle · Preis (rechts).
function renderPrice(d) {
  $("price-box").hidden = false;
  const body = $("price-comparables");   // <tbody> der Preistabelle
  body.innerHTML = "";
  const items = (d.comparables || []).slice().sort((a, b) => {
    const x = preisZahl(a.price), y = preisZahl(b.price);
    if (isNaN(x)) return 1;            // ohne erkennbaren Preis nach hinten
    if (isNaN(y)) return -1;
    return x - y;                      // günstigste zuerst
  });
  for (const c of items) {
    const tr = document.createElement("tr");
    // Spalte 1: Angebot als anklickbarer Link (lange Titel werden gekürzt).
    const tdAngebot = document.createElement("td");
    tdAngebot.className = "col-angebot";
    const titel = c.title || "Angebot";
    tdAngebot.title = titel;           // voller Titel als Tooltip
    if (c.url) {
      const a = document.createElement("a");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = titel;
      tdAngebot.appendChild(a);
    } else {
      tdAngebot.textContent = titel;
    }
    // Spalte 2: Quelle (z. B. ZVAB), dezent.
    const tdQuelle = document.createElement("td");
    tdQuelle.className = "col-quelle";
    tdQuelle.textContent = c.source || "";
    // Spalte 3: Preis (fett, rechtsbündig, in einer Zeile).
    const tdPreis = document.createElement("td");
    tdPreis.className = "col-preis";
    tdPreis.textContent = c.price || "—";
    tr.appendChild(tdAngebot);
    tr.appendChild(tdQuelle);
    tr.appendChild(tdPreis);
    body.appendChild(tr);
  }
  // Leere Tabelle ausblenden, damit nur der Hinweistext sichtbar bleibt.
  $("price-table").hidden = items.length === 0;
  $("price-status").textContent =
    items.length === 0 ? "Keine Beispielpreise gefunden."
                       : `${items.length} Beispielpreise gefunden:`;
  // Empfehlung + Begründung anzeigen. Das Eintragen in das Preisfeld macht NUR die
  // frische Suche (fetchPrice) – beim Wiederherstellen soll ein evtl. von Hand
  // geänderter Preis nicht überschrieben werden.
  const rec = (d.recommended_price || "").trim();
  const recEl = $("price-recommend");
  if (rec) {
    recEl.textContent = `Empfohlener Preis: ${rec} €`
      + (d.price_reason ? ` – ${d.price_reason}` : "");
    recEl.hidden = false;
  } else {
    recEl.textContent = d.price_reason || "";   // ohne Empfehlung ggf. nur die Begründung
    recEl.hidden = !d.price_reason;
  }
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
  $("price-recommend").hidden = true;
  const body = {};
  for (const key of ["title", "author", "book_title", "language",
                     "publication_year", "publisher", "book_format"]) {
    body[key] = $("f-" + key).value;
  }
  // Gewählten Zustand als Text mitgeben (z. B. „Gut"), damit die KI ihn einrechnet.
  body.condition = $("f-condition").selectedOptions[0].textContent.trim();
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
  // Empfohlenen Preis ins Feld eintragen (überschreibt einen evtl. getippten Wert –
  // gewollt: der Preis soll sich an die frische Recherche anpassen).
  const rec = (d.recommended_price || "").trim();
  if (rec) { $("f-price").value = rec; saveFieldsSoon(); }
  savePriceResult(d);   // Ergebnis im Entwurf merken (bleibt nach Neuladen erhalten)
  status("");  // Hauptzeile leeren – die Preisbox zeigt das Ergebnis selbst
}

// Speichert das Preis-Ergebnis im Entwurf, damit es ein Neuladen / Wiederaufnehmen übersteht.
async function savePriceResult(d) {
  try {
    await fetch("/api/draft/price", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ price_result: d }),
    });
  } catch (e) { /* nicht schlimm – beim nächsten Mal erneut */ }
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
  if (!appActive) return;   // blockiertes Fenster schreibt nicht in die gemeinsame Datei
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
  if (!appActive) return;   // blockiertes Fenster schreibt nicht in die gemeinsame Datei
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
  if (!appActive) return;   // pausiertes Fenster nicht mitlaufen lassen
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
  banner("info", "⏳ Bitte warten – die Anzeige wird erstellt (ca. 1 Minute) …");
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
  try {
    const fd = new FormData();
    fotosFuerAnalyse().forEach((f) => fd.append("images", f));  // nur ausgewählte Fotos analysieren
    const r = await fetch("/api/generate", { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) {
      status(data.error || "Fehler bei der Analyse.");
      banner("error", data.error || "Die Anzeige konnte nicht erstellt werden.");
      return;
    }
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
    banner("success", "✓ Text fertig – ich suche jetzt noch Beispielpreise …", 6000);
    saveFieldsNow();  // Ergebnis sofort in den Entwurf übernehmen
    fetchPrice();     // Preisrecherche automatisch anstoßen (läuft im Hintergrund)
  } catch (e) {
    // Bricht der Aufruf ab (Netzfehler/Timeout), bleibt die Seite bedienbar
    // und zeigt eine klare Meldung statt für immer „recherchiere …".
    status("Die Erstellung ist fehlgeschlagen. Bitte erneut versuchen.");
    banner("error", "Die Erstellung ist fehlgeschlagen. Bitte erneut versuchen.");
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
  // Sicherheitsabfrage nur, wenn gerade etwas auf dem Bildschirm steht.
  const hatInhalt = selectedFiles.length > 0 || !$("result").hidden;
  if (hatInhalt && !confirm(
      "Aktuellen Fall beiseitelegen und neu beginnen?\n\n"
      + "Du findest ihn jederzeit oben unter „Fall wiederaufnehmen“.")) return;
  selectedFiles = [];
  renderThumbs();
  for (const key of RESULT_FIELDS) $("f-" + key).value = "";
  $("f-description").innerHTML = "";
  $("f-price").value = "";
  $("f-condition").value = "5000";
  $("result").hidden = true;
  $("title-suggestions").hidden = true;
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
  $("save-success").hidden = true;
  $("show-entry-btn").hidden = true;
  knownImagesRev = 0;   // frischer Fall: Foto-Version zurücksetzen (kein Fehl-Reload)
  let parked = false;
  try { parked = (await (await fetch("/api/draft/clear", { method: "POST" })).json()).parked; }
  catch (e) {}
  bannerAus();          // alte Meldung vom vorigen Fall entfernen
  loadCases();          // ein gerade geparkter Fall erscheint in der Liste
  status(parked
    ? `Fall geparkt – du findest ihn oben unter „Fall wiederaufnehmen". Neuer Fall bereit.`
    : "Neuer Fall – bereit für die nächsten Fotos.");
});

// Liste „Aktive Fälle": begonnene, noch nicht abgesendete Fälle zum Weitermachen.
async function loadCases() {
  $("active-cases").hidden = false;   // Bereich ist immer sichtbar, auch wenn leer/Fehler
  let data = { cases: [] };
  try { data = await (await fetch("/api/cases")).json(); }
  catch (e) { /* offline o. Ä. – dann eben leere Liste */ }
  const list = $("active-cases-list");
  list.innerHTML = "";
  for (const c of data.cases || []) {
    const li = document.createElement("li");
    li.className = "case-row";
    const info = document.createElement("span");
    info.className = "case-info";
    const fotos = c.photo_count === 1 ? "1 Foto" : `${c.photo_count} Fotos`;
    info.textContent = `${c.name} · ${fotos} · ${formatDatum(c.saved_at)}`;
    const oeffnen = document.createElement("button");
    oeffnen.type = "button";
    oeffnen.textContent = "Öffnen";
    oeffnen.addEventListener("click", () => openCase(c.id));
    const del = document.createElement("button");
    del.type = "button";
    del.className = "case-del";
    del.textContent = "×";
    del.title = "Fall löschen";
    del.addEventListener("click", () => deleteCase(c.id, c.name));
    li.append(info, oeffnen, del);
    list.appendChild(li);
  }
  if (!list.children.length) {
    // Leerer Zustand: Bereich bleibt sichtbar, damit man die Funktion findet.
    const li = document.createElement("li");
    li.className = "sub";
    li.textContent = `Noch keine aktiven Fälle. Sobald du einen begonnenen Fall mit `
      + `„Neuen Fall starten" beiseitelegst, erscheint er hier.`;
    list.appendChild(li);
  }
  $("active-cases").hidden = false;   // immer sichtbar (auch wenn leer)
}

function formatDatum(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString("de-DE") + " "
       + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

// --- Übersicht & Verwaltung: alle Einträge nach Status, mit Aktionen ----------
const overviewDlg = $("overview-dialog");
function euro(n) {
  return (n || 0).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
}
// Baut eine Zeile mit Text + beliebig vielen Knöpfen ([{text, onClick, cls}]).
function ovRow(text, knoepfe) {
  const li = document.createElement("li");
  li.className = "ov-row";
  const info = document.createElement("span");
  info.className = "ov-info";
  info.textContent = text;
  li.appendChild(info);
  for (const k of (knoepfe || [])) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = k.text;
    if (k.cls) b.className = k.cls;
    b.addEventListener("click", k.onClick);
    li.appendChild(b);
  }
  return li;
}
function ovHinweis(text) {
  const li = document.createElement("li");
  li.className = "sub";
  li.textContent = text;
  return li;
}
function ovCount(n, ein, mehr) {
  return n ? `– ${n} ${n === 1 ? ein : mehr}` : "– keine";
}
function ovFotos(c) {
  return c.photo_count === 1 ? "1 Foto" : `${c.photo_count} Fotos`;
}
// Ruft eine Aktions-Route auf und frischt danach Fenster + Seite auf.
async function caseAction(id, pfad, erfolg, frage) {
  if (frage && !confirm(frage)) return;
  banner("info", "Bitte warten …");
  let r;
  try { r = await fetch(`/api/cases/${id}/${pfad}`, { method: "POST" }); }
  catch (e) { banner("error", "Aktion fehlgeschlagen (keine Verbindung).", 6000); return; }
  let d = {};
  try { d = await r.json(); } catch (e) { /* ohne Body weiter */ }
  if (!r.ok) { banner("error", d.error || "Aktion fehlgeschlagen.", 8000); return; }
  banner("success", erfolg, 4000);
  await renderOverview();   // Liste im Fenster neu aufbauen
  loadCases();
  loadRecent();
}
// Standard-Aktionen, die mehrere Abschnitte teilen.
function aktArchivieren(id) {
  return { text: "Archivieren", onClick: () =>
    caseAction(id, "archivieren", "Eintrag archiviert.") };
}
function aktLoeschen(id, name, zusatz = "") {
  return { text: "Löschen", cls: "case-del", onClick: () =>
    caseAction(id, "delete", "Eintrag gelöscht.",
      `Eintrag „${name}" wirklich löschen?${zusatz}`) };
}
async function renderOverview() {
  let d;
  try { d = await (await fetch("/api/overview")).json(); }
  catch (e) { banner("error", "Übersicht konnte nicht geladen werden.", 6000); return; }

  // 🛠️ In Arbeit (offene Fälle)
  const cases = d.active_cases || [];
  $("ov-cases-count").textContent = ovCount(cases.length, "Fall", "Fälle");
  const ulC = $("ov-cases"); ulC.innerHTML = "";
  for (const c of cases) {
    ulC.appendChild(ovRow(`${c.name} · ${ovFotos(c)}`, [
      { text: "Bearbeiten", onClick: () => openCase(c.id) },
      aktArchivieren(c.id),
      aktLoeschen(c.id, c.name, " Das lässt sich nicht rückgängig machen."),
    ]));
  }
  if (!cases.length) ulC.appendChild(ovHinweis("Keine begonnenen Fälle."));

  // ⏸️ Zurückgehalten (fertig, aber nicht hochgeladen)
  const held = d.held_cases || [];
  $("ov-held-count").textContent = ovCount(held.length, "Eintrag", "Einträge");
  const ulH = $("ov-held"); ulH.innerHTML = "";
  for (const c of held) {
    ulH.appendChild(ovRow(`${c.name} · ${ovFotos(c)}`, [
      { text: "Bearbeiten", onClick: () => openCase(c.id) },
      { text: "Freigeben", cls: "case-go", onClick: () =>
          caseAction(c.id, "freigeben", "Eintrag freigegeben – jetzt in der Sammeldatei.") },
      aktArchivieren(c.id),
      aktLoeschen(c.id, c.name),
    ]));
  }
  if (!held.length) ulH.appendChild(ovHinweis("Nichts zurückgehalten."));

  // ✅ Freigegeben (in der Sammeldatei)
  const stats = d.stats || { count: 0, total: 0 };
  $("ov-listings-count").textContent = stats.count
    ? `– ${stats.count} ${stats.count === 1 ? "Anzeige" : "Anzeigen"} · ${euro(stats.total)}`
    : "– keine";
  const ulL = $("ov-listings"); ulL.innerHTML = "";
  for (const item of d.listings || []) {
    const preis = item.price ? ` – ${item.price} EUR` : "";
    const text = (item.title || "(ohne Titel)") + preis;
    if (item.case_id) {
      const id = item.case_id;
      ulL.appendChild(ovRow(text, [
        { text: "Bearbeiten", onClick: () => openCase(id) },
        { text: "Zurückziehen", onClick: () =>
            caseAction(id, "zurueckziehen",
              "Eintrag zurückgezogen – nicht mehr in der Sammeldatei.") },
        aktArchivieren(id),
        aktLoeschen(id, item.title || "", " Auch die CSV-Zeile wird entfernt."),
      ]));
    } else {
      ulL.appendChild(ovRow(text));
    }
  }
  if (!(d.listings || []).length)
    ulL.appendChild(ovHinweis("Noch nichts in der Sammeldatei."));

  // 🗄️ Archivierte Einträge (weggeräumt, wiederherstellbar)
  const archd = d.archived_cases || [];
  $("ov-archived-count").textContent = ovCount(archd.length, "Eintrag", "Einträge");
  const ulAd = $("ov-archived"); ulAd.innerHTML = "";
  for (const c of archd) {
    ulAd.appendChild(ovRow(`${c.name} · ${ovFotos(c)}`, [
      { text: "Wiederherstellen", cls: "case-go", onClick: () =>
          caseAction(c.id, "wiederherstellen",
            "Eintrag wiederhergestellt (zurückgehalten).") },
      aktLoeschen(c.id, c.name, " Endgültig."),
    ]));
  }
  if (!archd.length) ulAd.appendChild(ovHinweis("Keine archivierten Einträge."));

  // 📁 Archivierte Sammeldateien (ganze CSVs, nur zur Info)
  const arch = d.archives || [];
  $("ov-archives-count").textContent = ovCount(arch.length, "Datei", "Dateien");
  const ulA = $("ov-archives"); ulA.innerHTML = "";
  for (const a of arch) {
    const anz = a.count === 1 ? "1 Anzeige" : `${a.count} Anzeigen`;
    ulA.appendChild(ovHinweis(`${a.filename} · ${anz} · ${euro(a.total)}`));
  }
  if (!arch.length) ulA.appendChild(ovHinweis("Noch nichts archiviert."));
}
async function openOverview() {
  await renderOverview();
  overviewDlg.showModal();
}
on("overview-btn", "click", openOverview);

// --- „Zum Upload"-Fenster: alles rund ums Hochladen gebündelt -----------------
const uploadDlg = $("upload-dialog");
async function openUpload() {
  await loadRecent();   // „Noch nicht hochgeladen"-Liste + Zähler füllen
  // Kompakter Stand nach Status (eine Zeile) aus der Übersicht.
  try {
    const d = await (await fetch("/api/overview")).json();
    const a = (d.active_cases || []).length;
    const h = (d.held_cases || []).length;
    const f = (d.stats || {}).count || 0;
    const ar = (d.archived_cases || []).length;
    $("up-status-summary").textContent =
      `🛠️ In Arbeit: ${a} · ⏸️ Zurückgehalten: ${h} · ✅ Freigegeben: ${f} · 🗄️ Archiviert: ${ar}`;
  } catch (e) { $("up-status-summary").textContent = ""; }
  uploadDlg.showModal();
}
on("upload-btn", "click", openUpload);
// „Bei eBay hochladen": als echtes neues Fenster öffnen (nicht nur als Tab).
// Fenstergröße angeben -> der Browser öffnet ein eigenständiges Fenster.
on("ebay-upload-link", "click", (e) => {
  e.preventDefault();
  const url = e.currentTarget.getAttribute("href");
  window.open(url, "ebay-upload", "width=1200,height=850,noopener");
});
// Querverweise zwischen den beiden Fenstern (immer erst schließen, dann öffnen).
on("up-manage-btn", "click", () => { uploadDlg.close(); openOverview(); });
on("ov-to-upload-btn", "click", () => { overviewDlg.close(); openUpload(); });

// --- Fragen-Fenster: einfacher Chat mit der KI ------------------------------
const chatPanel = $("chat-panel");
let chatVerlauf = [];   // [{role:"user"|"assistant", content:"…"}]

// Schwebendes Chat-Fenster auf/zu (Support-Stil). Der runde Knopf bleibt sichtbar.
function chatOeffnen()  { chatPanel.hidden = false; $("chat-text").focus(); }
function chatSchliessen() { chatPanel.hidden = true; }
function chatUmschalten() { if (chatPanel.hidden) chatOeffnen(); else chatSchliessen(); }

function chatZeile(role, text) {
  const div = document.createElement("div");
  div.className = "chat-zeile " + (role === "user" ? "chat-ich" : "chat-ki");
  div.textContent = text;
  $("chat-verlauf").appendChild(div);
  $("chat-verlauf").scrollTop = $("chat-verlauf").scrollHeight;
  return div;
}

// Wandelt die einfache Markdown-Auszeichnung der KI-Antwort in echtes Fett/Kursiv
// um (statt die Sternchen anzuzeigen). Erst HTML entschaerfen, dann nur **fett**,
// *kursiv* und Zeilenumbrueche zulassen – sicher gegen eingeschleustes HTML.
function chatFormat(text) {
  const sicher = (text || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return sicher
    .replace(/\*\*\*([^*]+?)\*\*\*/g, "<b><i>$1</i></b>")
    .replace(/\*\*([^*]+?)\*\*/g, "<b>$1</b>")
    .replace(/\*([^*\s][^*\n]*?)\*/g, "<i>$1</i>")
    .replace(/\n/g, "<br>");
}

// Erlaubte Aktions-Knöpfe: Die KI darf ans Ende ihrer Antwort Marker wie
// [aktion:einstellungen] setzen; daraus wird hier ein Knopf, der den jeweils
// VORHANDENEN Knopf auslöst. Feste Liste (Whitelist) – nur diese fünf sind
// möglich, alles andere wird ignoriert. So kann die KI nichts Beliebiges auslösen.
const CHAT_AKTIONEN = {
  einstellungen: { label: "⚙ Einstellungen öffnen",     ziel: "settings-btn" },
  anweisungen:   { label: "📝 Anweisungen bearbeiten",   ziel: "open-prompt-btn" },
  uebersicht:    { label: "🗂 Übersicht öffnen",          ziel: "overview-btn" },
  handy:         { label: "📱 Per Handy hochladen",       ziel: "handy-btn" },
  upload:        { label: "📤 eBay-Upload-Seite öffnen",  ziel: "ebay-upload-link" },
};

// Schneidet die [aktion:xxx]-Marker aus dem Antworttext und gibt den sauberen
// Text plus die Liste erkannter (erlaubter) Aktionen zurück.
function chatAktionenLesen(text) {
  const aktionen = [];
  const sauber = (text || "").replace(/\[aktion:([a-zäöü]+)\]/gi, (_, name) => {
    const key = name.toLowerCase();
    if (CHAT_AKTIONEN[key] && !aktionen.includes(key)) aktionen.push(key);
    return "";   // Marker aus dem sichtbaren Text entfernen
  }).trim();
  return { text: sauber, aktionen };
}

// Hängt unter eine Chat-Antwort die passenden Aktions-Knöpfe.
function chatAktionenAnzeigen(zeile, aktionen) {
  if (!aktionen.length) return;
  const leiste = document.createElement("div");
  leiste.className = "chat-aktionen";
  for (const key of aktionen) {
    const def = CHAT_AKTIONEN[key];
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chat-aktion";
    b.textContent = def.label;
    b.addEventListener("click", () => {
      const ziel = document.getElementById(def.ziel);
      if (ziel) ziel.click();   // löst den vorhandenen Knopf/Link aus
    });
    leiste.appendChild(b);
  }
  zeile.appendChild(leiste);
}

async function chatSenden() {
  const feld = $("chat-text");
  const frage = feld.value.trim();
  if (!frage) return;
  feld.value = "";
  chatZeile("user", frage);
  chatVerlauf.push({ role: "user", content: frage });
  const platz = chatZeile("assistant", "… denkt nach");
  $("chat-send").disabled = true;
  try {
    const r = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatVerlauf }),
    });
    const d = await r.json();
    if (!r.ok) { platz.textContent = "⚠ " + (d.error || "Es ist ein Fehler aufgetreten."); return; }
    const { text: antwortText, aktionen } = chatAktionenLesen(d.answer || "(keine Antwort)");
    platz.innerHTML = chatFormat(antwortText);
    chatAktionenAnzeigen(platz, aktionen);
    chatVerlauf.push({ role: "assistant", content: d.answer || "" });
  } catch (e) {
    platz.textContent = "⚠ Keine Verbindung – bitte erneut versuchen.";
  } finally {
    $("chat-send").disabled = false;
  }
}

on("chat-bubble", "click", chatUmschalten);   // runder Knopf unten rechts
on("chat-close", "click", chatSchliessen);
on("chat-send", "click", chatSenden);
// Enter sendet, Umschalt+Enter macht einen Zeilenumbruch.
on("chat-text", "keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); chatSenden(); }
});

// Öffnen: Backend macht den Fall zum aktuellen (und parkt den bisherigen offenen).
// Danach die Seite neu laden – die Start-Logik stellt den Fall sauber wieder her.
async function openCase(id) {
  status("Fall wird geöffnet …");
  await fetch("/api/cases/" + id + "/open", { method: "POST" });
  location.reload();
}

async function deleteCase(id, name) {
  if (!confirm(`Fall „${name}" wirklich löschen? Das lässt sich nicht rückgängig machen.`))
    return;
  await fetch("/api/cases/" + id + "/delete", { method: "POST" });
  loadCases();
}

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
    li.className = "recent-row";
    const preis = item.price ? ` – ${item.price} EUR` : "";
    const info = document.createElement("span");
    info.className = "recent-info";
    info.textContent = (item.title || "(ohne Titel)") + preis;
    li.appendChild(info);
    // Liegt zu dieser Anzeige ein vollständiger Fall vor? Dann bearbeitbar.
    if (item.case_id) {
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "recent-edit";
      edit.textContent = "Bearbeiten";
      edit.title = "Diese Anzeige öffnen und ändern – beim Speichern wird die CSV-Zeile aktualisiert";
      edit.addEventListener("click", () => openCase(item.case_id));
      li.appendChild(edit);
    }
    list.appendChild(li);
  }
  // Überblick: wie viele Anzeigen liegen bereit und was ist die Preissumme?
  const stats = data.stats || { count: 0, total: 0 };
  const statsEl = $("recent-stats");
  if (statsEl) {
    if (stats.count > 0) {
      const summe = stats.total.toLocaleString("de-DE",
        { style: "currency", currency: "EUR" });
      const wort = stats.count === 1 ? "Anzeige" : "Anzeigen";
      statsEl.textContent = `– ${stats.count} ${wort} bereit · Summe Startpreise ${summe}`;
    } else {
      statsEl.textContent = "Noch nichts in der Sammeldatei.";
    }
  }
  // Zähler direkt am roten „Zum Upload"-Knopf, damit man bereitliegende Anzeigen sieht.
  const badge = $("upload-count");
  if (badge) badge.textContent = stats.count ? ` · ${stats.count} bereit` : "";
}

// Speichert die aktuelle Anzeige in die Sammeldatei. overwrite=true erst senden,
// wenn der Nutzer das Überschreiben einer gleichnamigen Anzeige bestätigt hat.
async function submitListing(overwrite) {
  status("Fotos werden hochgeladen und Datei erstellt …");
  banner("info", "⏳ Bitte warten – Fotos werden hochgeladen und gespeichert …");
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
    if (confirm(`Es gibt bereits einen Eintrag für „${data.title}" `
                + `(gleicher Autor und Buchtitel).\n`
                + `Soll der alte Eintrag überschrieben werden?`)) {
      return submitListing(true);
    }
    status("Speichern abgebrochen – nichts geändert.");
    banner("info", "Speichern abgebrochen – nichts geändert.", 5000);
    return;
  }
  if (!r.ok) {
    status(data.error || "Fehler.");
    banner("error", data.error || "Die Anzeige konnte nicht gespeichert werden.");
    return;
  }
  $("folder-path").textContent = data.folder;
  status("");
  banner("success", `✓ Anzeige gespeichert! Jetzt ${data.count} Anzeige(n) in der Sammeldatei.`, 7000);
  $("save-success").textContent =
    `✓ Gespeichert – jetzt ${data.count} Anzeige(n) in „${data.filename}".`;
  $("save-success").hidden = false;
  $("show-entry-btn").hidden = false;  // „Eintrag anzeigen" jetzt verfügbar
  loadRecent();                        // Liste unten aktualisieren
}
$("save-csv-btn").addEventListener("click", () => submitListing(false));

// „Zurückhalten": aktuellen Entwurf fertig speichern, aber NICHT freigeben.
$("hold-btn").addEventListener("click", async () => {
  await saveFieldsNow();                 // aktuelle Feldwerte sichern
  banner("info", "Bitte warten …");
  let r;
  try { r = await fetch("/api/draft/zurueckhalten", { method: "POST" }); }
  catch (e) { banner("error", "Zurückhalten fehlgeschlagen (keine Verbindung).", 6000); return; }
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    banner("error", d.error || "Zurückhalten fehlgeschlagen.", 6000);
    return;
  }
  banner("success", `Eintrag zurückgehalten – du findest ihn unter „Übersicht".`, 6000);
  location.reload();
});

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

// „Speicherordner öffnen": zeigt im Finder/Explorer, wo die Datei ebay-anzeigen.csv
// liegt – damit man sie im eBay-Upload-Dialog leicht findet.
on("open-folder-btn", "click", async () => {
  try {
    const r = await fetch("/api/open-folder", { method: "POST" });
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      banner("error", d.error || "Konnte den Speicherordner nicht öffnen.", 6000);
    }
  } catch (err) {
    banner("error", "Konnte den Speicherordner nicht öffnen.", 6000);
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
    if (!r.ok) { banner("error", d.error || "Konnte nicht archivieren."); return; }
    $("save-success").hidden = true;
    $("show-entry-btn").hidden = true;
    banner("success", `✓ ${d.moved} Eintrag/Einträge archiviert als „${d.filename}". `
           + `Die Sammeldatei beginnt nun neu.`, 8000);
    loadRecent();  // Liste ist jetzt leer → Bereich blendet sich aus
  } catch (e) {
    banner("error", "Konnte nicht archivieren.");
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
  loadCases();   // begonnene, noch nicht abgesendete Fälle zeigen

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
  // Gespeichertes Preis-Ergebnis wiederherstellen (Vergleichsangebote + Empfehlung).
  if (draft.price_result) renderPrice(draft.price_result);
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
// „Anweisungen" ist jetzt ein Menüpunkt im Einstellungen-Fenster: erst die
// Einstellungen schließen, dann den Anweisungen-Editor öffnen.
$("open-prompt-btn").addEventListener("click", async () => {
  $("settings-dialog").close();
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
  $("s-model-chat").value = s.model_chat || "claude-haiku-4-5";
  $("s-upload-action").value = s.upload_action || "draft";
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
      model_chat: $("s-model-chat").value,
      upload_action: $("s-upload-action").value,
      location: $("s-location").value,
      shipping_cost: $("s-shipping_cost").value,
      primary_sources: collectPrimarySources(),
    }),
  });
  dlg.close();
  status("Einstellungen gespeichert.");
});
