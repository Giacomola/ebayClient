let selectedFiles = [];

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

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
  if (!r.ok) { const e = await r.json(); status(e.error || "Fehler."); return; }
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ebay-anzeige.csv";
  a.click();
  status("eBay-Datei gespeichert. Jetzt im eBay-CSV-Manager hochladen.");
});

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
  const box = $("p-fields");
  box.innerHTML = "";
  const fields = s.prompt_fields || {};
  for (const [key, label] of PROMPT_FIELDS) {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const ta = document.createElement("textarea");
    ta.id = "p-field-" + key;
    ta.rows = 2;
    ta.value = fields[key] || "";
    wrap.appendChild(ta);
    box.appendChild(wrap);
  }
  promptDlg.showModal();
});
$("p-save").addEventListener("click", async (e) => {
  e.preventDefault();
  const prompt_fields = {};
  for (const [key] of PROMPT_FIELDS) prompt_fields[key] = $("p-field-" + key).value;
  await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt_general: $("p-general").value, prompt_fields }),
  });
  promptDlg.close();
  status("Prompt-Vorlage gespeichert.");
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
