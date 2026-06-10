let selectedFiles = [];

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

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
dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
dz.addEventListener("drop", (e) => {
  e.preventDefault(); dz.classList.remove("drag"); addFiles(e.dataTransfer.files);
});
$("choose-btn").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", (e) => addFiles(e.target.files));

$("generate-btn").addEventListener("click", async () => {
  status("KI analysiert die Fotos …");
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
  $("result").hidden = false;
  status("Fertig – bitte prüfen und bei Bedarf bearbeiten.");
  saveFieldsNow();  // Ergebnis sofort in den Entwurf übernehmen
});

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
  await fetch("/api/draft/clear", { method: "POST" });
  status("Neuer Fall – bereit für die nächsten Fotos.");
});

$("save-csv-btn").addEventListener("click", async () => {
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
  const r = await fetch("/api/create-csv", { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok) { status(data.error || "Fehler."); return; }
  $("folder-path").textContent = data.folder;
  status(`Hinzugefügt – jetzt ${data.count} Anzeige(n) in „${data.filename}". `
         + `Ordner: ${data.folder}`);
});

// Speicherordner wählen (öffnet ein natives Ordner-Auswahlfenster).
$("choose-folder-btn").addEventListener("click", async () => {
  status("Ordner-Auswahl geöffnet – bitte im Fenster einen Ordner wählen …");
  const d = await (await fetch("/api/choose-folder", { method: "POST" })).json();
  if (d.folder) {
    $("folder-path").textContent = d.folder;
    status("Speicherordner gesetzt.");
  } else {
    status("Kein Ordner gewählt.");
  }
});

// Beim Start: gespeicherten Ordner anzeigen und den letzten Arbeitsstand laden.
(async () => {
  const s = await (await fetch("/api/settings")).json();
  if (s.save_folder) $("folder-path").textContent = s.save_folder;

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

// „Programm beenden": stoppt den Server. Der Stand ist ohnehin gespeichert.
on("quit-btn", "click", async () => {
  if (!confirm("Programm wirklich beenden? Der aktuelle Stand bleibt gespeichert.")) return;
  try { await fetch("/api/shutdown", { method: "POST" }); } catch (e) { /* Server weg = ok */ }
  document.body.innerHTML = "<main><p style='padding:2rem;font-size:1.1rem'>" +
    "Programm beendet. Sie können diesen Tab jetzt schließen.</p></main>";
});

const dlg = $("settings-dialog");
$("settings-btn").addEventListener("click", async () => {
  const s = await (await fetch("/api/settings")).json();
  $("s-anthropic").value = s.anthropic_api_key || "";
  $("s-imgbb").value = s.imgbb_api_key || "";
  $("s-model").value = s.model;
  $("s-location").value = s.location;
  $("s-shipping_cost").value = s.shipping_cost;
  dlg.showModal();
});
$("s-save").addEventListener("click", async (e) => {
  e.preventDefault();
  await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      anthropic_api_key: $("s-anthropic").value,
      imgbb_api_key: $("s-imgbb").value,
      model: $("s-model").value,
      location: $("s-location").value,
      shipping_cost: $("s-shipping_cost").value,
    }),
  });
  dlg.close();
  status("Einstellungen gespeichert.");
});
