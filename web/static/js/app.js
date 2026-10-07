// Generador de Etiquetas SPA / PWA - app.js

let itemsState = [];
let loadedFileName = "etiquetas";
let debounceTimer = null;
let deferredPrompt = null;

// Inicialización de iconos y eventos
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  setupPWA();
  setupTabs();
  setupDragAndDrop();
  setupManualInput();
  setupTableEvents();
  setupExportEvents();
});

// Configuración PWA (Service Worker e Instalación)
function setupPWA() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then((reg) => console.log('[PWA] Service Worker registrado:', reg.scope))
        .catch((err) => console.warn('[PWA] Error registrando Service Worker:', err));
    });
  }

  const installBtn = document.getElementById('btn-pwa-install');
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) {
      installBtn.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    }
  });

  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        showToast('¡Instalando aplicación!', 'success');
      }
      deferredPrompt = null;
      installBtn.classList.add('hidden');
    });
  }

  window.addEventListener('appinstalled', () => {
    if (installBtn) installBtn.classList.add('hidden');
    showToast('Aplicación instalada exitosamente', 'success');
  });
}

// Toast Notificaciones
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast-enter flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white ${
    type === "error"
      ? "bg-rose-600"
      : type === "success"
      ? "bg-emerald-600"
      : "bg-slate-800"
  }`;

  const iconName = type === "error" ? "alert-circle" : type === "success" ? "check-circle" : "info";
  toast.innerHTML = `<i data-lucide="${iconName}" class="w-4 h-4"></i><span>${message}</span>`;
  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// 1. Gestión de Tabs (Excel vs Manual)
function setupTabs() {
  const tabExcelBtn = document.getElementById("tab-excel-btn");
  const tabManualBtn = document.getElementById("tab-manual-btn");
  const tabExcelContent = document.getElementById("tab-excel-content");
  const tabManualContent = document.getElementById("tab-manual-content");

  tabExcelBtn.addEventListener("click", () => {
    tabExcelBtn.classList.add("active", "border-indigo-600", "text-indigo-600");
    tabExcelBtn.classList.remove("border-transparent", "text-slate-500");
    tabManualBtn.classList.remove("active", "border-indigo-600", "text-indigo-600");
    tabManualBtn.classList.add("border-transparent", "text-slate-500");

    tabExcelContent.classList.remove("hidden");
    tabManualContent.classList.add("hidden");
  });

  tabManualBtn.addEventListener("click", () => {
    tabManualBtn.classList.add("active", "border-indigo-600", "text-indigo-600");
    tabManualBtn.classList.remove("border-transparent", "text-slate-500");
    tabExcelBtn.classList.remove("active", "border-indigo-600", "text-indigo-600");
    tabExcelBtn.classList.add("border-transparent", "text-slate-500");

    tabManualContent.classList.remove("hidden");
    tabExcelContent.classList.add("hidden");
  });
}

// 2. Drag & Drop y Carga de Archivo Excel
function setupDragAndDrop() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("excel-file-input");
  const fileBadge = document.getElementById("file-info-badge");
  const btnClearExcel = document.getElementById("btn-clear-excel");

  dropZone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, e => {
      e.preventDefault();
      dropZone.classList.add("border-indigo-500", "bg-indigo-50/50");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, e => {
      e.preventDefault();
      dropZone.classList.remove("border-indigo-500", "bg-indigo-50/50");
    });
  });

  dropZone.addEventListener("drop", e => {
    if (e.dataTransfer.files.length) {
      handleExcelFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", e => {
    if (e.target.files.length) {
      handleExcelFile(e.target.files[0]);
    }
  });

  btnClearExcel.addEventListener("click", () => {
    fileInput.value = "";
    fileBadge.classList.add("hidden");
    dropZone.classList.remove("hidden");
    loadedFileName = "etiquetas";
  });
}

async function handleExcelFile(file) {
  if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
    showToast("Por favor suba un archivo .xlsx o .xls", "error");
    return;
  }

  showToast("Procesando archivo Excel...", "info");
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload-excel", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error al procesar el Excel");
    }

    const data = await res.json();
    loadedFileName = data.filename || "etiquetas";

    const newItems = data.items.map((it, idx) => ({
      id: Date.now() + "_" + idx,
      item: it.item,
      description: it.description,
      qty: it.qty,
      selected: it.qty > 0
    }));

    itemsState = newItems;
    renderTable();

    document.getElementById("drop-zone").classList.add("hidden");
    const fileBadge = document.getElementById("file-info-badge");
    fileBadge.classList.remove("hidden");
    document.getElementById("file-name-label").textContent = file.name;
    document.getElementById("file-items-label").textContent = `${data.total_items} ítems encontrados`;

    if (newItems.length > 0) {
      updatePreview(newItems[0].item, newItems[0].description);
    }
    showToast(`Se cargaron ${data.total_items} ítems exitosamente`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// 3. Carga Manual de Códigos
function setupManualInput() {
  const codeIn = document.getElementById("manual-code");
  const descIn = document.getElementById("manual-desc");
  const qtyIn = document.getElementById("manual-qty");
  const btnAdd = document.getElementById("btn-add-manual");

  function addItem() {
    const code = codeIn.value.trim().toUpperCase();
    const desc = descIn.value.trim().toUpperCase();
    const qty = parseInt(qtyIn.value) || 1;

    if (!code) {
      showToast("Ingrese el código del ítem", "error");
      codeIn.focus();
      return;
    }

    itemsState.push({
      id: Date.now().toString(),
      item: code,
      description: desc,
      qty: qty,
      selected: true
    });

    renderTable();
    updatePreview(code, desc);

    codeIn.value = "";
    descIn.value = "";
    qtyIn.value = "1";
    codeIn.focus();
    showToast(`Ítem ${code} agregado`, "success");
  }

  btnAdd.addEventListener("click", addItem);
  [codeIn, descIn, qtyIn].forEach(inp => {
    inp.addEventListener("keypress", e => {
      if (e.key === "Enter") addItem();
    });
  });
}

// 4. Renderizado y Eventos de la Tabla
function setupTableEvents() {
  document.getElementById("search-input").addEventListener("input", filterTable);

  document.getElementById("btn-select-all").addEventListener("click", () => {
    itemsState.forEach(i => (i.selected = true));
    renderTable();
  });

  document.getElementById("btn-deselect-all").addEventListener("click", () => {
    itemsState.forEach(i => (i.selected = false));
    renderTable();
  });

  document.getElementById("th-checkbox").addEventListener("change", e => {
    itemsState.forEach(i => (i.selected = e.target.checked));
    renderTable();
  });

  document.getElementById("btn-clear-table").addEventListener("click", () => {
    if (confirm("¿Desea vaciar todos los ítems de la lista?")) {
      itemsState = [];
      renderTable();
      showToast("Lista vaciada", "info");
    }
  });
}

function renderTable() {
  const tbody = document.getElementById("items-tbody");
  tbody.innerHTML = "";

  if (itemsState.length === 0) {
    tbody.innerHTML = `
      <tr class="text-center py-12">
        <td colspan="5" class="py-12 text-slate-400">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-slate-300"></i>
          No hay ítems cargados. Importa un archivo Excel o usa la carga manual.
        </td>
      </tr>`;
    if (window.lucide) lucide.createIcons();
    updateTotals();
    return;
  }

  const query = document.getElementById("search-input").value.trim().toLowerCase();

  itemsState.forEach(item => {
    const isVisible = !query || item.item.toLowerCase().includes(query) || item.description.toLowerCase().includes(query);
    if (!isVisible) return;

    const tr = document.createElement("tr");
    tr.className = `row-hover border-b border-slate-100 transition-colors ${item.selected ? "row-selected" : "opacity-60"}`;
    tr.dataset.id = item.id;

    tr.innerHTML = `
      <td class="py-2.5 px-3 text-center">
        <input type="checkbox" ${item.selected ? "checked" : ""} class="item-checkbox rounded text-indigo-600 focus:ring-indigo-500">
      </td>
      <td class="py-2.5 px-4 font-mono font-semibold text-slate-900 cursor-pointer flex items-center gap-1.5 preview-trigger">
        <span class="bg-slate-100 text-slate-800 px-2 py-0.5 rounded border border-slate-200 text-xs">${item.item}</span>
      </td>
      <td class="py-2.5 px-4 text-slate-700">
        <input type="text" value="${item.description}" class="item-desc-input w-full bg-transparent hover:bg-white focus:bg-white border border-transparent hover:border-slate-300 focus:border-indigo-500 rounded px-2 py-1 text-xs outline-none">
      </td>
      <td class="py-2.5 px-4 text-center">
        <div class="flex items-center justify-center gap-1">
          <button class="btn-qty-minus text-slate-400 hover:text-slate-700 w-5 h-5 rounded hover:bg-slate-200 flex items-center justify-center font-bold text-xs">-</button>
          <input type="number" min="0" value="${item.qty}" class="item-qty-input w-12 text-center text-xs font-semibold py-1 border border-slate-200 rounded focus:ring-1 focus:ring-indigo-500 outline-none">
          <button class="btn-qty-plus text-slate-400 hover:text-slate-700 w-5 h-5 rounded hover:bg-slate-200 flex items-center justify-center font-bold text-xs">+</button>
        </div>
      </td>
      <td class="py-2.5 px-3 text-center">
        <button class="btn-delete text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-rose-50 transition-colors" title="Eliminar">
          <i data-lucide="trash-2" class="w-4 h-4"></i>
        </button>
      </td>
    `;

    const chk = tr.querySelector(".item-checkbox");
    chk.addEventListener("change", e => {
      item.selected = e.target.checked;
      tr.className = `row-hover border-b border-slate-100 transition-colors ${item.selected ? "row-selected" : "opacity-60"}`;
      updateTotals();
    });

    tr.querySelector(".preview-trigger").addEventListener("click", () => {
      updatePreview(item.item, item.description);
    });

    tr.addEventListener("mouseenter", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        updatePreview(item.item, item.description);
      }, 150);
    });

    const descInput = tr.querySelector(".item-desc-input");
    descInput.addEventListener("change", e => {
      item.description = e.target.value.trim().toUpperCase();
      updatePreview(item.item, item.description);
    });

    const qtyInput = tr.querySelector(".item-qty-input");
    qtyInput.addEventListener("change", e => {
      const q = parseInt(e.target.value) || 0;
      item.qty = Math.max(0, q);
      qtyInput.value = item.qty;
      updateTotals();
    });

    tr.querySelector(".btn-qty-minus").addEventListener("click", () => {
      item.qty = Math.max(0, item.qty - 1);
      qtyInput.value = item.qty;
      updateTotals();
    });

    tr.querySelector(".btn-qty-plus").addEventListener("click", () => {
      item.qty += 1;
      qtyInput.value = item.qty;
      updateTotals();
    });

    tr.querySelector(".btn-delete").addEventListener("click", () => {
      itemsState = itemsState.filter(i => i.id !== item.id);
      renderTable();
    });

    tbody.appendChild(tr);
  });

  if (window.lucide) lucide.createIcons();
  updateTotals();
}

function filterTable() {
  renderTable();
}

function updateTotals() {
  const total = itemsState.length;
  const selected = itemsState.filter(i => i.selected && i.qty > 0).length;
  const labelsCount = itemsState
    .filter(i => i.selected)
    .reduce((sum, i) => sum + (parseInt(i.qty) || 0), 0);

  document.getElementById("lbl-total-items").textContent = total;
  document.getElementById("lbl-selected-items").textContent = selected;
  document.getElementById("lbl-total-labels").textContent = labelsCount;
}

// 5. Previsualizador en Vivo
function updatePreview(item, description) {
  const img = document.getElementById("preview-image");
  const loader = document.getElementById("preview-loading");

  loader.classList.remove("hidden");
  const url = `/api/preview-label?item=${encodeURIComponent(item)}&description=${encodeURIComponent(description)}`;

  const tempImg = new Image();
  tempImg.onload = () => {
    img.src = url;
    loader.classList.add("hidden");
  };
  tempImg.onerror = () => {
    loader.classList.add("hidden");
  };
  tempImg.src = url;
}

// 6. Generación de PDF, Impresión y Descarga ZIP
function setupExportEvents() {
  const btnPrintDirect = document.getElementById("btn-print-direct");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const btnDownloadZip = document.getElementById("btn-download-zip");
  const iframe = document.getElementById("print-iframe");

  function getExportPayload() {
    const selected = itemsState.filter(i => i.selected && i.qty > 0);
    if (selected.length === 0) {
      showToast("Selecciona al menos un ítem con cantidad mayor a 0", "error");
      return null;
    }
    return {
      items: selected.map(i => ({
        item: i.item,
        description: i.description,
        qty: i.qty
      })),
      filename: loadedFileName || "etiquetas",
      width_mm: 60.0,
      height_mm: 30.0
    };
  }

  btnPrintDirect.addEventListener("click", async () => {
    const payload = getExportPayload();
    if (!payload) return;

    showToast("Generando documento para imprimir...", "info");
    btnPrintDirect.disabled = true;

    try {
      const res = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Error al generar PDF");

      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);

      iframe.src = blobUrl;
      iframe.onload = () => {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
        btnPrintDirect.disabled = false;
        showToast("Listo para imprimir", "success");
      };
    } catch (err) {
      showToast(err.message, "error");
      btnPrintDirect.disabled = false;
    }
  });

  btnDownloadPdf.addEventListener("click", async () => {
    const payload = getExportPayload();
    if (!payload) return;

    showToast("Descargando PDF...", "info");
    btnDownloadPdf.disabled = true;

    try {
      const res = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Error al generar el PDF");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${payload.filename || "etiquetas"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      showToast("PDF descargado con éxito", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btnDownloadPdf.disabled = false;
    }
  });

  btnDownloadZip.addEventListener("click", async () => {
    const payload = getExportPayload();
    if (!payload) return;

    showToast("Comprimiendo imágenes en .ZIP...", "info");
    btnDownloadZip.disabled = true;

    try {
      const res = await fetch("/api/download-zip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Error al generar ZIP");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${payload.filename || "etiquetas"}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      showToast("Archivo ZIP descargado", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btnDownloadZip.disabled = false;
    }
  });
}
