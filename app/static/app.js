// State Variables
let documentsList = [];
let activeDocId = null;
let currentChart = null;

// Initialize Elements on Load
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initEngine();
  fetchDocuments();
  setupEventListeners();
});

function initTheme() {
  const savedTheme = localStorage.getItem("docuextract_theme") || "dark";
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  const root = document.documentElement;
  const label = document.getElementById("theme-toggle-label");
  const btn = document.getElementById("btn-theme-toggle");
  if (theme === "light") {
    root.classList.add("theme-light");
    if (label) label.innerText = "Dark Theme";
    if (btn) {
      const iconEl = btn.querySelector("i, svg");
      if (iconEl) {
        iconEl.outerHTML = '<i id="theme-toggle-icon" data-lucide="moon" class="w-4 h-4 text-slate-600"></i>';
      }
    }
  } else {
    root.classList.remove("theme-light");
    if (label) label.innerText = "White Theme";
    if (btn) {
      const iconEl = btn.querySelector("i, svg");
      if (iconEl) {
        iconEl.outerHTML = '<i id="theme-toggle-icon" data-lucide="sun" class="w-4 h-4 text-amber-400"></i>';
      }
    }
  }
  if (typeof lucide !== "undefined") {
    lucide.createIcons();
  }
}

function getCurrencySymbol(curr) {
  const c = (curr || "USD").toString().trim().toUpperCase();
  if (c === "INR") return "₹";
  if (c === "EUR") return "€";
  if (c === "GBP") return "£";
  return "$";
}

function formatCurrencyAmount(val, curr) {
  const sym = getCurrencySymbol(curr);
  const num = Number(val || 0);
  return `${sym}${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// Setup Engine and Settings
async function initEngine() {
  const savedKey = localStorage.getItem("gemini_api_key");
  if (savedKey) {
    document.getElementById("input-api-key").value = savedKey;
  }
  try {
    const res = await fetch("/api/config");
    if (res.ok) {
      const cfg = await res.json();
      const modelEl = document.getElementById("settings-configured-model");
      if (modelEl && cfg.configured_model) {
        modelEl.innerText = cfg.configured_model;
      }
    }
  } catch (e) {}
  updateEngineStatus("Local Parser");
  lucide.createIcons();
}

function updateEngineStatus(engineType) {
  const indicator = document.getElementById("engine-status-indicator");
  const text = document.getElementById("engine-status-text");
  
  if (engineType === "Gemini AI") {
    indicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse";
    text.innerText = "Engine: Gemini AI";
  } else if (engineType === "Mock Mode") {
    indicator.className = "w-2.5 h-2.5 rounded-full bg-slate-400";
    text.innerText = "Engine: Mock Mode";
  } else {
    indicator.className = "w-2.5 h-2.5 rounded-full bg-amber-400";
    text.innerText = "Engine: Local Parser";
  }
}

// Event Listeners Setup
function setupEventListeners() {
  // Theme Toggle Controls
  const btnThemeToggle = document.getElementById("btn-theme-toggle");
  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const isLight = document.documentElement.classList.contains("theme-light");
      const nextTheme = isLight ? "dark" : "light";
      localStorage.setItem("docuextract_theme", nextTheme);
      applyTheme(nextTheme);
    });
  }

  // Settings Modal Controls
  const btnSettings = document.getElementById("btn-settings");
  const modalSettings = document.getElementById("modal-settings");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const btnClearSettings = document.getElementById("btn-clear-settings");
  const btnToggleKeyVis = document.getElementById("btn-toggle-key-vis");
  const inputApiKey = document.getElementById("input-api-key");

  btnSettings.addEventListener("click", () => {
    modalSettings.classList.remove("hidden");
    setTimeout(() => {
      modalSettings.classList.remove("opacity-0");
      document.getElementById("settings-card").classList.remove("scale-95");
    }, 10);
  });

  const closeSettings = () => {
    modalSettings.classList.add("opacity-0");
    document.getElementById("settings-card").classList.add("scale-95");
    setTimeout(() => modalSettings.classList.add("hidden"), 200);
  };

  btnCloseSettings.addEventListener("click", closeSettings);
  modalSettings.addEventListener("click", (e) => {
    if (e.target === modalSettings) closeSettings();
  });

  btnToggleKeyVis.addEventListener("click", () => {
    if (inputApiKey.type === "password") {
      inputApiKey.type = "text";
      btnToggleKeyVis.innerHTML = '<i data-lucide="eye-off" class="w-4 h-4"></i>';
    } else {
      inputApiKey.type = "password";
      btnToggleKeyVis.innerHTML = '<i data-lucide="eye" class="w-4 h-4"></i>';
    }
    lucide.createIcons();
  });

  btnSaveSettings.addEventListener("click", () => {
    const key = inputApiKey.value.trim();
    const activeDoc = documentsList.find(d => d.id === activeDocId);
    const currentEngine = activeDoc ? (activeDoc.engine_used || "Local Parser") : "Local Parser";
    if (key) {
      localStorage.setItem("gemini_api_key", key);
      showToast("Settings Saved", "Gemini API key saved. Engine status will reflect actual extraction result.", "success");
    } else {
      localStorage.removeItem("gemini_api_key");
    }
    updateEngineStatus(currentEngine);
    closeSettings();
  });

  btnClearSettings.addEventListener("click", () => {
    inputApiKey.value = "";
    localStorage.removeItem("gemini_api_key");
    const activeDoc = documentsList.find(d => d.id === activeDocId);
    updateEngineStatus(activeDoc ? (activeDoc.engine_used || "Local Parser") : "Local Parser");
    showToast("Settings Cleared", "API key removed from browser storage.", "info");
    closeSettings();
  });

  // Drag & Drop
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");

  dropZone.addEventListener("click", () => fileInput.click());
  
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-brand-500", "bg-brand-500/5");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-brand-500", "bg-brand-500/5");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-brand-500", "bg-brand-500/5");
    
    if (e.dataTransfer.files.length > 0) {
      uploadFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      uploadFile(fileInput.files[0]);
    }
  });

  // Search & Filter
  document.getElementById("search-input").addEventListener("input", filterQueue);
  document.getElementById("filter-type").addEventListener("change", filterQueue);
  document.getElementById("filter-status").addEventListener("change", filterQueue);

  // Raw JSON display controls
  const btnRawJson = document.getElementById("btn-raw-json");
  const modalJson = document.getElementById("modal-json");
  const btnCloseJson = document.getElementById("btn-close-json");
  const btnCopyJson = document.getElementById("btn-copy-json");

  btnRawJson.addEventListener("click", () => {
    const doc = documentsList.find(d => d.id === activeDocId);
    if (!doc) return;
    
    document.getElementById("json-raw-display").innerText = JSON.stringify(doc.extracted_data, null, 2);
    modalJson.classList.remove("hidden");
    setTimeout(() => {
      modalJson.classList.remove("opacity-0");
      document.getElementById("json-card").classList.remove("scale-95");
    }, 10);
  });

  const closeJson = () => {
    modalJson.classList.add("opacity-0");
    document.getElementById("json-card").classList.add("scale-95");
    setTimeout(() => modalJson.classList.add("hidden"), 200);
  };

  btnCloseJson.addEventListener("click", closeJson);
  modalJson.addEventListener("click", (e) => {
    if (e.target === modalJson) closeJson();
  });

  btnCopyJson.addEventListener("click", () => {
    const jsonText = document.getElementById("json-raw-display").innerText;
    navigator.clipboard.writeText(jsonText)
      .then(() => showToast("Copied", "JSON schema copied to clipboard.", "success"))
      .catch(() => showToast("Error", "Could not copy JSON.", "error"));
  });

  // Save Approvals
  const form = document.getElementById("extraction-form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitApproval();
  });

  document.getElementById("btn-save-verify").addEventListener("click", submitApproval);
}

// Fetch and Render documents
async function fetchDocuments() {
  try {
    const response = await fetch("/api/documents");
    documentsList = await response.json();
    renderQueue();
    updateStats();
    if (!activeDocId && documentsList.length > 0) {
      selectDocument(documentsList[0].id);
    }
  } catch (error) {
    showToast("Error", "Failed to retrieve documents queue.", "error");
  }
}

function renderQueue() {
  const container = document.getElementById("queue-container");
  container.innerHTML = "";
  
  if (documentsList.length === 0) {
    container.innerHTML = `
      <div class="text-center py-8 text-slate-500">
        <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-slate-700"></i>
        <p class="text-xs">No documents processed yet</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  documentsList.forEach(doc => {
    const card = document.createElement("div");
    card.className = `queue-card-transition p-3 border rounded-xl cursor-pointer bg-slate-900 shadow-md ${
      doc.id === activeDocId ? "queue-card-active" : "border-slate-800 hover:border-slate-700"
    }`;
    
    // Status Badge/Icon
    let statusIcon = "";
    if (doc.status === "Verified") {
      statusIcon = '<i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-500"></i>';
    } else if (doc.review_required) {
      statusIcon = '<i data-lucide="alert-triangle" class="w-4 h-4 text-amber-500 animate-pulse"></i>';
    } else {
      statusIcon = '<i data-lucide="circle-dashed" class="w-4 h-4 text-slate-500"></i>';
    }

    // Type styling
    let typeBadge = "";
    if (doc.doc_type === "Invoice") {
      typeBadge = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    } else if (doc.doc_type === "Delivery Note") {
      typeBadge = "bg-violet-500/10 text-violet-400 border border-violet-500/20";
    } else if (doc.doc_type === "Contract") {
      typeBadge = "bg-sky-500/10 text-sky-400 border border-sky-500/20";
    } else {
      typeBadge = "bg-slate-500/10 text-slate-400 border border-slate-700";
    }

    // Short date formatting
    const confidencePct = Math.round(doc.confidence * 100);

    const engineUsed = doc.engine_used || "Local Parser";
    let engineBadgeColor = "text-amber-400 bg-amber-500/10 border-amber-500/20";
    if (engineUsed === "Gemini AI") {
      engineBadgeColor = "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    } else if (engineUsed === "Mock Mode") {
      engineBadgeColor = "text-slate-400 bg-slate-800 border-slate-700";
    }

    card.innerHTML = `
      <div class="flex items-start justify-between space-x-2">
        <div class="flex items-center space-x-2 min-w-0">
          ${statusIcon}
          <span class="text-xs font-semibold text-slate-200 truncate block">${doc.filename}</span>
        </div>
        <span class="text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-wider font-semibold font-mono ${
          confidencePct >= 90 ? "text-emerald-400" : confidencePct >= 70 ? "text-sky-400" : "text-rose-400"
        }">${confidencePct}%</span>
      </div>
      
      <div class="flex items-center justify-between mt-3 text-[10px]">
        <div class="flex items-center space-x-1.5">
          <span class="px-2 py-0.5 rounded-md font-semibold text-[9px] uppercase ${typeBadge}">${doc.doc_type}</span>
          <span class="px-1.5 py-0.2 rounded text-[8px] font-mono border ${engineBadgeColor}">${engineUsed}</span>
        </div>
        <span class="text-slate-500 font-mono">${doc.status}</span>
      </div>
    `;
    
    card.addEventListener("click", () => selectDocument(doc.id));
    container.appendChild(card);
  });
  
  lucide.createIcons();
}

function filterQueue() {
  const query = document.getElementById("search-input").value.toLowerCase();
  const typeFilter = document.getElementById("filter-type").value;
  const statusFilter = document.getElementById("filter-status").value;

  const cards = document.getElementById("queue-container").children;
  
  documentsList.forEach((doc, index) => {
    const matchesSearch = doc.filename.toLowerCase().includes(query);
    const matchesType = !typeFilter || doc.doc_type === typeFilter;
    const matchesStatus = !statusFilter || doc.status === statusFilter;
    
    const cardElement = cards[index];
    if (cardElement && cardElement.tagName === "DIV") {
      if (matchesSearch && matchesType && matchesStatus) {
        cardElement.classList.remove("hidden");
      } else {
        cardElement.classList.add("hidden");
      }
    }
  });
}

// Select and show active document details
function selectDocument(id) {
  activeDocId = id;
  const doc = documentsList.find(d => d.id === id);
  if (!doc) return;

  // Highlights active card in list
  renderQueue();

  // Hide empty state
  document.getElementById("empty-workspace-state").classList.add("opacity-0", "pointer-events-none");
  setTimeout(() => document.getElementById("empty-workspace-state").classList.add("hidden"), 300);

  // Engine Used Badge & Global Header Sync
  const eng = doc.engine_used || "Local Parser";
  updateEngineStatus(eng);
  const engineBadge = document.getElementById("badge-engine-used");
  if (engineBadge) {
    engineBadge.innerText = `Engine: ${eng}`;
    if (eng === "Gemini AI") {
      engineBadge.className = "text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/25";
    } else if (eng === "Mock Mode") {
      engineBadge.className = "text-[11px] font-semibold text-slate-400 bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-700";
    } else {
      engineBadge.className = "text-[11px] font-semibold text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/25";
    }
  }

  // Classify Badge Type styling
  const classificationBadge = document.getElementById("badge-classification");
  classificationBadge.innerText = doc.doc_type;
  
  if (doc.doc_type === "Invoice") {
    classificationBadge.className = "text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20";
  } else if (doc.doc_type === "Delivery Note") {
    classificationBadge.className = "text-xs font-semibold text-violet-400 bg-violet-500/10 px-2 py-0.5 rounded-md border border-violet-500/20";
  } else if (doc.doc_type === "Contract") {
    classificationBadge.className = "text-xs font-semibold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded-md border border-sky-500/20";
  } else {
    classificationBadge.className = "text-xs font-semibold text-slate-400 bg-slate-500/10 px-2 py-0.5 rounded-md border border-slate-700";
  }

  // Confidence Score Gauge
  const confPct = Math.round(doc.confidence * 100);
  const confLabel = document.getElementById("lbl-confidence");
  confLabel.innerText = `${confPct}%`;
  
  if (confPct >= 90) {
    confLabel.className = "text-xs font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/25";
  } else if (confPct >= 70) {
    confLabel.className = "text-xs font-bold px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/25";
  } else {
    confLabel.className = "text-xs font-bold px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/25 animate-pulse";
  }

  // Warning alerts
  const warningBox = document.getElementById("review-warning-box");
  const reasonsList = document.getElementById("review-reasons-list");
  reasonsList.innerHTML = "";
  
  if (doc.review_required) {
    warningBox.classList.remove("hidden");
    doc.review_reasons.forEach(reason => {
      const li = document.createElement("li");
      li.innerText = reason;
      reasonsList.appendChild(li);
    });
  } else {
    warningBox.classList.add("hidden");
  }

  // Draw Document Preview
  renderDocumentVisual(doc);

  // Draw Data Fields Form
  renderExtractionForm(doc);
  
  lucide.createIcons();
}

// Generate the beautiful Paper visual preview
function renderDocumentVisual(doc) {
  const visualTitle = document.getElementById("visual-title");
  const visualDocId = document.getElementById("visual-doc-id");
  const visualBody = document.getElementById("visual-body");
  const visualSmudge = document.getElementById("visual-smudge");
  const previewFileType = document.getElementById("preview-file-type");
  const previewEngineBadge = document.getElementById("preview-engine-badge");
  
  visualDocId.innerText = `ID: ${doc.id}`;
  visualTitle.innerText = doc.doc_type.toUpperCase();

  if (previewEngineBadge) {
    const eng = doc.engine_used || "Local Parser";
    previewEngineBadge.innerText = eng;
    if (eng === "Gemini AI") {
      previewEngineBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold border text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    } else if (eng === "Mock Mode") {
      previewEngineBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold border text-slate-400 bg-slate-800 border-slate-700";
    } else {
      previewEngineBadge.className = "text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold border text-amber-400 bg-amber-500/10 border-amber-500/20";
    }
  }

  // Reset visual blurry blur effects
  visualSmudge.classList.add("hidden");
  
  // Set file type badge
  if (doc.filename.endsWith(".jpg") || doc.filename.endsWith(".jpeg") || doc.filename.endsWith(".png")) {
    previewFileType.innerText = "IMAGE File";
    previewFileType.className = "text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20";
  } else {
    previewFileType.innerText = "PDF Document";
    previewFileType.className = "text-[10px] px-2 py-0.5 rounded-full font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
  }

  if (doc.filename.includes("blurry")) {
    visualSmudge.classList.remove("hidden");
  }

  let html = "";
  const data = doc.extracted_data;

  if (doc.doc_type === "Invoice" && data && Object.keys(data).length > 0) {
    const curr = (data.currency || "USD").toUpperCase();
    const currSym = getCurrencySymbol(curr);
    html = `
      <div class="space-y-1">
        <p class="text-[10px] text-slate-400 font-semibold">VENDOR</p>
        <p class="text-sm font-bold text-white leading-tight">${data.vendor_name || '—'}</p>
      </div>
      <div class="grid grid-cols-2 gap-2 text-[10px] border-t border-slate-800 pt-2">
        <div>
          <span class="text-slate-500 block">INVOICE NO.</span>
          <span class="text-slate-300 font-mono font-semibold">${data.invoice_number || '—'}</span>
        </div>
        <div>
          <span class="text-slate-500 block">DATE</span>
          <span class="text-slate-300 font-mono">${data.invoice_date || '—'}</span>
        </div>
      </div>
      <div class="border-t border-slate-800 pt-2">
        <span class="text-[10px] text-slate-500 block mb-1">LINE ITEMS (${curr})</span>
        <div class="space-y-1.5">
          ${(data.line_items || []).map(item => `
            <div class="flex justify-between items-center text-[10px] bg-slate-950 p-1.5 rounded border border-slate-900">
              <span class="text-slate-300 truncate max-w-[140px]">${item.description}</span>
              <span class="text-slate-400 font-mono font-medium">${item.quantity} × ${formatCurrencyAmount(item.price || 0, curr)} = <strong class="text-emerald-400">${formatCurrencyAmount(item.amount || 0, curr)}</strong></span>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="border-t border-slate-800 pt-2 mt-auto text-[10px] space-y-0.5">
        <div class="flex justify-between items-center text-slate-400">
          <span>SUBTOTAL</span>
          <span class="font-mono">${formatCurrencyAmount(data.subtotal || 0, curr)}</span>
        </div>
        ${(data.cgst !== undefined && data.cgst !== null) ? `
          <div class="flex justify-between items-center text-slate-400">
            <span>CGST</span>
            <span class="font-mono">${formatCurrencyAmount(data.cgst, curr)}</span>
          </div>
        ` : ''}
        ${(data.sgst !== undefined && data.sgst !== null) ? `
          <div class="flex justify-between items-center text-slate-400">
            <span>SGST</span>
            <span class="font-mono">${formatCurrencyAmount(data.sgst, curr)}</span>
          </div>
        ` : ''}
        <div class="flex justify-between items-center text-slate-400">
          <span>TOTAL TAX</span>
          <span class="font-mono">${formatCurrencyAmount(data.tax || 0, curr)}</span>
        </div>
        <div class="flex justify-between items-center text-xs pt-1 border-t border-slate-800/60">
          <span class="text-slate-400 font-medium">GRAND TOTAL</span>
          <span class="text-sm font-bold text-emerald-400 font-mono">${formatCurrencyAmount(data.total || 0, curr)}</span>
        </div>
      </div>
    `;
  } else if (doc.doc_type === "Delivery Note" && data && Object.keys(data).length > 0) {
    html = `
      <div class="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <span class="text-slate-500 block">SENDER</span>
          <span class="text-slate-200 font-semibold leading-tight">${data.sender_name || '—'}</span>
        </div>
        <div>
          <span class="text-slate-500 block">RECIPIENT</span>
          <span class="text-slate-200 font-semibold leading-tight">${data.recipient_name || '—'}</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2 text-[10px] border-t border-slate-800 pt-2">
        <div>
          <span class="text-slate-500 block">DELIVERY NOTE ID</span>
          <span class="text-slate-300 font-mono font-semibold">${data.delivery_note_id || '—'}</span>
        </div>
        <div>
          <span class="text-slate-500 block">DELIVERY DATE</span>
          <span class="text-slate-300 font-mono">${data.delivery_date || '—'}</span>
        </div>
      </div>
      <div class="border-t border-slate-800 pt-2">
        <span class="text-[10px] text-slate-500 block mb-1">GOODS DELIVERED</span>
        <div class="space-y-1">
          ${(data.items || []).map(item => `
            <div class="flex justify-between items-center text-[10px] bg-slate-950 p-1.5 rounded border border-slate-900">
              <span class="text-slate-300 truncate max-w-[180px]">${item.description}</span>
              <span class="text-violet-400 font-mono font-medium">${item.quantity} ${item.unit || 'units'}</span>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="border-t border-slate-800 pt-2 mt-auto text-[10px] grid grid-cols-2 gap-2 text-slate-500">
        <div>
          <span>CARRIER</span>
          <span class="block text-slate-300 truncate font-medium">${data.carrier_name || 'Not Spec.'}</span>
        </div>
        <div>
          <span>RECEIVED BY</span>
          <span class="block text-slate-300 font-bold truncate">${data.received_by || 'Not Spec.'}</span>
        </div>
      </div>
    `;
  } else if (doc.doc_type === "Contract" && data && Object.keys(data).length > 0) {
    const curr = (data.currency || "USD").toUpperCase();
    const currSym = curr === "INR" ? "₹" : curr === "EUR" ? "€" : curr === "GBP" ? "£" : "$";
    html = `
      <div class="space-y-1">
        <p class="text-[9px] text-slate-400 font-semibold">AGREEMENT TYPE</p>
        <p class="text-sm font-bold text-sky-400 leading-tight">${data.contract_type || '—'}</p>
      </div>
      <div class="border-t border-slate-800 pt-2 text-[10px]">
        <span class="text-slate-500 block mb-1">PARTIES SIGNED</span>
        <div class="space-y-1">
          ${(data.parties || []).map(p => `
            <div class="flex justify-between bg-slate-950 p-1.5 rounded border border-slate-900">
              <span class="text-slate-200 truncate font-semibold">${p.name}</span>
              <span class="text-slate-500 uppercase tracking-wider text-[8px] font-bold">${p.role}</span>
            </div>
          `).join('')}
        </div>
      </div>
      <div class="grid grid-cols-2 gap-2 text-[10px] border-t border-slate-800 pt-2">
        <div>
          <span class="text-slate-500 block">EFFECTIVE DATE</span>
          <span class="text-slate-300 font-semibold">${data.effective_date || '—'}</span>
        </div>
        <div>
          <span class="text-slate-500 block">EXPIRATION DATE</span>
          <span class="text-slate-300">${data.expiration_date || 'Ongoing'}</span>
        </div>
      </div>
      <div class="border-t border-slate-800 pt-2 mt-auto text-[10px]">
        <div class="flex justify-between items-center mb-1">
          <span class="text-slate-500">CONTRACT TOTAL VALUE</span>
          <span class="font-bold text-sky-400 font-mono">${currSym}${(data.contract_amount || 0).toLocaleString()}</span>
        </div>
      </div>
    `;
  } else {
    html = `
      <div class="flex-1 flex flex-col justify-center items-center text-center p-4">
        <div class="p-3 bg-slate-950 border border-slate-850 rounded-xl mb-3 text-slate-500">
          <i data-lucide="file-warning" class="w-8 h-8"></i>
        </div>
        <p class="text-xs font-semibold text-slate-300">Unclassified Template Layout</p>
        <p class="text-[10px] text-slate-500 mt-1 max-w-[200px]">The document contains unstructured content and failed automatic parser routing.</p>
      </div>
    `;
  }

  visualBody.innerHTML = html;
  lucide.createIcons();
}

// Generate interactive schema form
function renderExtractionForm(doc) {
  const form = document.getElementById("extraction-form");
  form.innerHTML = "";
  
  const data = doc.extracted_data;
  
  if (doc.doc_type === "Unknown" || !data || Object.keys(data).length === 0) {
    form.innerHTML = `
      <div class="bg-rose-500/5 border border-rose-500/10 rounded-xl p-4 flex items-start space-x-3 mb-6">
        <i data-lucide="x-circle" class="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5"></i>
        <div>
          <h4 class="text-xs font-bold text-rose-400">Classification Failure</h4>
          <p class="text-[11px] text-slate-400 mt-1">This document does not match any recognized schema structure. Please choose a valid target schema to structure this file manually.</p>
        </div>
      </div>
      
      <div class="space-y-3">
        <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wider">Select Schema Type</label>
        <div class="grid grid-cols-3 gap-3">
          <button type="button" onclick="initializeUnknownDocAs('Invoice')" class="py-3 bg-slate-900 border border-slate-800 hover:border-emerald-500 text-slate-300 hover:text-white rounded-lg transition font-semibold text-xs flex flex-col items-center justify-center space-y-1">
            <i data-lucide="file-text" class="w-5 h-5 text-emerald-400"></i>
            <span>Invoice</span>
          </button>
          <button type="button" onclick="initializeUnknownDocAs('Delivery Note')" class="py-3 bg-slate-900 border border-slate-800 hover:border-violet-500 text-slate-300 hover:text-white rounded-lg transition font-semibold text-xs flex flex-col items-center justify-center space-y-1">
            <i data-lucide="truck" class="w-5 h-5 text-violet-400"></i>
            <span>Delivery Note</span>
          </button>
          <button type="button" onclick="initializeUnknownDocAs('Contract')" class="py-3 bg-slate-900 border border-slate-800 hover:border-sky-500 text-slate-300 hover:text-white rounded-lg transition font-semibold text-xs flex flex-col items-center justify-center space-y-1">
            <i data-lucide="file-key" class="w-5 h-5 text-sky-400"></i>
            <span>Contract</span>
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  if (doc.doc_type === "Invoice") {
    const curr = (data.currency || "USD").toUpperCase();
    const currSym = getCurrencySymbol(curr);
    const hasCgst = data.cgst !== undefined && data.cgst !== null;
    const hasSgst = data.sgst !== undefined && data.sgst !== null;
    // Generate Invoice Form
    form.innerHTML = `
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Invoice Number</label>
          <input type="text" name="invoice_number" value="${data.invoice_number || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium shadow-sm focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Invoice Date</label>
          <input type="text" name="invoice_date" value="${data.invoice_date || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium shadow-sm focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Vendor Name</label>
          <input type="text" name="vendor_name" value="${data.vendor_name || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium shadow-sm focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Currency</label>
          <input type="text" name="currency" value="${curr}" required oninput="refreshInvoiceCurrencyDisplays()" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium shadow-sm focus:outline-none transition">
        </div>
      </div>

      <!-- Line Items Section -->
      <div class="border-t border-slate-800 pt-4">
        <div class="flex justify-between items-center mb-3">
          <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wide">Line Items</h4>
          <button type="button" onclick="addInvoiceItemRow()" class="text-xs bg-slate-900 border border-slate-700 hover:border-indigo-400 text-indigo-400 hover:text-indigo-300 px-3 py-1.5 rounded-md transition font-semibold flex items-center space-x-1 shadow-sm">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
            <span>Add Item</span>
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs min-w-[500px]" id="invoice-items-table">
            <thead>
              <tr class="text-slate-400 border-b border-slate-750 font-semibold">
                <th class="pb-2 w-[48%]">Description</th>
                <th class="pb-2 text-center w-[14%]">Qty</th>
                <th class="pb-2 text-right w-[16%]" id="th-item-price">Price (${currSym})</th>
                <th class="pb-2 text-right w-[16%]" id="th-item-amount">Amount (${currSym})</th>
                <th class="pb-2 text-center w-[6%]"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60" id="invoice-items-tbody">
              ${(data.line_items || []).map((item, idx) => `
                <tr class="item-row">
                  <td class="py-2 pr-2">
                    <input type="text" value="${item.description || ''}" required class="item-desc w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="number" step="any" value="${item.quantity || 0}" required class="item-qty w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition" oninput="calculateItemRowAmount(this)">
                  </td>
                  <td class="py-2 px-2 text-right">
                    <input type="number" step="0.01" value="${Number(item.price || 0).toFixed(2)}" required class="item-price w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-right rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition" oninput="calculateItemRowAmount(this)">
                  </td>
                  <td class="py-2 pl-2 text-right text-emerald-400 font-mono font-bold item-amount-val text-xs">
                    ${formatCurrencyAmount(item.amount || 0, curr)}
                  </td>
                  <td class="py-2 text-center">
                    <button type="button" onclick="removeInvoiceItemRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
                      <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Financial Totals -->
      <div class="border-t border-slate-800 pt-4 grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-200 tracking-wide" id="lbl-subtotal-title">Subtotal (${currSym})</label>
            <span class="text-xs font-mono text-slate-400" id="lbl-subtotal-formatted">${formatCurrencyAmount(data.subtotal || 0, curr)}</span>
          </div>
          <input type="number" step="0.01" name="subtotal" value="${Number(data.subtotal || 0).toFixed(2)}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-mono font-medium focus:outline-none transition" oninput="recalculateInvoiceSummary()">
        </div>
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-200 tracking-wide" id="lbl-tax-title">Total Tax (${currSym})</label>
            <span class="text-xs font-mono text-slate-400" id="lbl-tax-formatted">${formatCurrencyAmount(data.tax || 0, curr)}</span>
          </div>
          <input type="number" step="0.01" name="tax" value="${Number(data.tax || 0).toFixed(2)}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-mono font-medium focus:outline-none transition" oninput="recalculateInvoiceSummary()">
        </div>
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-200 tracking-wide" id="lbl-total-title">Grand Total (${currSym})</label>
            <span class="text-xs font-mono font-bold text-emerald-400" id="lbl-total-formatted">${formatCurrencyAmount(data.total || 0, curr)}</span>
          </div>
          <input type="number" step="0.01" name="total" value="${Number(data.total || 0).toFixed(2)}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-emerald-400 font-mono font-bold focus:outline-none transition" oninput="refreshInvoiceCurrencyDisplays()">
        </div>
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-200 tracking-wide" id="lbl-cgst-title">CGST (${currSym})</label>
            <span class="text-xs font-mono text-slate-400" id="lbl-cgst-formatted">${hasCgst ? formatCurrencyAmount(data.cgst, curr) : '—'}</span>
          </div>
          <input type="number" step="0.01" name="cgst" value="${hasCgst ? Number(data.cgst).toFixed(2) : ''}" placeholder="Optional" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-mono font-medium focus:outline-none transition" oninput="recalculateTaxesFromBreakdown()">
        </div>
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="text-xs font-semibold text-slate-200 tracking-wide" id="lbl-sgst-title">SGST (${currSym})</label>
            <span class="text-xs font-mono text-slate-400" id="lbl-sgst-formatted">${hasSgst ? formatCurrencyAmount(data.sgst, curr) : '—'}</span>
          </div>
          <input type="number" step="0.01" name="sgst" value="${hasSgst ? Number(data.sgst).toFixed(2) : ''}" placeholder="Optional" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-mono font-medium focus:outline-none transition" oninput="recalculateTaxesFromBreakdown()">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Payment Due Date</label>
          <input type="text" name="due_date" value="${data.due_date || ''}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
      </div>
    `;
  } else if (doc.doc_type === "Delivery Note") {
    // Generate Delivery Note Form
    form.innerHTML = `
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Delivery Note ID</label>
          <input type="text" name="delivery_note_id" value="${data.delivery_note_id || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Delivery Date</label>
          <input type="text" name="delivery_date" value="${data.delivery_date || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Sender Name</label>
          <input type="text" name="sender_name" value="${data.sender_name || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Recipient Name</label>
          <input type="text" name="recipient_name" value="${data.recipient_name || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div class="col-span-2">
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Purchase Order (PO) Number</label>
          <input type="text" name="po_number" value="${data.po_number || ''}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
      </div>

      <!-- Items Section -->
      <div class="border-t border-slate-800 pt-4">
        <div class="flex justify-between items-center mb-3">
          <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wide">Delivered Goods</h4>
          <button type="button" onclick="addDNItemRow()" class="text-xs bg-slate-900 border border-slate-700 hover:border-indigo-400 text-indigo-400 hover:text-indigo-300 px-3 py-1.5 rounded-md transition font-semibold flex items-center space-x-1 shadow-sm">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
            <span>Add Item</span>
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs min-w-[400px]" id="dn-items-table">
            <thead>
              <tr class="text-slate-400 border-b border-slate-750 font-semibold">
                <th class="pb-2 w-[60%]">Item Description</th>
                <th class="pb-2 text-center w-[18%]">Quantity</th>
                <th class="pb-2 text-center w-[16%]">Unit</th>
                <th class="pb-2 text-center w-[6%]"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60" id="dn-items-tbody">
              ${(data.items || []).map((item, idx) => `
                <tr class="dn-item-row">
                  <td class="py-2 pr-2">
                    <input type="text" value="${item.description || ''}" required class="dn-item-desc w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="number" step="any" value="${item.quantity || 0}" required class="dn-item-qty w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                  </td>
                  <td class="py-2 px-2 text-center">
                    <input type="text" value="${item.unit || 'pcs'}" required class="dn-item-unit w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                  </td>
                  <td class="py-2 text-center">
                    <button type="button" onclick="removeDNItemRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
                      <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Carrier / Signoff -->
      <div class="border-t border-slate-800 pt-4 grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Carrier Company</label>
          <input type="text" name="carrier_name" value="${data.carrier_name || ''}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Received By (Signature/Name)</label>
          <input type="text" name="received_by" value="${data.received_by || ''}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
      </div>
    `;
  } else if (doc.doc_type === "Contract") {
    const curr = (data.currency || "USD").toUpperCase();
    const currSym = getCurrencySymbol(curr);
    // Generate Contract Form
    form.innerHTML = `
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Contract ID / Ref</label>
          <input type="text" name="contract_id" value="${data.contract_id || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Signature Date</label>
          <input type="text" name="contract_date" value="${data.contract_date || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Effective Date</label>
          <input type="text" name="effective_date" value="${data.effective_date || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Expiration Date</label>
          <input type="text" name="expiration_date" value="${data.expiration_date || ''}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Agreement Value (${currSym})</label>
          <input type="number" step="any" name="contract_amount" value="${data.contract_amount || 0}" class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-sky-400 font-mono font-bold focus:outline-none transition">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-200 tracking-wide mb-1.5">Agreement Type</label>
          <input type="text" name="contract_type" value="${data.contract_type || ''}" required class="w-full bg-slate-900 border border-slate-700 hover:border-slate-500 focus:border-indigo-400 rounded-lg px-3.5 py-2.5 text-sm text-white font-medium focus:outline-none transition">
        </div>
      </div>

      <!-- Contract Parties -->
      <div class="border-t border-slate-800 pt-4">
        <div class="flex justify-between items-center mb-3">
          <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wide">Signatory Parties</h4>
          <button type="button" onclick="addContractPartyRow()" class="text-xs bg-slate-900 border border-slate-700 hover:border-indigo-400 text-indigo-400 hover:text-indigo-300 px-3 py-1.5 rounded-md transition font-semibold flex items-center space-x-1 shadow-sm">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
            <span>Add Party</span>
          </button>
        </div>
        
        <table class="w-full text-left text-xs" id="parties-table">
          <thead>
            <tr class="text-slate-400 border-b border-slate-750 font-semibold">
              <th class="pb-2 w-[58%]">Entity/Name</th>
              <th class="pb-2 w-[36%]">Role (Client, Vendor)</th>
              <th class="pb-2 text-center w-[6%]"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60" id="parties-tbody">
            ${(data.parties || []).map((party, idx) => `
              <tr class="party-row">
                <td class="py-2 pr-2">
                  <input type="text" value="${party.name || ''}" required class="party-name w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                </td>
                <td class="py-2 px-2">
                  <input type="text" value="${party.role || ''}" required class="party-role w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
                </td>
                <td class="py-2 text-center">
                  <button type="button" onclick="removeContractPartyRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                  </button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>

      <!-- Key Clauses -->
      <div class="border-t border-slate-800 pt-4">
        <div class="flex justify-between items-center mb-3">
          <h4 class="text-xs font-bold text-slate-200 uppercase tracking-wide">Key Clauses</h4>
          <button type="button" onclick="addClauseRow()" class="text-xs bg-slate-900 border border-slate-700 hover:border-indigo-400 text-indigo-400 hover:text-indigo-300 px-3 py-1.5 rounded-md transition font-semibold flex items-center space-x-1 shadow-sm">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
            <span>Add Clause</span>
          </button>
        </div>
        <div id="clauses-container" class="space-y-2">
          ${(data.key_clauses || []).map((clause, idx) => `
            <div class="flex items-start space-x-2 clause-row bg-slate-900 p-2.5 rounded-lg border border-slate-700/90 hover:border-slate-500 transition">
              <textarea required class="clause-text w-full bg-transparent text-xs text-white font-medium focus:outline-none resize-none leading-relaxed" rows="2">${clause}</textarea>
              <button type="button" onclick="removeClauseRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded flex-shrink-0 transition">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
  
  lucide.createIcons();
}

// Global functions for dynamic form rows manipulation (attached to window for onclick triggers)
window.addInvoiceItemRow = function() {
  const tbody = document.getElementById("invoice-items-tbody");
  const tr = document.createElement("tr");
  tr.className = "item-row";
  const curr = (document.getElementsByName("currency")[0] ? document.getElementsByName("currency")[0].value.trim().toUpperCase() : "USD");
  tr.innerHTML = `
    <td class="py-2 pr-2">
      <input type="text" value="" required class="item-desc w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 px-2 text-center">
      <input type="number" step="any" value="1" required class="item-qty w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition" oninput="calculateItemRowAmount(this)">
    </td>
    <td class="py-2 px-2 text-right">
      <input type="number" step="0.01" value="0.00" required class="item-price w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-right rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition" oninput="calculateItemRowAmount(this)">
    </td>
    <td class="py-2 pl-2 text-right text-emerald-400 font-mono font-bold item-amount-val text-xs">
      ${formatCurrencyAmount(0, curr)}
    </td>
    <td class="py-2 text-center">
      <button type="button" onclick="removeInvoiceItemRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
  lucide.createIcons();
};

window.removeInvoiceItemRow = function(btn) {
  btn.closest("tr").remove();
  recalculateInvoiceSummary();
};

window.calculateItemRowAmount = function(input) {
  const row = input.closest("tr");
  const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
  const price = parseFloat(row.querySelector(".item-price").value) || 0;
  const amount = qty * price;
  const curr = (document.getElementsByName("currency")[0] ? document.getElementsByName("currency")[0].value.trim().toUpperCase() : "USD");
  row.querySelector(".item-amount-val").innerText = formatCurrencyAmount(amount, curr);
  recalculateInvoiceSummary();
};

window.recalculateTaxesFromBreakdown = function() {
  const cgstInput = document.getElementsByName("cgst")[0];
  const sgstInput = document.getElementsByName("sgst")[0];
  const taxInput = document.getElementsByName("tax")[0];
  if (cgstInput && sgstInput && (cgstInput.value !== "" || sgstInput.value !== "")) {
    const cgst = parseFloat(cgstInput.value) || 0;
    const sgst = parseFloat(sgstInput.value) || 0;
    if (taxInput) taxInput.value = (cgst + sgst).toFixed(2);
  }
  recalculateInvoiceSummary();
};

window.recalculateInvoiceSummary = function() {
  const rows = document.querySelectorAll("#invoice-items-tbody .item-row");
  let subtotal = 0;
  
  rows.forEach(row => {
    const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
    const price = parseFloat(row.querySelector(".item-price").value) || 0;
    subtotal += qty * price;
  });
  
  const taxRateInput = document.getElementsByName("tax")[0];
  const subtotalInput = document.getElementsByName("subtotal")[0];
  const totalInput = document.getElementsByName("total")[0];

  if (subtotalInput) subtotalInput.value = subtotal.toFixed(2);
  
  const tax = parseFloat(taxRateInput ? taxRateInput.value : 0) || 0;
  if (totalInput) totalInput.value = (subtotal + tax).toFixed(2);
  refreshInvoiceCurrencyDisplays();
};

window.refreshInvoiceCurrencyDisplays = function() {
  const currInput = document.getElementsByName("currency")[0];
  const curr = currInput ? currInput.value.trim().toUpperCase() : "USD";
  const sym = getCurrencySymbol(curr);

  const thPrice = document.getElementById("th-item-price");
  const thAmount = document.getElementById("th-item-amount");
  if (thPrice) thPrice.innerText = `Price (${sym})`;
  if (thAmount) thAmount.innerText = `Amount (${sym})`;

  const titles = [
    ["lbl-subtotal-title", "Subtotal"],
    ["lbl-tax-title", "Total Tax"],
    ["lbl-total-title", "Grand Total"],
    ["lbl-cgst-title", "CGST"],
    ["lbl-sgst-title", "SGST"]
  ];
  titles.forEach(([id, label]) => {
    const el = document.getElementById(id);
    if (el) el.innerText = `${label} (${sym})`;
  });

  document.querySelectorAll("#invoice-items-tbody .item-row").forEach(row => {
    const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
    const price = parseFloat(row.querySelector(".item-price").value) || 0;
    const amtEl = row.querySelector(".item-amount-val");
    if (amtEl) amtEl.innerText = formatCurrencyAmount(qty * price, curr);
  });

  const subVal = parseFloat(document.getElementsByName("subtotal")[0]?.value) || 0;
  const taxVal = parseFloat(document.getElementsByName("tax")[0]?.value) || 0;
  const totVal = parseFloat(document.getElementsByName("total")[0]?.value) || 0;
  const cgstRaw = document.getElementsByName("cgst")[0]?.value;
  const sgstRaw = document.getElementsByName("sgst")[0]?.value;

  const subFmt = document.getElementById("lbl-subtotal-formatted");
  const taxFmt = document.getElementById("lbl-tax-formatted");
  const totFmt = document.getElementById("lbl-total-formatted");
  const cgstFmt = document.getElementById("lbl-cgst-formatted");
  const sgstFmt = document.getElementById("lbl-sgst-formatted");

  if (subFmt) subFmt.innerText = formatCurrencyAmount(subVal, curr);
  if (taxFmt) taxFmt.innerText = formatCurrencyAmount(taxVal, curr);
  if (totFmt) totFmt.innerText = formatCurrencyAmount(totVal, curr);
  if (cgstFmt) cgstFmt.innerText = (cgstRaw !== undefined && cgstRaw !== "") ? formatCurrencyAmount(parseFloat(cgstRaw) || 0, curr) : "—";
  if (sgstFmt) sgstFmt.innerText = (sgstRaw !== undefined && sgstRaw !== "") ? formatCurrencyAmount(parseFloat(sgstRaw) || 0, curr) : "—";
};

// Delivery Note Row functions
window.addDNItemRow = function() {
  const tbody = document.getElementById("dn-items-tbody");
  const tr = document.createElement("tr");
  tr.className = "dn-item-row";
  tr.innerHTML = `
    <td class="py-2 pr-2">
      <input type="text" value="" required class="dn-item-desc w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 px-2 text-center">
      <input type="number" step="any" value="1" required class="dn-item-qty w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 px-2 text-center">
      <input type="text" value="pcs" required class="dn-item-unit w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 text-center rounded-md px-2 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 text-center">
      <button type="button" onclick="removeDNItemRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
  lucide.createIcons();
};

window.removeDNItemRow = function(btn) {
  btn.closest("tr").remove();
};

// Contract Row functions
window.addContractPartyRow = function() {
  const tbody = document.getElementById("parties-tbody");
  const tr = document.createElement("tr");
  tr.className = "party-row";
  tr.innerHTML = `
    <td class="py-2 pr-2">
      <input type="text" value="" required class="party-name w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 px-2">
      <input type="text" value="" required class="party-role w-full bg-slate-900 border border-slate-700/90 hover:border-slate-500 focus:border-indigo-400 rounded-md px-2.5 py-1.5 text-xs text-white font-medium focus:outline-none transition">
    </td>
    <td class="py-2 text-center">
      <button type="button" onclick="removeContractPartyRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded transition">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
  lucide.createIcons();
};

window.removeContractPartyRow = function(btn) {
  btn.closest("tr").remove();
};

window.addClauseRow = function() {
  const container = document.getElementById("clauses-container");
  const div = document.createElement("div");
  div.className = "flex items-start space-x-2 clause-row bg-slate-900 p-2.5 rounded-lg border border-slate-700/90 hover:border-slate-500 transition";
  div.innerHTML = `
    <textarea required class="clause-text w-full bg-transparent text-xs text-white font-medium focus:outline-none resize-none leading-relaxed" rows="2" placeholder="Enter clause text..."></textarea>
    <button type="button" onclick="removeClauseRow(this)" class="text-rose-400 hover:text-rose-300 p-1 hover:bg-rose-500/10 rounded flex-shrink-0 transition">
      <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
    </button>
  `;
  container.appendChild(div);
  lucide.createIcons();
};

window.removeClauseRow = function(btn) {
  btn.closest(".clause-row").remove();
};

// If a document fails classification, initialize empty structures for human to fill
window.initializeUnknownDocAs = function(targetType) {
  const doc = documentsList.find(d => d.id === activeDocId);
  if (!doc) return;
  
  doc.doc_type = targetType;
  
  if (targetType === "Invoice") {
    doc.extracted_data = {
      invoice_number: "",
      invoice_date: new Date().toISOString().split('T')[0],
      vendor_name: "",
      currency: "INR",
      line_items: [{description: "", quantity: 1.0, price: 0.0, amount: 0.0}],
      subtotal: 0.0,
      tax: 0.0,
      total: 0.0,
      due_date: ""
    };
  } else if (targetType === "Delivery Note") {
    doc.extracted_data = {
      delivery_note_id: "",
      delivery_date: new Date().toISOString().split('T')[0],
      recipient_name: "",
      sender_name: "",
      po_number: "",
      items: [{description: "", quantity: 1.0, unit: "pcs"}],
      carrier_name: "",
      received_by: ""
    };
  } else if (targetType === "Contract") {
    doc.extracted_data = {
      contract_id: "",
      contract_date: new Date().toISOString().split('T')[0],
      parties: [{name: "", role: "Client"}, {name: "", role: "Vendor"}],
      effective_date: new Date().toISOString().split('T')[0],
      expiration_date: "",
      contract_amount: 0.0,
      currency: "USD",
      contract_type: "Agreement",
      key_clauses: []
    };
  }

  // Reload views
  selectDocument(doc.id);
  showToast("Schema Mapping Initialized", `Switched template to ${targetType}.`, "info");
};

// Handle Drag-and-Drop and preloaded uploads
async function uploadFile(file) {
  const scanningOverlay = document.getElementById("scanning-overlay");
  const scanningFilename = document.getElementById("scanning-filename");
  
  scanningFilename.innerText = file.name;
  scanningOverlay.classList.remove("hidden");
  scanningOverlay.classList.remove("opacity-0");

  const formData = new FormData();
  formData.append("file", file);

  const apiKey = localStorage.getItem("gemini_api_key");
  if (apiKey) {
    formData.append("api_key", apiKey);
  }

  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      body: formData
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Server extraction failed");
    }

    const docResult = await response.json();
    
    // Add to list and fetch updated items
    await fetchDocuments();
    
    // Select newly uploaded document
    selectDocument(docResult.id);
    
    showToast("Extraction Completed", `${file.name} parsed successfully.`, "success");
  } catch (error) {
    showToast("Processing Failed", error.message, "error");
  } finally {
    scanningOverlay.classList.add("opacity-0");
    setTimeout(() => scanningOverlay.classList.add("hidden"), 300);
  }
}

// Quick Sample upload trigger
window.uploadSample = function(filename) {
  const blob = new Blob(["mock-binary-payload"], { type: "application/octet-stream" });
  const file = new File([blob], filename, { type: "application/octet-stream" });
  uploadFile(file);
};

// Approve verified data
async function submitApproval() {
  if (!activeDocId) return;

  const doc = documentsList.find(d => d.id === activeDocId);
  if (!doc) return;

  const verifiedPayload = {};
  
  if (doc.doc_type === "Invoice") {
    const totalInput = document.getElementsByName("total")[0];
    const subtotalInput = document.getElementsByName("subtotal")[0];
    const taxInput = document.getElementsByName("tax")[0];
    
    verifiedPayload.invoice_number = document.getElementsByName("invoice_number")[0].value;
    verifiedPayload.invoice_date = document.getElementsByName("invoice_date")[0].value;
    verifiedPayload.vendor_name = document.getElementsByName("vendor_name")[0].value;
    const currInput = document.getElementsByName("currency")[0];
    const cgstInput = document.getElementsByName("cgst")[0];
    const sgstInput = document.getElementsByName("sgst")[0];
    verifiedPayload.currency = currInput ? currInput.value : (doc.extracted_data.currency || "USD");
    verifiedPayload.subtotal = parseFloat(subtotalInput ? subtotalInput.value : 0) || 0;
    verifiedPayload.tax = parseFloat(taxInput ? taxInput.value : 0) || 0;
    verifiedPayload.cgst = (cgstInput && cgstInput.value !== "") ? parseFloat(cgstInput.value) : null;
    verifiedPayload.sgst = (sgstInput && sgstInput.value !== "") ? parseFloat(sgstInput.value) : null;
    verifiedPayload.total = parseFloat(totalInput ? totalInput.value : 0) || 0;
    verifiedPayload.due_date = document.getElementsByName("due_date")[0].value;
    
    // Collect Line Items
    verifiedPayload.line_items = [];
    document.querySelectorAll("#invoice-items-tbody .item-row").forEach(row => {
      const desc = row.querySelector(".item-desc").value;
      const qty = parseFloat(row.querySelector(".item-qty").value) || 0;
      const price = parseFloat(row.querySelector(".item-price").value) || 0;
      verifiedPayload.line_items.push({
        description: desc,
        quantity: qty,
        price: price,
        amount: qty * price
      });
    });
  } else if (doc.doc_type === "Delivery Note") {
    verifiedPayload.delivery_note_id = document.getElementsByName("delivery_note_id")[0].value;
    verifiedPayload.delivery_date = document.getElementsByName("delivery_date")[0].value;
    verifiedPayload.sender_name = document.getElementsByName("sender_name")[0].value;
    verifiedPayload.recipient_name = document.getElementsByName("recipient_name")[0].value;
    verifiedPayload.po_number = document.getElementsByName("po_number")[0].value;
    verifiedPayload.carrier_name = document.getElementsByName("carrier_name")[0].value;
    verifiedPayload.received_by = document.getElementsByName("received_by")[0].value;
    
    // Collect Items
    verifiedPayload.items = [];
    document.querySelectorAll("#dn-items-tbody .dn-item-row").forEach(row => {
      verifiedPayload.items.push({
        description: row.querySelector(".dn-item-desc").value,
        quantity: parseFloat(row.querySelector(".dn-item-qty").value) || 0,
        unit: row.querySelector(".dn-item-unit").value
      });
    });
  } else if (doc.doc_type === "Contract") {
    verifiedPayload.contract_id = document.getElementsByName("contract_id")[0].value;
    verifiedPayload.contract_date = document.getElementsByName("contract_date")[0].value;
    verifiedPayload.effective_date = document.getElementsByName("effective_date")[0].value;
    verifiedPayload.expiration_date = document.getElementsByName("expiration_date")[0].value;
    verifiedPayload.contract_amount = parseFloat(document.getElementsByName("contract_amount")[0].value) || 0;
    verifiedPayload.contract_type = document.getElementsByName("contract_type")[0].value;
    
    // Collect Parties
    verifiedPayload.parties = [];
    document.querySelectorAll("#parties-tbody .party-row").forEach(row => {
      verifiedPayload.parties.push({
        name: row.querySelector(".party-name").value,
        role: row.querySelector(".party-role").value
      });
    });
    
    // Collect Clauses
    verifiedPayload.key_clauses = [];
    document.querySelectorAll("#clauses-container .clause-row").forEach(row => {
      verifiedPayload.key_clauses.push(row.querySelector(".clause-text").value);
    });
  }

  // Send update to Backend API
  try {
    const response = await fetch(`/api/documents/${activeDocId}/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(verifiedPayload)
    });
    
    if (!response.ok) throw new Error("Failed to verify document");

    const updatedDoc = await response.json();
    
    // Update local state list
    const index = documentsList.findIndex(d => d.id === activeDocId);
    if (index !== -1) {
      documentsList[index] = updatedDoc;
    }

    // Refresh views & stats
    renderQueue();
    selectDocument(activeDocId);
    updateStats();

    showToast("Document Verified", "Extraction schema approved and saved.", "success");
  } catch (error) {
    showToast("Verification Error", error.message, "error");
  }
}

// Update Stats Dashboard & Draw Breakdown Chart
async function updateStats() {
  try {
    const response = await fetch("/api/stats");
    const stats = await response.json();

    document.getElementById("stat-total").innerText = stats.total_documents;
    document.getElementById("stat-review").innerText = stats.needs_review;
    document.getElementById("stat-verified").innerText = stats.verified;
    
    const confidencePct = Math.round(stats.average_confidence * 100);
    document.getElementById("stat-confidence").innerText = `${confidencePct}%`;

    // Percentage of jobs requiring review
    const reviewPct = stats.total_documents > 0 ? Math.round((stats.needs_review / stats.total_documents) * 100) : 0;
    const reviewBadge = document.getElementById("stat-review-badge");
    reviewBadge.innerText = `${reviewPct}% of pool`;
    
    if (reviewPct > 50) {
      reviewBadge.className = "text-xs px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 font-semibold border border-rose-500/20";
    } else if (reviewPct > 0) {
      reviewBadge.className = "text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/20";
    } else {
      reviewBadge.className = "text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20";
    }

  } catch (error) {
    console.error("Failed to update dashboard stats: ", error);
  }
}

// Toast Notifications Helper
function showToast(title, message, type = "success") {
  const toast = document.getElementById("toast");
  const iconContainer = document.getElementById("toast-icon-container");
  const icon = document.getElementById("toast-icon");
  const titleEl = document.getElementById("toast-title");
  const msgEl = document.getElementById("toast-message");

  titleEl.innerText = title;
  msgEl.innerText = message;

  if (type === "success") {
    iconContainer.className = "p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
    icon.setAttribute("data-lucide", "check");
  } else if (type === "error") {
    iconContainer.className = "p-1.5 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30";
    icon.setAttribute("data-lucide", "alert-circle");
  } else {
    iconContainer.className = "p-1.5 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30";
    icon.setAttribute("data-lucide", "info");
  }

  lucide.createIcons();

  // Slide up toast
  toast.classList.remove("translate-y-24", "opacity-0");
  toast.classList.add("translate-y-0", "opacity-100");

  // Hide toast after 4s
  setTimeout(() => {
    toast.classList.remove("translate-y-0", "opacity-100");
    toast.classList.add("translate-y-24", "opacity-0");
  }, 4000);
}
