// Generador de Etiquetas SPA / PWA - app.js

let itemsState = [];
let loadedFileName = "etiquetas";
let debounceTimer = null;
let catalogDebounceTimer = null;
let deferredPrompt = null;
let selectedLabelSize = "60x30";
let lastPreviewItem = "012345";
let lastPreviewDesc = "EJEMPLO DE ETIQUETA";

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  setupPWA();
  setupTabs();
  setupSizeSelector();
  setupCatalogSearch();
  setupAddModal();
  setupDragAndDrop();
  setupManualInput();
  setupTableEvents();
  setupExportEvents();
  loadCatalogStats();
});

// Configuración PWA
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

// 1. Gestión de Tabs (Catálogo vs Excel vs Manual)
function setupTabs() {
  const tabs = [
    { btn: "tab-catalog-btn", content: "tab-catalog-content" },
    { btn: "tab-excel-btn", content: "tab-excel-content" },
    { btn: "tab-manual-btn", content: "tab-manual-content" }
  ];

  tabs.forEach(t => {
    const btnElem = document.getElementById(t.btn);
    btnElem.addEventListener("click", () => {
      tabs.forEach(other => {
        const b = document.getElementById(other.btn);
        const c = document.getElementById(other.content);
        if (other.btn === t.btn) {
          b.classList.add("active", "border-indigo-600", "text-indigo-600");
          b.classList.remove("border-transparent", "text-slate-500");
          c.classList.remove("hidden");
        } else {
          b.classList.remove("active", "border-indigo-600", "text-indigo-600");
          b.classList.add("border-transparent", "text-slate-500");
          c.classList.add("hidden");
        }
      });
    });
  });
}

// 1.1 Selector de Tamaño de Etiquetas (60x30 mm vs 60x95 mm)
function setupSizeSelector() {
  const btn30 = document.getElementById("btn-size-60x30");
  const btn95 = document.getElementById("btn-size-60x95") || document.getElementById("btn-size-60x90");

  if (!btn30 || !btn95) return;

  btn30.addEventListener("click", () => setLabelSize("60x30"));
  btn95.addEventListener("click", () => setLabelSize("60x95"));
}

function setLabelSize(size) {
  selectedLabelSize = size;
  const btn30 = document.getElementById("btn-size-60x30");
  const btn95 = document.getElementById("btn-size-60x95") || document.getElementById("btn-size-60x90");
  const badge = document.getElementById("badge-preview-size");
  const container = document.getElementById("preview-container");
  const pdfBtnLabel = document.getElementById("lbl-btn-pdf");

  if (size === "60x95" || size === "60x90") {
    // 60x95 activo
    if (btn30) {
      btn30.classList.remove("active", "border-indigo-600", "bg-indigo-50/70", "text-indigo-900");
      btn30.classList.add("border-slate-200", "bg-slate-50", "text-slate-700");
      const check30 = btn30.querySelector(".size-check-box");
      if (check30) {
        check30.className = "size-check-box w-4 h-4 rounded-full border border-slate-300 bg-white text-transparent flex items-center justify-center shrink-0";
      }
    }

    if (btn95) {
      btn95.classList.add("active", "border-indigo-600", "bg-indigo-50/70", "text-indigo-900");
      btn95.classList.remove("border-slate-200", "bg-slate-50", "text-slate-700");
      const check95 = btn95.querySelector(".size-check-box");
      if (check95) {
        check95.className = "size-check-box w-4 h-4 rounded-full border border-indigo-600 bg-indigo-600 text-white flex items-center justify-center shrink-0";
      }
    }

    if (badge) {
      badge.textContent = "62 x 100 mm";
      badge.className = "text-[11px] font-mono bg-purple-50 text-purple-700 font-bold px-2 py-0.5 rounded border border-purple-200";
    }

    if (container) {
      container.classList.remove("preview-box-60x30");
      container.classList.remove("preview-box-60x90");
      container.classList.add("preview-box-60x95");
    }

    if (pdfBtnLabel) pdfBtnLabel.textContent = "Descargar PDF (62x100 mm)";
  } else {
    // 60x30 activo
    if (btn95) {
      btn95.classList.remove("active", "border-indigo-600", "bg-indigo-50/70", "text-indigo-900");
      btn95.classList.add("border-slate-200", "bg-slate-50", "text-slate-700");
      const check95 = btn95.querySelector(".size-check-box");
      if (check95) {
        check95.className = "size-check-box w-4 h-4 rounded-full border border-slate-300 bg-white text-transparent flex items-center justify-center shrink-0";
      }
    }

    if (btn30) {
      btn30.classList.add("active", "border-indigo-600", "bg-indigo-50/70", "text-indigo-900");
      btn30.classList.remove("border-slate-200", "bg-slate-50", "text-slate-700");
      const check30 = btn30.querySelector(".size-check-box");
      if (check30) {
        check30.className = "size-check-box w-4 h-4 rounded-full border border-indigo-600 bg-indigo-600 text-white flex items-center justify-center shrink-0";
      }
    }

    if (badge) {
      badge.textContent = "62 x 29 mm";
      badge.className = "text-[11px] font-mono bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded border border-indigo-200";
    }

    if (container) {
      container.classList.remove("preview-box-60x95");
      container.classList.remove("preview-box-60x90");
      container.classList.add("preview-box-60x30");
    }

    if (pdfBtnLabel) pdfBtnLabel.textContent = "Descargar PDF (62x29 mm)";
  }

  if (window.lucide) lucide.createIcons();
  updatePreview(lastPreviewItem, lastPreviewDesc);
}

// 2. Base de Datos / Catálogo (DATOS_DEPO.xlsx)
async function loadCatalogStats() {
  try {
    const res = await fetch("/api/catalog/stats");
    if (res.ok) {
      const data = await res.json();
      const badge = document.getElementById("badge-catalog-count");
      if (badge) {
        badge.textContent = `${data.total_items.toLocaleString()} ítems`;
      }
    }
  } catch (err) {
    console.warn("No se pudo cargar estadísticas de catálogo:", err);
  }
}

function setupCatalogSearch() {
  const input = document.getElementById("catalog-search-input");
  const resultsBox = document.getElementById("catalog-results-box");
  const resultsList = document.getElementById("catalog-results-list");
  const resultsCount = document.getElementById("catalog-results-count");

  input.addEventListener("input", () => {
    clearTimeout(catalogDebounceTimer);
    const query = input.value.trim().toUpperCase();

    if (query.length < 2) {
      resultsBox.classList.add("hidden");
      resultsList.innerHTML = "";
      return;
    }

    catalogDebounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/catalog/search?q=${encodeURIComponent(query)}&limit=30`);
        if (!res.ok) return;
        const items = await res.json();

        resultsList.innerHTML = "";
        resultsCount.textContent = `${items.length} resultado${items.length === 1 ? '' : 's'}`;

        if (items.length === 0) {
          resultsList.innerHTML = `
            <div class="p-4 text-center text-xs text-slate-500">
              No se encontraron artículos con el término "${query}". Puedes agregarlo usando el botón verde.
            </div>`;
          resultsBox.classList.remove("hidden");
          return;
        }

        items.forEach(it => {
          const row = document.createElement("div");
          row.className = "p-3 hover:bg-slate-100/80 transition-colors flex flex-col sm:flex-row gap-2 justify-between items-start sm:items-center";
          row.innerHTML = `
            <div class="flex-1 cursor-pointer catalog-preview-trigger">
              <div class="flex items-center gap-2">
                <span class="font-mono text-xs font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-200">${it.item}</span>
                <span class="text-[11px] text-slate-400 font-medium">UOM: ${it.uom || 'CU'}</span>
              </div>
              <p class="text-xs text-slate-800 font-medium mt-1">${it.description}</p>
            </div>
            <div class="flex items-center gap-2 self-end sm:self-center">
              <input type="number" value="1" min="1" class="catalog-qty-input w-12 text-center text-xs font-bold py-1 border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none">
              <button class="btn-add-from-catalog bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors">
                <i data-lucide="plus" class="w-3.5 h-3.5"></i>
                <span>Agregar</span>
              </button>
            </div>
          `;

          // Preview al hacer clic en el texto
          row.querySelector(".catalog-preview-trigger").addEventListener("click", () => {
            updatePreview(it.item, it.description);
          });

          // Botón agregar a cola de impresión
          const qtyInput = row.querySelector(".catalog-qty-input");
          row.querySelector(".btn-add-from-catalog").addEventListener("click", () => {
            const qty = parseInt(qtyInput.value) || 1;
            addItemToPrintQueue(it.item, it.description, qty);
            showToast(`Ítem ${it.item} agregado a la cola de impresión`, "success");
          });

          resultsList.appendChild(row);
        });

        if (window.lucide) lucide.createIcons();
        resultsBox.classList.remove("hidden");
      } catch (err) {
        console.error("Error buscando en catálogo:", err);
      }
    }, 250);
  });
}

// 3. Modal para Agregar Ítem a Base de Datos
function setupAddModal() {
  const modal = document.getElementById("modal-add-item");
  const btnOpen1 = document.getElementById("btn-open-add-modal");
  const btnOpen2 = document.getElementById("btn-trigger-add-modal");
  const btnClose = document.getElementById("btn-close-modal");
  const btnCancel = document.getElementById("btn-cancel-modal");
  const btnSave = document.getElementById("btn-save-modal-item");

  const inputCode = document.getElementById("modal-item-code");
  const inputUom = document.getElementById("modal-item-uom");
  const inputDesc = document.getElementById("modal-item-desc");
  const chkAddToPrint = document.getElementById("modal-add-to-print");
  const inputQty = document.getElementById("modal-item-qty");

  function openModal() {
    inputCode.value = "";
    inputUom.value = "CU";
    inputDesc.value = "";
    inputQty.value = "1";
    chkAddToPrint.checked = true;
    modal.classList.remove("hidden");
    inputCode.focus();
  }

  function closeModal() {
    modal.classList.add("hidden");
  }

  if (btnOpen1) btnOpen1.addEventListener("click", openModal);
  if (btnOpen2) btnOpen2.addEventListener("click", openModal);
  if (btnClose) btnClose.addEventListener("click", closeModal);
  if (btnCancel) btnCancel.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  btnSave.addEventListener("click", async () => {
    const code = inputCode.value.trim().toUpperCase();
    const uom = inputUom.value.trim().toUpperCase() || "CU";
    const desc = inputDesc.value.trim().toUpperCase();
    const addToPrint = chkAddToPrint.checked;
    const qty = parseInt(inputQty.value) || 1;

    if (!code) {
      showToast("Ingrese el código del ítem", "error");
      inputCode.focus();
      return;
    }
    if (!desc) {
      showToast("Ingrese la descripción del artículo", "error");
      inputDesc.focus();
      return;
    }

    btnSave.disabled = true;
    btnSave.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Guardando...</span>`;

    try {
      const res = await fetch("/api/catalog/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item: code, description: desc, uom: uom })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error guardando en el archivo Excel");
      }

      const data = await res.json();
      showToast(data.message, "success");
      loadCatalogStats();

      // Si solicitó agregarlo a la cola de impresión
      if (addToPrint) {
        addItemToPrintQueue(code, desc, qty);
        updatePreview(code, desc);
      }

      closeModal();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btnSave.disabled = false;
      btnSave.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Guardar en Base de Datos</span>`;
      if (window.lucide) lucide.createIcons();
    }
  });
}

function addItemToPrintQueue(code, description, qty = 1) {
  // Si ya está en la lista, sumar la cantidad
  const existing = itemsState.find(it => it.item.toUpperCase() === code.toUpperCase());
  if (existing) {
    existing.qty += qty;
    existing.selected = true;
  } else {
    itemsState.push({
      id: Date.now().toString() + "_" + Math.random().toString(36).substring(2, 5),
      item: code,
      description: description,
      qty: qty,
      selected: true
    });
  }
  renderTable();
  updatePreview(code, description);
}

// 4. Drag & Drop y Carga de Archivo Excel
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

// 5. Carga Manual de Códigos
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

    addItemToPrintQueue(code, desc, qty);

    codeIn.value = "";
    descIn.value = "";
    qtyIn.value = "1";
    codeIn.focus();
    showToast(`Ítem ${code} agregado a impresión`, "success");
  }

  btnAdd.addEventListener("click", addItem);
  [codeIn, descIn, qtyIn].forEach(inp => {
    inp.addEventListener("keypress", e => {
      if (e.key === "Enter") addItem();
    });
  });
}

// 6. Renderizado y Eventos de la Tabla
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
    if (confirm("¿Desea vaciar todos los ítems de la lista de impresión?")) {
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
          No hay ítems en la cola de impresión. Busca en la base de datos, carga un Excel o usa la carga manual.
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
        <input type="text" value="${item.description}" class="item-desc-input w-full bg-transparent hover:bg-white focus:bg-white border border-transparent hover:border-slate-300 focus:border-indigo-500 rounded px-2 py-1 text-xs outline-none uppercase">
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

// 7. Previsualizador en Vivo
function updatePreview(item, description) {
  if (item) lastPreviewItem = item;
  if (description) lastPreviewDesc = description;

  const it = lastPreviewItem || "012345";
  const de = lastPreviewDesc || "EJEMPLO DE ETIQUETA";

  const img = document.getElementById("preview-image");
  const loader = document.getElementById("preview-loading");

  if (loader) loader.classList.remove("hidden");
  const url = `/api/preview-label?item=${encodeURIComponent(it)}&description=${encodeURIComponent(de)}&size=${selectedLabelSize}&_t=${Date.now()}`;

  const tempImg = new Image();
  tempImg.onload = () => {
    img.src = url;
    if (loader) loader.classList.add("hidden");
  };
  tempImg.onerror = () => {
    console.warn("Fallo en carga de preview, reintentando directamente en elemento imagen");
    img.src = url;
    if (loader) loader.classList.add("hidden");
  };
  tempImg.src = url;
}

// 8. Generación de PDF, Impresión y Descarga ZIP
function setupExportEvents() {
  const btnPrintDirect = document.getElementById("btn-print-direct");
  const btnPrintPopup = document.getElementById("btn-print-popup");
  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const btnDownloadZip = document.getElementById("btn-download-zip");

  function getExportPayload() {
    let selected = itemsState.filter(i => i.selected && i.qty > 0);
    if (selected.length === 0) {
      // Si la cola está vacía o no hay selección, exportar el ítem en previsualización
      const it = lastPreviewItem || "012345";
      const de = lastPreviewDesc || "EJEMPLO DE ETIQUETA";
      selected = [{ item: it, description: de, qty: 1 }];
    }
    return {
      items: selected.map(i => ({
        item: i.item,
        description: i.description,
        qty: i.qty || 1
      })),
      filename: loadedFileName || "etiquetas",
      size: selectedLabelSize,
      width_mm: (selectedLabelSize === "60x95" || selectedLabelSize === "60x90") ? 100.0 : 62.0,
      height_mm: (selectedLabelSize === "60x95" || selectedLabelSize === "60x90") ? 62.0 : 29.0
    };
  }

  async function triggerBrowserPrint(openInNewTab = false) {
    const payload = getExportPayload();
    if (!payload) return;

    showToast("Preparando documento térmico Brother...", "info");
    btnPrintDirect.disabled = true;
    if (btnPrintPopup) btnPrintPopup.disabled = true;

    // Si es en nueva pestaña, abrir de inmediato para no perder el contexto de click
    let printTab = null;
    if (openInNewTab) {
      printTab = window.open("", "_blank");
      if (printTab) {
        printTab.document.write(`
          <!DOCTYPE html><html><head><title>Impresión Térmica Brother...</title></head>
          <body style="font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#0f172a;color:#f8fafc;margin:0;">
            <div style="text-align:center;padding:20px;">
              <p style="font-weight:bold;font-size:16px;">Cargando documento térmico...</p>
              <p style="font-size:12px;color:#94a3b8;margin-top:6px;">Usa Ctrl + P y verifica que el papel esté en <b>62mm</b> (Cinta continua).</p>
            </div>
          </body></html>
        `);
      }
    }

    try {
      const res = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Error al preparar documento de impresión");
      }

      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      if (openInNewTab && printTab) {
        printTab.location.href = blobUrl;
        showToast("Documento abierto. Recuerda seleccionar Papel: 62mm en Chrome", "success");
      } else {
        // Impresión directa usando iframe con el PDF en el navegador
        let printFrame = document.getElementById("pdf-print-direct-frame");
        if (printFrame) printFrame.remove();

        printFrame = document.createElement("iframe");
        printFrame.id = "pdf-print-direct-frame";
        printFrame.style.position = "fixed";
        printFrame.style.right = "0";
        printFrame.style.bottom = "0";
        printFrame.style.width = "0";
        printFrame.style.height = "0";
        printFrame.style.border = "none";
        printFrame.src = blobUrl;
        document.body.appendChild(printFrame);

        printFrame.onload = function() {
          setTimeout(() => {
            try {
              printFrame.contentWindow.focus();
              printFrame.contentWindow.print();
              showToast("Diálogo enviado. Si la máquina pide rollo, cambia papel a 62mm", "success");
            } catch (e) {
              console.warn("Fallo print iframe, abriendo en ventana:", e);
              window.open(blobUrl, "_blank");
            }
          }, 500);
        };
      }
    } catch (err) {
      if (printTab) printTab.close();
      showToast(err.message, "error");
    } finally {
      btnPrintDirect.disabled = false;
      if (btnPrintPopup) btnPrintPopup.disabled = false;
    }
  }

  btnPrintDirect.addEventListener("click", () => triggerBrowserPrint(false));
  if (btnPrintPopup) {
    btnPrintPopup.addEventListener("click", () => triggerBrowserPrint(true));
  }

  btnDownloadPdf.addEventListener("click", async () => {
    const payload = getExportPayload();
    if (!payload) return;

    showToast("Generando y descargando PDF...", "info");
    btnDownloadPdf.disabled = true;

    try {
      const res = await fetch("/api/generate-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Error al generar el PDF");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `${payload.filename || "etiquetas"}_${payload.size}.pdf`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        a.remove();
        window.URL.revokeObjectURL(url);
      }, 10000);

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

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Error al generar ZIP");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = `${payload.filename || "etiquetas"}.zip`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        a.remove();
        window.URL.revokeObjectURL(url);
      }, 10000);

      showToast("Archivo ZIP descargado", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      btnDownloadZip.disabled = false;
    }
  });
}
