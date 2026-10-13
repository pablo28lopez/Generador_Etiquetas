# Generador de Etiquetas de Depósito (Web SPA & PWA)

Solución integral y moderna para diseño, previsualización en vivo e impresión térmica de etiquetas con código de barras **Code39** / **Code128** en impresoras Brother QL (62x29 mm y 62x100 mm), a partir de la base de datos Excel (`DATOS_DEPO.xlsx`), carga de archivos o entrada manual.

---

## 📂 Estructura del Proyecto

```text
generador-etiquetas/
├── web/                         # Aplicación Web Integral (FastAPI + SPA/PWA)
│   ├── main.py                  # Backend FastAPI (renderizado Pillow, PDF FPDF2, API)
│   ├── requirements.txt         # Dependencias Python (FastAPI, Uvicorn, Pandas, etc.)
│   ├── Dockerfile               # Contenedor Docker listo para producción
│   ├── docker-compose.yml       # Orquestador Docker
│   ├── iniciar_app.bat          # Lanzador 1-clic con servidor automático y modo app
│   ├── iniciar_app.vbs          # Lanzador silencioso sin ventana de consola
│   ├── iniciar_servidor_red.bat # Servidor en red LAN (muestra IP local)
│   ├── detener_servidor.bat     # Detiene el servidor local
│   ├── configurar_impresora_brother.bat # Asistente permanente para driver Windows
│   ├── data/
│   │   └── DATOS_DEPO.xlsx      # Base de datos de artículos (~36.800 ítems)
│   ├── fonts/                   # Fuentes oficiales (Arial, Arial Bold, Arial Black)
│   └── static/                  # Frontend SPA / PWA
│       ├── index.html           # Interfaz de usuario (Tailwind CSS, Lucide)
│       ├── manifest.json        # Manifiesto PWA para instalación como app nativa
│       ├── css/style.css        # Estilos y animaciones
│       ├── js/app.js            # Lógica cliente (Live Preview, Drag&Drop, Impresión)
│       ├── js/service-worker.js # Service worker para funcionamiento offline
│       └── img/                 # Logos e íconos institucionales
│
├── tests/
│   └── test_suite.py            # Suite automatizada de pruebas unitarias
├── configurar_impresora_brother.bat # Script de configuración rápida Brother QL
└── README.md                    # Documentación del sistema
```

---

## 🚀 Inicio Rápido

### 1. Iniciar con 1 Clic (Modo App Nativa)
1. Haz doble clic en **`iniciar_app.bat`** (o **`iniciar_app.vbs`** para inicio silencioso).
2. Se iniciará el servidor en segundo plano y se abrirá automáticamente la ventana de la aplicación (en Microsoft Edge o Google Chrome sin barra de navegación).

### 2. Iniciar para la Red Local (Depósito)
1. Ejecuta **`iniciar_servidor_red.bat`**.
2. Mostrará la dirección IP local (ejemplo: `http://192.168.1.50:8000`) para que cualquier computadora o tablet de la red pueda generar e imprimir etiquetas.

### 3. Ejecutar con Docker
```bash
cd web
docker compose up -d --build
```
Acceso en cualquier navegador: `http://localhost:8000`.

---

## 🖨️ Configuración Impresora Brother QL-800

### Solución Permanente al error de rollo / medida en Drivers
Windows suele configurar de fábrica la Brother QL-800 en `29mm x 90mm`. Para que Chrome y Edge recuerden la medida correcta para siempre:
1. Ejecuta **`configurar_impresora_brother.bat`**.
2. En la ventana de Preferencias de Impresión que se abre:
   - Selecciona **`62mm x 29mm`** (etiqueta chica DK-11209) o **`62mm`** (rollo continuo DK-22205).
   - Haz clic en **Aplicar** y **Aceptar**.
3. ¡Listo! A partir de ese momento, todos los navegadores imprimirán directamente sin solicitar cambio de medida.

---

## 🧪 Pruebas Automatizadas

Para ejecutar el test suite integral:
```bash
py -3 tests/test_suite.py
```
Valida:
- Carga y búsqueda en el catálogo Excel (~13.570 ítems únicos).
- Generación y legibilidad de códigos de barra Code39 y Code128.
- Renderizado milimétrico y márgenes mínimos en ambas medidas.
- Generación de documentos PDF y HTML térmico para Brother QL.
- Endpoint de compresión de imágenes ZIP.
- Verificación de estado de salud (*Health check*).

---

## 🐙 Historial de Versiones

- **`v2.6.0`**: **Impresión Directa por Comandos Nativos RAW (Sin Driver Windows):**
  - Motor de generación de comandos Brother Raster binarios (`ESC i a`, `ESC i z`, raster scanlines, autocut) integrado en el backend.
  - Envío directo al puerto USB / Spooler de Windows en modo `RAW` mediante `winspool.drv`, omitiendo el driver de Brother por completo.
  - Impresión con 1 clic desde el navegador sin abrir diálogos de impresión, sin fallos de roll mismatch y con corte automático.
  - Detección automática de impresora Brother conectada y selector de tipo de rollo (troquelado DK-11209/DK-11202 o continuo DK-22205).
  - Descarga de archivos binarios `.prn` para depuración.
- **`v2.5.0`**: **Edición Web Pura & Depuración Total:**
  - Purgado y eliminación de todos los componentes de escritorio antiguos y binarios pesados.
  - Suite Web 100% blindada, activa y testeada con suite automatizada (`tests/test_suite.py`).
  - Sincronización en `Proyecto DEPO` con lanzador directo y asistente de configuración Brother.
- **`v2.4.0`**: Etiqueta chica con márgenes mínimos absolutos + Solución permanente driver Brother QL-800.
- **`v2.3.0`**: Etiqueta chica 62x29 mm centrada y blindaje de códigos de barra.
- **`v2.2.0`**: ID en Arial Black maximizado y corrección de descargas PDF.
- **`v2.1.0`**: Cabecera institucional `DLS Archer - Depósito Neuquén`.
