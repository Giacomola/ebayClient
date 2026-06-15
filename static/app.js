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
  const list = $("price-comparables");
  list.innerHTML = "";
  for (const c of d.comparables || []) {
    const li = document.createElement("li");
    // Preis deutlich hervorheben (fett), danach das Angebot als anklickbarer Link.
    const preis = document.createElement("b");
    preis.textContent = c.price || "—";
    li.appendChild(preis);
    li.appendChild(document.createTextNode(" – "));
    const titel = c.title || c.source || "Angebot";
    const beschriftung = (c.title && c.source) ? `${titel} (${c.source})` : titel;
    if (c.url) {
      const a = document.createElement("a");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = beschriftung;
      li.appendChild(a);
    } else {
      li.appendChild(document.createTextNode(beschriftung));
    }
    list.appendChild(li);
  }
  $("price-status").textContent =
    list.children.length === 0 ? "Keine Beispielpreise gefunden." : "";
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
async function saveImagesNow() {
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  await fetch("/api/draft/images", { method: "POST", body: fd });
}
// Baut aus einem gespeicherten Base64-Foto wieder eine Datei (für den Upload).
function dataURLtoFile(dataURL, name) {
  const [head, b64] = dataURL.split(",");
  const mime = (head.match(/:(.*?);/) || [])[1] || "image/jpeg";
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new File([bytes], name, { type: mime });
}

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  selectedFiles.forEach((file) => {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    box.appendChild(img);
  });
  $("generate-btn").disabled = selectedFiles.length === 0;
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
    selectedFiles.forEach((f) => fd.append("images", f));
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
    status("Text fertig. Preis bei Bedarf mit „Preis recherchieren“ prüfen.");
    saveFieldsNow();  // Ergebnis sofort in den Entwurf übernehmen
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
$("mark-uploaded-btn").addEventListener("click", async () => {
  if (!confirm("Erst klicken, NACHDEM du die Datei zu eBay hochgeladen hast!\n\n"
               + "Alle Einträge der aktuellen Sammeldatei werden ins Archiv verschoben "
               + "und aus der aktiven Datei entfernt. So werden sie bei eBay nicht doppelt "
               + "angelegt.")) return;
  try {
    const r = await fetch("/api/mark-uploaded", { method: "POST" });
    const d = await r.json();
    if (!r.ok) { alert(d.error || "Konnte nicht abschließen."); return; }
    $("save-success").hidden = true;
    $("show-entry-btn").hidden = true;
    status(`✓ ${d.moved} Eintrag/Einträge ins Archiv verschoben. `
           + `Die aktive Sammeldatei ist nun leer für die nächsten Bücher.`);
    loadRecent();  // Liste ist jetzt leer → Bereich blendet sich aus
  } catch (e) {
    alert("Konnte nicht abschließen.");
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

const dlg = $("settings-dialog");
// Hinweistext unter dem Rechenleistung-Schalter passend zur Auswahl setzen.
function updateKiBackendHint() {
  const abo = $("s-ki-backend").value === "abo";
  $("ki-backend-hint").textContent = abo
    ? "Läuft über dein Claude-Abo (Claude Code muss installiert und eingeloggt sein). Der API-Schlüssel wird dann nicht gebraucht."
    : "Läuft über den Anthropic-API-Schlüssel und wird pro Nutzung abgerechnet.";
}
$("s-ki-backend").addEventListener("change", updateKiBackendHint);

$("settings-btn").addEventListener("click", async () => {
  const s = await (await fetch("/api/settings")).json();
  $("s-ki-backend").value = s.ki_backend || "api_key";
  updateKiBackendHint();
  $("s-anthropic").value = s.anthropic_api_key || "";
  $("s-imgbb").value = s.imgbb_api_key || "";
  $("s-model-text").value = s.model_text || "claude-opus-4-8";
  $("s-model-price").value = s.model_price || "claude-sonnet-4-6";
  $("s-location").value = s.location;
  $("s-shipping_cost").value = s.shipping_cost;
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
    }),
  });
  dlg.close();
  status("Einstellungen gespeichert.");
});
