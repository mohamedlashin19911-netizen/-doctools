/* أدوات المستندات — واجهة محلية */
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

/* ---------- التبويبات ---------- */
$$(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    $$(".view").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("#view-" + t.dataset.view).classList.add("active");
  })
);

function toast(msg, ok = true) {
  const el = $("#toast");
  el.textContent = msg;
  el.style.background = ok ? "#1d4d38" : "#4d1d1d";
  el.style.display = "block";
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.style.display = "none"), 3500);
}

function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

const extOf = (n) => {
  n = n.toLowerCase();
  if (n.endsWith(".tar.gz")) return "tar.gz";
  return n.includes(".") ? n.split(".").pop() : "";
};

/* ---------- محوّل الصيغ ---------- */
const convFiles = [];
const dzC = $("#drop-convert"), inpC = $("#file-convert");

function bindDrop(dz, input, onFiles) {
  dz.addEventListener("click", () => input.click());
  input.addEventListener("change", () => { onFiles([...input.files]); input.value = ""; });
  ["dragover", "dragenter"].forEach((e) =>
    dz.addEventListener(e, (ev) => { ev.preventDefault(); dz.classList.add("over"); })
  );
  ["dragleave", "drop"].forEach((e) =>
    dz.addEventListener(e, (ev) => { ev.preventDefault(); dz.classList.remove("over"); })
  );
  dz.addEventListener("drop", (ev) => onFiles([...ev.dataTransfer.files]));
}

bindDrop(dzC, inpC, addConvFiles);

let convMeta = [];

function addConvFiles(files) {
  const list = [...files];
  if (!list.length) return;
  const fd = new FormData();
  list.forEach((f) => fd.append("files", f));
  fetch("/api/inspect", { method: "POST", body: fd })
    .then((r) => r.json())
    .then((data) => {
      data.files.forEach((info, idx) => {
        convFiles.push(list[idx]);
        convMeta.push({ src: info.src, targets: info.targets });
        if (!info.src) toast(`لم أتعرّف على نوع: ${list[idx].name}`, false);
      });
      renderConvList();
    });
}

function renderConvList() {
  const ul = $("#list-convert");
  ul.innerHTML = "";
  convFiles.forEach((f, i) => {
    const li = document.createElement("li");
    const src = convMeta[i]?.src || extOf(f.name) || "؟";
    li.innerHTML = `<span>${f.name}</span><span class="ext">${src.toUpperCase()} → ؟</span>`;
    const x = document.createElement("button");
    x.textContent = "✕";
    x.onclick = () => { convFiles.splice(i, 1); convMeta.splice(i, 1); renderConvList(); };
    li.appendChild(x);
    ul.appendChild(li);
  });
  updateTargets();
}

const FORMAT_GROUPS = [
  { name: "📄 مستندات", exts: ["pdf", "docx", "odt", "rtf", "txt", "md", "html"] },
  { name: "📽️ عروض تقديمية", exts: ["pptx"] },
  { name: "📚 كتب ومانجا", exts: ["epub", "fb2", "cbz", "xps"] },
  { name: "🖼️ صور شائعة", exts: ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "ico", "svg"] },
  { name: "🎞️ صور متخصصة", exts: ["avif", "heic", "heif", "jp2", "tga", "pcx", "ppm", "dds", "sgi", "im", "eps", "xbm", "cur", "qoi", "psd", "wmf", "icns", "mpo", "xpm"] },
  { name: "📊 جداول", exts: ["xlsx", "xls", "csv", "tsv"] },
  { name: "🧩 بيانات", exts: ["json", "xml", "yaml", "toml", "ini", "cfg", "conf"] },
  { name: "✍️ نصوص ومترجمات", exts: ["tex", "rst", "srt", "vtt", "log"] },
  { name: "🗜️ أرشيف", exts: ["extract", "zip", "7z", "tar", "tar.gz"] },
];
const LABELS = {
  extract: "فك الضغط", "tar.gz": "TAR.GZ", heic: "HEIC", heif: "HEIF",
  jpeg: "JPEG", tga: "TGA", pcx: "PCX", ppm: "PPM", dds: "DDS", sgi: "SGI",
  im: "IM", eps: "EPS", xbm: "XBM", cur: "CUR", qoi: "QOI", psd: "PSD",
  wmf: "WMF", icns: "ICNS", mpo: "MPO", xpm: "XPM", jp2: "JP2", avif: "AVIF",
  ico: "ICO", svg: "SVG", odt: "ODT", rtf: "RTF", epub: "EPUB", fb2: "FB2",
  cbz: "CBZ", xps: "XPS", tsv: "TSV", yaml: "YAML", toml: "TOML", ini: "INI",
  cfg: "CFG", conf: "CONF", tex: "TEX", rst: "RST", srt: "SRT", vtt: "VTT", log: "LOG",
};
let supported = new Set();
let chosenTarget = null;

function renderPicker(filter = "") {
  const box = $("#target-groups");
  box.innerHTML = "";
  for (const g of FORMAT_GROUPS) {
    let items = g.exts.filter((e) => supported.has(e));
    if (filter)
      items = items.filter((e) => e.includes(filter) || (LABELS[e] || "").includes(filter));
    if (!items.length) continue;
    const div = document.createElement("div");
    div.innerHTML = `<div class="grp-title">${g.name}</div>`;
    const chips = document.createElement("div");
    chips.className = "chips";
    for (const e of items) {
      const b = document.createElement("button");
      b.className = "chip" + (e === chosenTarget ? " active" : "");
      b.textContent = (LABELS[e] || e).toUpperCase();
      b.onclick = () => {
        chosenTarget = e;
        $("#target-label").textContent = "→ " + b.textContent;
        $("#target-panel").hidden = true;
        $("#btn-convert").disabled = false;
        renderPicker(filter);
      };
      chips.appendChild(b);
    }
    div.appendChild(chips);
    box.appendChild(div);
  }
  if (!box.children.length)
    box.innerHTML = '<div class="muted">لا توجد صيغة مناسبة لهذه الملفات</div>';
}

function updateTargets() {
  supported = new Set();
  chosenTarget = null;
  $("#target-label").textContent = "";
  $("#btn-convert").disabled = true;
  $("#target-open").disabled = true;
  if (!convFiles.length) return;
  if (convMeta.some((m) => !m.src)) return; // ملف لم يتم التعرف عليه
  let common = convMeta[0].targets;
  for (const m of convMeta.slice(1)) common = common.filter((t) => m.targets.includes(t));
  supported = new Set(common);
  $("#target-open").disabled = false;
  renderPicker($("#target-search").value.trim().toLowerCase());
}

$("#target-open").addEventListener("click", () => {
  $("#target-panel").hidden = !$("#target-panel").hidden;
});
$("#target-search").addEventListener("input", (e) =>
  renderPicker(e.target.value.trim().toLowerCase())
);

$("#btn-convert").addEventListener("click", async () => {
  const target = chosenTarget;
  if (!target) return;
  const st = $("#conv-status");
  st.className = "status";
  st.innerHTML = '<span class="spin"></span> جاري التحويل على جهازك...';
  $("#btn-convert").disabled = true;
  const fd = new FormData();
  convFiles.forEach((f) => fd.append("files", f));
  fd.append("target", target);
  try {
    const r = await fetch("/api/convert", { method: "POST", body: fd });
    if (!r.ok) throw new Error((await r.json()).error || "فشل التحويل");
    const blob = await r.blob();
    const cd = r.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename\*=UTF-8''([^;]+)/);
    const name = m ? decodeURIComponent(m[1]) : `محول.${blob.type.includes("zip") ? "zip" : target}`;
    download(blob, name);
    st.textContent = "✅ تم التحويل والتنزيل";
    st.className = "status ok";
  } catch (e) {
    st.textContent = "❌ " + e.message;
    st.className = "status err";
  } finally {
    $("#btn-convert").disabled = false;
  }
});

/* ---------- تفريغ النص OCR ---------- */
let ocrFile = null;

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

bindDrop($("#drop-ocr"), $("#file-ocr"), (files) => {
  if (!files.length) return;
  ocrFile = files[0];
  const ul = $("#list-ocr");
  ul.innerHTML = "";
  const li = document.createElement("li");
  li.innerHTML = `<span>${ocrFile.name}</span><span class="ext">OCR</span>`;
  const x = document.createElement("button");
  x.textContent = "✕";
  x.onclick = () => { ocrFile = null; ul.innerHTML = ""; $("#btn-ocr").disabled = true; };
  li.appendChild(x);
  ul.appendChild(li);
  $("#btn-ocr").disabled = false;
});

$("#btn-ocr").addEventListener("click", async () => {
  if (!ocrFile) return;
  const st = $("#ocr-status");
  st.className = "status";
  st.innerHTML = '<span class="spin"></span> جاري التفريغ على جهازك... (صفحات الـ PDF الممسوحة بتاخد ثواني لكل صفحة)';
  $("#btn-ocr").disabled = true;
  const fd = new FormData();
  fd.append("file", ocrFile);
  fd.append("lang", $("#ocr-lang").value);
  fd.append("fmt", $("#ocr-fmt").value);
  try {
    const r = await fetch("/api/ocr", { method: "POST", body: fd });
    if (!r.ok) throw new Error((await r.json()).error || "فشل التفريغ");
    const { text, engine, src } = await r.json();
    let out = text;
    if ($("#ocr-space").checked) {
      out = out.split(/\n+/).map((l) => l.trim()).filter(Boolean).join("\n\n");
    }
    const ta = $("#ocr-text");
    ta.value = out;
    ta.dir = $("#ocr-dir").value;
    ["ocr-copy", "ocr-txt", "ocr-pdf", "ocr-editor"].forEach((id) => ($("#" + id).disabled = false));
    st.textContent = "✅ تم التفريغ";
    st.className = "status ok";
    $("#ocr-meta").textContent = `المصدر: ${src.toUpperCase()} — المحرك: ${engine} — ${out.length} حرف`;
  } catch (e) {
    st.textContent = "❌ " + e.message;
    st.className = "status err";
  } finally {
    $("#btn-ocr").disabled = false;
  }
});

$("#ocr-copy").addEventListener("click", async () => {
  const t = $("#ocr-text").value;
  try {
    await navigator.clipboard.writeText(t);
    toast("تم نسخ النص 📋");
  } catch {
    const ta = $("#ocr-text");
    ta.designMode = "on"; ta.contentEditable = "true";
    ta.select(); document.execCommand("copy");
    toast("تم نسخ النص 📋");
  }
});

function dirMark() {
  const d = $("#ocr-dir").value;
  return d === "rtl" ? "\u200F" : d === "ltr" ? "\u200E" : "";
}

$("#ocr-txt").addEventListener("click", () => {
  const blob = new Blob(["\ufeff" + dirMark() + $("#ocr-text").value], { type: "text/plain;charset=utf-8" });
  download(blob, (ocrFile ? ocrFile.name.replace(/\.[^.]+$/, "") : "نص") + ".txt");
});

function textToBlocks(text) {
  const mark = dirMark();
  return text.split(/\n{2,}|\n(?=\S)/).filter((p) => p.trim()).map((p) => {
    p = mark + p.trim();
    if (p.startsWith("# ")) return { type: "text", html: `<h1>${escHtml(p.slice(2))}</h1>` };
    return { type: "text", html: `<p>${escHtml(p)}</p>` };
  });
}

$("#ocr-pdf").addEventListener("click", async () => {
  const blocks = textToBlocks($("#ocr-text").value);
  if (!blocks.length) return;
  try {
    const r = await fetch("/api/create", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: "pdf", name: "نص-متفرغ", blocks }),
    });
    if (!r.ok) throw new Error((await r.json()).error || "فشل الحفظ");
    download(await r.blob(), "نص-متفرغ.pdf");
    toast("تم تنزيل PDF ⬇");
  } catch (e) { toast(e.message, false); }
});

$("#ocr-editor").addEventListener("click", () => {
  const d = $("#ocr-dir").value;
  const paras = $("#ocr-text").value.split(/\n{2,}|\n(?=\S)/).filter((p) => p.trim());
  for (const p of paras) {
    p = p.trim();
    const b = p.startsWith("# ") ? makeBlock(`<h1>${escHtml(p.slice(2))}</h1>`) : makeBlock(`<p>${escHtml(p)}</p>`);
    if (d !== "auto") b.querySelector(".content").dir = d;
  }
  toast("أُضيف النص للمحرر ✏️");
});

/* ---------- تحليل وفحص المجلدات ---------- */
function renderTree(node, depth = 0) {
  if (node.dir) {
    const det = document.createElement("details");
    if (depth < 1) det.open = true;
    const sum = document.createElement("summary");
    sum.innerHTML = `📁 <b>${escHtml(node.name)}</b>${node.blocked ? ' <span class="muted">(ممنوع الوصول)</span>' : ""}`;
    det.appendChild(sum);
    for (const c of node.children || []) det.appendChild(renderTree(c, depth + 1));
    return det;
  }
  const div = document.createElement("div");
  div.className = "tfile";
  const warn = node.warn ? ` <span title="${escHtml(node.warn)}">⚠️</span>` : "";
  div.innerHTML = `📄 ${escHtml(node.name)} <span class="muted" dir="ltr">(${node.size_h})</span>${warn}`;
  return div;
}

async function analyzeFolder() {
  const path = $("#an-path").value.trim();
  if (!path) return toast("اكتب مسار المجلد الأول", false);
  const st = $("#an-status");
  st.className = "status";
  st.innerHTML = '<span class="spin"></span> جاري التحليل على جهازك...';
  $("#btn-analyze").disabled = true;
  try {
    const r = await fetch("/api/folder", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, deep: $("#an-deep").checked }),
    });
    if (!r.ok) throw new Error((await r.json()).error || "فشل التحليل");
    const d = await r.json();
    d.archives = d.archives || [];
    d.issues = d.issues || [];
    renderAnalysis(d);
    st.textContent = "✅ انتهى التحليل";
    st.className = "status ok";
  } catch (e) {
    st.textContent = "❌ " + e.message;
    st.className = "status err";
  } finally {
    $("#btn-analyze").disabled = false;
  }
}
$("#btn-analyze").addEventListener("click", analyzeFolder);
$("#an-path").addEventListener("keydown", (e) => { if (e.key === "Enter") analyzeFolder(); });

$("#btn-scanfile").addEventListener("click", async () => {
  const p = $("#an-file").value.trim();
  if (!p) return toast("اكتب مسار الملف", false);
  const st = $("#an-status");
  st.className = "status";
  st.innerHTML = '<span class="spin"></span> جاري الفحص...';
  try {
    const r = await fetch("/api/folder/scan-file", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: p }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "فشل الفحص");
    st.textContent = d.msg.startsWith("لا توجد") ? "✅ " + d.msg : "⚠️ " + d.msg;
    st.className = d.msg.startsWith("لا توجد") ? "status ok" : "status err";
  } catch (e) {
    st.textContent = "❌ " + e.message;
    st.className = "status err";
  }
});

/* ---------- تحليل المجلدات بالسحب ---------- */
const ARC_EXTS = ["zip", "7z", "tar", "gz", "tgz", "bz2", "xz", "tar.gz", "tar.bz2", "tar.xz"];
const SCAN_LIMIT = 600, ARC_LIMIT = 30;

async function walkEntry(entry, prefix) {
  const node = { name: entry.name, dir: entry.isDirectory, children: [] };
  const files = [];
  if (entry.isDirectory) {
    const reader = entry.createReader();
    const entries = [];
    while (true) {
      const batch = await new Promise((res, rej) => reader.readEntries(res, rej));
      if (!batch.length) break;
      entries.push(...batch);
    }
    for (const child of entries) {
      const [r, f] = await walkEntry(child, prefix + entry.name + "/");
      node.children.push(r);
      files.push(...f);
    }
    node.children.sort((a, b) => (b.dir - a.dir) || a.name.localeCompare(b.name, "ar"));
  } else {
    const file = await new Promise((res) => entry.file(res, () => res(null)));
    if (!file) return [node, files];
    const ext = (file.name.toLowerCase().match(/\.([^.]+)$/) || ["", "بدون"])[1];
    node.size_h = humanSize(file.size);
    node.ext = ext;
    files.push({ file, path: prefix + entry.name, node, ext });
  }
  return [node, files];
}

function humanSize(n) {
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < 4) { n /= 1024; i++; }
  return n.toFixed(i ? 1 : 0) + " " + u[i];
}

function statsFromDrop(root, files) {
  const exts = {}, cats = {};
  let dirs = 0, total = 0, maxDepth = 0;
  const walk = (n, d) => {
    maxDepth = Math.max(maxDepth, d);
    if (n.dir) { dirs++; (n.children || []).forEach((c) => walk(c, d + 1)); }
    else total += files.find((f) => f.node === n)?.file.size || 0;
  };
  walk(root, 0);
  for (const f of files) {
    exts[f.ext] = (exts[f.ext] || 0) + 1;
    const cat = ["png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff", "ico", "svg", "heic", "avif", "psd", "cur"].includes(f.ext) ? "صور"
      : ["mp4", "mkv", "avi", "mov", "webm", "wmv", "flv", "mpeg"].includes(f.ext) ? "فيديوهات"
      : ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus"].includes(f.ext) ? "صوتيات"
      : ["pdf", "docx", "doc", "txt", "md", "html", "rtf", "odt", "pptx", "xls", "xlsx", "csv", "epub"].includes(f.ext) ? "مستندات"
      : ARC_EXTS.includes(f.ext) ? "أرشيفات" : "أخرى";
    cats[cat] = (cats[cat] || 0) + 1;
  }
  return {
    tree: root,
    stats: { dirs, files: files.length, total_size_h: humanSize(total), max_depth: maxDepth, scanned: 0, truncated: files.length > SCAN_LIMIT },
    exts: Object.entries(exts).sort((a, b) => b[1] - a[1]).slice(0, 40).map(([ext, count]) => ({ ext, count, size_h: "" })),
    cats: Object.entries(cats).sort((a, b) => b[1] - a[1]).map(([cat, count]) => ({ cat, count })),
    archives: [], issues: [],
  };
}

function renderAnalysis(d) {
  $("#an-results").hidden = false;
  const s = d.stats;
  $("#an-summary").innerHTML = `
    <div class="stat"><b>${s.dirs}</b><span>مجلد</span></div>
    <div class="stat"><b>${s.files}</b><span>ملف</span></div>
    <div class="stat"><b>${s.total_size_h}</b><span>الحجم الكلي</span></div>
    <div class="stat"><b>${s.max_depth + 1}</b><span>عمق الطبقات</span></div>
    <div class="stat"><b>${s.scanned || "—"}</b><span>ملفات اتفحصت</span></div>`;
  $("#an-cats").innerHTML = d.cats.map((c) => `<button class="chip" disabled>${c.cat}: <b>${c.count}</b></button>`).join("");
  $("#an-exts").innerHTML = d.exts.map((e) =>
    `<div class="extrow"><span class="ext">${escHtml(e.ext)}</span><span>${e.count} ملف</span><span class="muted">${e.size_h || ""}</span></div>`).join("")
    || '<div class="muted">لا ملفات</div>';
  const treeBox = $("#an-tree");
  treeBox.innerHTML = "";
  treeBox.appendChild(renderTree(d.tree));
  if (s.truncated) treeBox.innerHTML += '<div class="muted">⚠ المجلد ضخم — الفحص اتقف عند حد العدد</div>';
  const arc = $("#an-archives");
  if (arc) {
    arc.innerHTML = (d.archives || []).length
      ? d.archives.map((a) => `<div class="issue" style="border-color:var(--line-2);background:var(--surface-2)">
          <b dir="ltr" style="float:inline-start">${escHtml(a.path)}</b>
          <div style="color:var(--text)">📦 ${a.members} عضو${a.nested ? ` — وفيه ${a.nested} أرشيف جواه` : ""} — ${a.bad ? `<span style="color:var(--err)">${a.bad} ملف جواه بيكذب</span>` : '<span style="color:var(--ok)">مفيش مشاكل جواه</span>'}</div>
          <div style="color:var(--muted);font-size:11.5px">${(a.exts || []).slice(0, 8).map((e) => `.${e[0]}×${e[1]}`).join("، ")}</div>
        </div>`).join("")
      : '<div class="muted">مفيش مضغوطات في المجلد ده.</div>';
  }
  const iss = $("#an-issues");
  if (!d.issues.length) {
    iss.className = "status ok";
    iss.textContent = s.scanned ? `✅ تم فحص ${s.scanned} ملف — مفيش أي مشكلة ولا امتداد بيكذب` : "الفحص العميق كان مقفول";
  } else {
    iss.className = "";
    iss.innerHTML = `<div class="status err">⚠️ ${d.issues.length} ملف فيه مشكلة:</div>` +
      d.issues.map((i) => `<div class="issue" dir="auto"><b dir="ltr">${escHtml(i.path)}</b> <span class="muted">(${i.size_h})</span><div>${escHtml(i.msg)}</div></div>`).join("");
  }
}

async function analyzeDrop(root, files) {
  const d = statsFromDrop(root, files);
  renderAnalysis(d);
  if (!$("#an-deep").checked) { $("#an-status").textContent = "✅ الرسم اتبنى — الفحص العميق كان مقفول"; return; }
  const st = $("#an-status");
  const scanList = files.slice(0, SCAN_LIMIT);
  const arcs = files.filter((f) => ARC_EXTS.includes(f.ext)).slice(0, ARC_LIMIT);
  let done = 0;
  for (let i = 0; i < scanList.length; i += 30) {
    const batch = scanList.slice(i, i + 30);
    const fd = new FormData();
    batch.forEach((f) => fd.append("files", f.file.slice(0, 65536), f.file.name));
    try {
      const r = await fetch("/api/scan", { method: "POST", body: fd });
      if (!r.ok) throw new Error("فشل الاتصال");
      const { results } = await r.json();
      results.forEach((res, k) => {
        done++;
        if (res.msg) {
          d.issues.push({ path: batch[k].path, msg: res.msg, size_h: batch[k].node.size_h });
          batch[k].node.warn = res.msg;
        }
      });
    } catch (e) { /* كمّل الباقي */ }
    st.innerHTML = `<span class="spin"></span> جاري الفحص… ${done}/${scanList.length} ملف`;
    d.stats.scanned = done;
    renderAnalysis(d);
  }
  for (const a of arcs) {
    if (a.file.size > 300 * 1024 * 1024) continue;
    st.innerHTML = `<span class="spin"></span> جاري فحص المضغوطات…`;
    try {
      const fd = new FormData();
      fd.append("file", a.file, a.file.name);
      const r = await fetch("/api/scan-archive", { method: "POST", body: fd });
      const sub = await r.json();
      if (r.ok && sub.members !== undefined) {
        d.archives.push({ path: a.path, members: sub.members, nested: sub.nested, bad: sub.issues.length, exts: sub.exts, size_h: a.node.size_h });
        sub.issues.forEach((is) => d.issues.push(is));
      }
    } catch (e) { /* كمّل */ }
    d.stats.scanned = done;
    renderAnalysis(d);
  }
  st.textContent = done ? `✅ انتهى الفحص — ${d.issues.length} مشكلة من ${done} ملف` : "❌ فشل الفحص";
  st.className = done ? "status ok" : "status err";
}

/* dropzone التحليل: بيقبل فولدرات بجرها */
const dzA = $("#drop-analyze"), inA = $("#file-analyze");
inA.addEventListener("change", async () => {
  const list = [...inA.files];
  inA.value = "";
  if (!list.length) return;
  const rootName = list[0].webkitRelativePath.split("/")[0] || "مجلد";
  const root = { name: rootName, dir: true, children: [] };
  const files = [];
  const map = new Map([["", root]]);
  for (const f of list) {
    const parts = f.webkitRelativePath.split("/");
    let cur = root, key = "";
    for (let i = 0; i < parts.length - 1; i++) {
      const pkey = key + "/" + parts[i];
      if (!map.has(pkey)) {
        const nd = { name: parts[i], dir: true, children: [] };
        map.get(key).children.push(nd);
        map.set(pkey, nd);
      }
      key = pkey; cur = map.get(key);
    }
    const fname = parts[parts.length - 1];
    const ext = (fname.toLowerCase().match(/\.([^.]+)$/) || ["", "بدون"])[1];
    const node = { name: fname, dir: false, size_h: humanSize(f.size), ext };
    cur.children.push(node);
    files.push({ file: f, path: f.webkitRelativePath, node, ext });
  }
  analyzeDrop(root, files);
});
dzA.addEventListener("click", () => inA.click());
["dragover", "dragenter"].forEach((ev) => dzA.addEventListener(ev, (e) => { e.preventDefault(); dzA.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => dzA.addEventListener(ev, (e) => { e.preventDefault(); dzA.classList.remove("over"); }));
dzA.addEventListener("drop", async (e) => {
  const items = [...e.dataTransfer.items].map((it) => it.webkitGetAsEntry && it.webkitGetAsEntry()).filter(Boolean);
  if (!items.length) return toast("معلش — جررو فولدر من المستكشف", false);
  let root, files;
  if (items.length === 1 && items[0].isDirectory) {
    [root, files] = await walkEntry(items[0], "");
  } else {
    root = { name: "ملفات مسحوبة", dir: true, children: [] };
    files = [];
    for (const it of items) {
      const [n, fs] = await walkEntry(it, "");
      root.children.push(n);
      files.push(...fs);
    }
  }
  analyzeDrop(root, files);
});

/* ---------- المحرر ---------- */
const blocksEl = $("#blocks");
let dragSrc = null;

function makeBlock(html, isImage = false, dataUrl = "") {
  const div = document.createElement("div");
  div.className = "block";
  div.draggable = true;
  div.innerHTML = `<span class="handle">⠿</span><button class="x" title="حذف">✕</button>`;
  const content = document.createElement("div");
  content.className = "content";
  if (isImage) {
    content.innerHTML = `<img src="${dataUrl}">`;
    div.dataset.type = "image";
    div.dataset.data = dataUrl;
  } else {
    content.contentEditable = "true";
    content.dir = "auto";
    content.innerHTML = html || "<p>اكتب هنا...</p>";
    div.dataset.type = "text";
  }
  div.appendChild(content);
  div.querySelector(".x").onclick = () => div.remove();
  div.addEventListener("dragstart", () => (dragSrc = div));
  div.addEventListener("dragend", () => { dragSrc = null; div.classList.remove("dragging"); });
  div.addEventListener("dragover", (e) => { e.preventDefault(); div.classList.add("dragover"); });
  div.addEventListener("dragleave", () => div.classList.remove("dragover"));
  div.addEventListener("drop", (e) => {
    e.preventDefault();
    div.classList.remove("dragover");
    if (!dragSrc || dragSrc === div) return;
    const rect = div.getBoundingClientRect();
    const after = e.clientY > rect.top + rect.height / 2;
    blocksEl.insertBefore(dragSrc, after ? div.nextSibling : div);
  });
  blocksEl.appendChild(div);
  if (!isImage) content.focus();
  return div;
}

$("#add-text").onclick = () => makeBlock("<p>اكتب هنا...</p>");

bindDrop($("#drop-create"), $("#file-create"), async (files) => {
  for (const f of files) {
    const fd = new FormData();
    fd.append("file", f);
    const r = await fetch("/api/extract", { method: "POST", body: fd });
    if (!r.ok) { toast((await r.json()).error || "خطأ في " + f.name, false); continue; }
    const { blocks } = await r.json();
    for (const b of blocks)
      b.type === "image" ? makeBlock("", true, b.data) : makeBlock(b.html);
    toast(`تم إدراج ${f.name} في المحرر`);
  }
});

$("#add-image").onclick = () => $("#file-inline").click();
$("#file-inline").addEventListener("change", () => {
  for (const f of $("#file-inline").files) {
    const rd = new FileReader();
    rd.onload = () => makeBlock("", true, rd.result);
    rd.readAsDataURL(f);
  }
  $("#file-inline").value = "";
});

/* أدوات التنسيق */
$$("#fmt-toolbar button[data-cmd]").forEach((b) =>
  b.addEventListener("mousedown", (e) => {
    e.preventDefault();
    document.execCommand(b.dataset.cmd, false, null);
  })
);
$("#block-type").addEventListener("change", (e) => {
  document.execCommand("formatBlock", false, "<" + e.target.value + ">");
  e.target.value = "p";
});
$("#font-size").addEventListener("change", (e) => {
  if (e.target.value) document.execCommand("fontSize", false, e.target.value);
  e.target.value = "";
});
$("#text-color").addEventListener("input", (e) =>
  document.execCommand("foreColor", false, e.target.value)
);

let createFmt = "pdf";
$$("#create-fmts .chip").forEach((c) =>
  c.addEventListener("click", () => {
    $$("#create-fmts .chip").forEach((x) => x.classList.remove("active"));
    c.classList.add("active");
    createFmt = c.dataset.fmt;
  })
);

$("#btn-create").addEventListener("click", async () => {
  const blocks = $$("#blocks .block").map((b) =>
    b.dataset.type === "image"
      ? { type: "image", data: b.dataset.data }
      : { type: "text", html: b.querySelector(".content").innerHTML }
  );
  if (!blocks.length) return toast("المحرر فاضي — أضف نص أو صورة", false);
  const st = $("#create-status");
  st.className = "status";
  st.innerHTML = '<span class="spin"></span> جاري الإنشاء...';
  try {
    const r = await fetch("/api/create", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: createFmt, name: $("#doc-name").value || "مستند", blocks }),
    });
    if (!r.ok) throw new Error((await r.json()).error || "فشل الحفظ");
    const blob = await r.blob();
    const cd = r.headers.get("Content-Disposition") || "";
    const m = cd.match(/filename\*=UTF-8''([^;]+)/);
    download(blob, m ? decodeURIComponent(m[1]) : `مستند.${createFmt}`);
    st.textContent = "✅ تم التصدير";
    st.className = "status ok";
  } catch (e) {
    st.textContent = "❌ " + e.message;
    st.className = "status err";
  }
});

makeBlock("<h1>عنوان المستند</h1>");
makeBlock("<p>ابدأ الكتابة هنا، أو ارفع ملفات من الجانب.</p>");
