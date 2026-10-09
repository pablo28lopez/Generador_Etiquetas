# Suite Generador de Etiquetas de Depósito (Desktop & Web PWA)

Solución integral para diseño, previsualización e impresión térmica de etiquetas con código de barras **Code39** (60x30 mm) a partir de planillas Excel (.xlsx / .xls) o carga manual.

---

## 📂 Estructura del Repositorio

```text
generador-etiquetas/
├── app.py                  # Versión Escritorio en Python (Tkinter + Pillow + FPDF2)
├── build.bat               # Compilador automático de 1 clic para generar .exe (PyInstaller)
├── installer.iss           # Script de Inno Setup para crear instalador formal Windows
├── requirements.txt        # Dependencias de Python para la versión desktop
├── icono.ico               # Ícono oficial de la aplicación
├── logo.png                # Logotipo institucional
├── arial.ttf / arialbd.ttf # Fuentes TrueType embebidas
├── .gitignore              # Reglas de exclusión para Git
├── README.md               # Esta documentación
│
└── web/                    # Versión Web SPA / PWA & Docker
    ├── Dockerfile          # Imagen Linux optimizada (Python 3.11 slim)
    ├── docker-compose.yml  # Orquestador Docker para despliegue inmediato
    ├── .dockerignore       # Exclusiones de construcción de imagen Docker
    ├── requirements.txt    # Dependencias web (FastAPI, Uvicorn, Pandas, FPDF2, Barcode)
    ├── main.py             # Backend FastAPI con generación en memoria RAM
    ├── iniciar_app.bat     # Lanzador por lotes con inicio automático del servidor
    ├── iniciar_app.vbs     # Lanzador silencioso sin consola para acceso directo
    ├── detener_servidor.bat# Script para detener el servidor local (puerto 8000)
    ├── launcher.py         # Orquestador Python y apertura en modo ventana app
    ├── run_local.bat       # Servidor local para pruebas en Windows (CRLF)
    ├── fonts/              # Fuentes Arial incluidas
    └── static/             # Frontend Single Page Application & PWA
        ├── manifest.json   # Manifiesto PWA para instalación como App nativa
        ├── index.html      # Interfaz responsiva (Tailwind CSS, Lucide Icons)
        ├── css/style.css   # Estilos personalizados y animaciones
        ├── js/app.js       # Lógica cliente (Live Preview, Drag & Drop, Impresión)
        ├── js/service-worker.js # Service Worker con caché fuera de línea
        └── img/            # Íconos 192x192, 512x512 y logos
```

---

## 🖥️ 1. Versión de Escritorio Windows

### Compilar el Ejecutable Portable (.exe):
1. Haz doble clic sobre **`build.bat`**.
2. El script instalará las dependencias y compilará la app mediante PyInstaller incrustando iconos y fuentes.
3. El archivo resultante estará en `dist\GeneradorEtiquetas.exe`.

### Generar el Asistente de Instalación (Setup.exe):
1. Instala [Inno Setup](https://jrsoftware.org/isdl.php).
2. Haz clic derecho sobre **`installer.iss`** y selecciona **"Compile"**.
3. Se creará `dist\instalador\Instalador_Generador_Etiquetas_Setup.exe` con accesos directos en Escritorio y Menú Inicio.

---

## 🌐 2. Versión Web (SPA / PWA) & Docker

### Acceso Directo de 1 Clic desde el Escritorio:
1. Haz doble clic en el acceso directo de tu Escritorio: **`Generador de Etiquetas (Web).lnk`** (o ejecuta **`iniciar_app.vbs`**).
2. El script detectará si el servidor ya está corriendo. Si no lo está, lo iniciará silenciosamente en segundo plano.
3. Se abrirá la aplicación directamente en modo ventana nativa independiente (utilizando Microsoft Edge o Google Chrome sin distracciones de barras de navegación ni pestañas).
4. Para detener el servidor si lo requieres, ejecuta **`detener_servidor.bat`**.

### Probar Localmente en Windows (Modo Consola):
1. Entra a la carpeta `web`.
2. Haz doble clic en **`iniciar_app.bat`** o **`run_local.bat`**.
3. Abre automáticamente tu navegador en `http://localhost:8000`.

### Desplegar en Docker:
En la carpeta `web`:
```bash
docker compose up -d --build
```
Acceso desde cualquier navegador en: `http://localhost:8000` (o la IP de tu servidor).

### Instalación como PWA:
- Abre la web en Chrome, Edge o móvil y haz clic en **"Instalar App"** en la barra superior para agregarla como aplicación de escritorio o acceso móvil.

### 📏 Soporte de Tamaños de Etiquetas (60x30 mm y 60x95 mm Horizontal):
- **Botones Selector Tipo Check:** Permite alternar en tiempo real entre el tamaño estándar (**60 x 30 mm**, 600x300 px) y el tamaño horizontal grande (**60 x 95 mm**, 950x600 px, etiqueta institucional de depósito).
- **Diseño Oficial para 60 x 95 mm (Grande / Horizontal):**
  - **Encabezado institucional:** Logotipo oficial de alta resolución de **DLS Archer** a la izquierda y, justo al lado, la píldora redondeada con contorno marino `#042433` y texto en relieve `DLS DEPOSITO NEUQUEN`.
  - **Banda negra sólida de alto contraste:** Con el código de ítem en tipografía blanca gigante en negrita (con autoescalado dinámico según longitud), visible a gran distancia en bodega.
  - **Cuadro inferior enmarcado:** Recuadro blanco con borde negro para la descripción del artículo, con tipografía negrita adaptativa y ajuste multilínea automático.
- **Impresión Directa desde el Navegador (100% Nativa sin Modificar Propiedades):**
  - Utiliza un motor de impresión HTML con directivas `@page { size: 95mm 60mm; margin: 0; }` (o `60mm 30mm`) e imágenes Base64 incrustadas.
  - **Botón "Imprimir Directo (Navegador)":** Desencadena de inmediato el cuadro de impresión nativo del navegador con tamaño térmico exacto y margen cero, utilizando un marco de renderizado compatible con el motor de seguridad de Chromium/Edge.
  - **Botón "Abrir Pestaña de Impresión (Ctrl+P)":** Opción adicional de un clic que abre una pestaña limpia e independiente con las etiquetas a escala 1:1 y el cuadro de diálogo de impresión listo para enviar al driver.
- **Exportación en PDF Nativamente Horizontal (Landscape):**
  - El PDF se genera con orientación horizontal `FPDF("L", "mm", (60.0, 95.0))` (95.0 mm de ancho x 60.0 mm de alto), adaptándose al rollo térmico sin requerir rotaciones ni ajustes manuales de propiedades de impresión.

### 📚 Base de Datos Integrada (DATOS_DEPO.xlsx):
- **Catálogo de ~36.800 ítems:** Búsqueda ultrarrápida en memoria RAM por código o descripción.
- **Botón "➕ Nuevo Ítem en Base":** Permite agregar nuevos registros directamente al archivo Excel `DATOS_DEPO.xlsx` respetando el formato original de 4 columnas (`[Código, UOM, None, Descripción]`).
- **Descarga Directa:** Botón para descargar el Excel actualizado en cualquier momento.

---

## 🐙 3. Control de Versiones con Git y GitHub

Este proyecto utiliza ramas estándar y **tags anotados** para registrar el historial de versiones con sus cambios detallados:

### Historial de Tags y Versiones:
- **`v1.0.0`**: Versión inicial Desktop. Soporte de Excel (.xlsx/.xls), códigos Code39, recorte de código de barras, generación de etiquetas 600x300 px y exportación en PDF 60x30 mm.
- **`v1.1.0`**: Versión Web SPA y contenedorización Docker. Backend FastAPI con procesamiento en memoria RAM (`BytesIO`), drag & drop, live preview y compatibilidad con impresoras térmicas.
- **`v1.2.0`**: Soporte PWA (Progressive Web App). Manifiesto Web, Service Worker para caché estática, íconos de alta resolución (192px/512px) y botón directo de instalación en el navegador.
- **`v1.2.1`**: Guía completa de distribución y compartición de la suite.
- **`v1.3.0`**: Integración de Base de Datos Excel (`DATOS_DEPO.xlsx`), buscador en tiempo real entre ~36.800 ítems, modal para agregar ítems al Excel en el mismo formato original y persistencia en Docker via volumen `data/`.
- **`v1.3.1`**: Lanzadores de 1 clic silenciosos (`iniciar_app.bat`, `iniciar_app.vbs`), apertura en modo ventana app (`--app`) y accesos directos oficiales en el Escritorio de Windows con icono institucional.
- **`v1.4.0`**: Selector de 2 tamaños de etiqueta tipo check (**60 x 30 mm** y **60 x 90 mm**), rediseño de vista previa en vivo proporcional, formato multilínea optimizado para 60x90, y exportación PDF/ZIP adaptada a ambas medidas térmicas.
- **`v1.5.0`**: Formato institucional oficial de etiqueta con cabecera `DEPOSITO DLS NEUQUEN`, logo DLS Archer, banda negra con código de ítem en blanco y cuadro inferior para descripción; simplificación del botón a 'Grande'.
- **`v1.6.0`**: Medida 60x95 mm, nuevo logotipo institucional y motor de impresión HTML inicial.
- **`v1.7.0`**: Rediseño definitivo en formato **Horizontal 95 x 60 mm** (950x600 px); logotipo a la izquierda y píldora `DLS DEPOSITO NEUQUEN` al lado; código de ítem central sobre franja negra sólida; cuadro de descripción inferior enmarcado; doble solución de impresión directa web (botón directo en página y botón de apertura en pestaña dedicada Ctrl+P sin bloqueos de navegador); PDF configurado nativamente en Landscape (95.0 x 60.0 mm).
- **`v1.8.0`**: Paridad total entre versión Web y Escritorio + Compatibilidad Brother QL-800 + Portabilidad 100% independiente.
- **`v1.9.0`**: Encabezado ampliado (tamaño 52), recuadro de ID en negro con tipografía blanca, motor de impresión PDF nativo en navegador para Brother QL-800 y binario standalone sincronizado.
- **`v2.0.0`**: Tipografía Arial Black oficial en ID + Generador de código de barras ultra robusto en memoria + Diagnóstico Brother QL-800.
- **`v2.1.0`**: Nueva identidad de cabecera oficial + Restauración de tipografía original en etiquetas chicas + Nombres exactos de rollos Brother:
  - **Cabecera Institucional:** Eliminado el cuadro verde 'Depósito' y la línea secundaria; reemplazado por `DLS Archer - Depósito Neuquén` en Web y Escritorio.
  - **Etiquetas Chicas Originales:** Restaurado el tamaño y fuente original (`Arial Bold` tamaño 80 pt en ID y `Arial` 22 pt en descripción), reservando Arial Black exclusivamente para las etiquetas Grandes.
  - **Nomenclatura Oficial Brother:** Botones y selectores ahora reflejan la denominación exacta de la impresora Brother: `62 x 29 mm (Chica - DK-11209 / Cinta 62mm)` y `62 x 100 mm (Grande - DK-11202 / Cinta 62mm)`.
  - **Distribución Actualizada:** Web y ejecutables de escritorio sincronizados en `Proyecto DEPO`.
- **`v2.2.0`**: ID en Arial Black maximizado y centrado milimétrico + Fix descarga PDF 1-clic + Resolución mismatch rollo Brother QL-800:
  - **ID Maximizado y Centrado:** Algoritmo dinámico que escala la fuente Arial Black hasta 150 pt con compensación de offsets verticales de Pillow, logrando márgenes perfectamente simétricos arriba/abajo (18 px) y ocupando el ancho completo del recuadro negro.
  - **Corrección Descarga PDF:** Soporte para descargar directamente la previsualización activa sin requerir selección previa en la tabla, y eliminación de revocación prematura de Blob URLs en navegadores Chromium.
  - **Diagnóstico y Guía Brother QL-800:** Explicación y resolución del error de coincidencia de rollo mediante ajuste de tamaño de papel a `62mm` en el diálogo de impresión de Chrome.
  - **Sincronización Completa:** Generación de nuevo ejecutable `GeneradorEtiquetas.exe` y archivo ZIP portable listos para distribución independiente.
- **`v2.3.0`**: Etiqueta chica 62x29 mm 100% centrada y márgenes mínimos + Blindaje códigos de barra en Portable + Seteo automático Chrome/Edge para Brother QL-800.
- **`v2.4.0`**: Etiqueta chica con márgenes mínimos absolutos + Solución permanente para driver Brother QL-800:
  - **Márgenes Mínimos Absolutos en Etiqueta Chica (62x29 mm):** Código de barras maximizado a 608 px (98% del ancho del rollo de 62mm), código de ítem en Arial Bold 94 pt con auto-escalado y compensación de glifos, descripción en Arial 28 pt. Márgenes superior/inferior reducidos a solo 1.2 mm (12 px) y laterales a 1.7 mm (17 px) totalmente simétricos.
  - **Solución Definitiva Driver Brother QL-800:** Script automatizado `configurar_impresora_brother.bat` para fijar la medida de 62mm de manera permanente en Windows (`rundll32 printui.dll`), eliminando para siempre la necesidad de cambiar la medida manualmente en el driver.
  - **Impresión Web Directa Blindada:** Montaje optimizado en iframe fuera de pantalla (620x290 px) con decodificación de imagen previa para evitar bloqueos y diálogos fallidos en Google Chrome y Microsoft Edge.
  - **Paridad Total y Binarios:** Ejecutable `GeneradorEtiquetas.exe` y ZIP portable actualizados en `Proyecto DEPO`.

### Publicar en tu repositorio de GitHub:
Para subir este proyecto a tu cuenta de GitHub en la rama **`main`** junto con todos los tags:

```bash
# 1. Vincular con tu repositorio remoto de GitHub
git remote add origin https://github.com/<tu-usuario>/<tu-repositorio>.git

# 2. Subir la rama principal 'main' y todos los tags con sus comentarios
git push -u origin main --tags
```

### Crear una nueva versión con Tag para futuros cambios:
Cada vez que se introduzcan modificaciones en el código:
```bash
# 1. Agregar y confirmar los cambios en la rama main
git add .
git commit -m "Descripción concisa del cambio"

# 2. Crear el tag anotado con los detalles de la versión
git tag -a v1.3.0 -m "Versión 1.3.0:
- Cambio 1: Detalle del cambio
- Cambio 2: Corrección o nueva función"

# 3. Publicar la rama main y los tags en GitHub
git push origin main
git push origin --tags
```

---

## 📢 4. Cómo Compartir la Aplicación con Otros Usuarios

Tienes 4 formas prácticas de compartirla según tus necesidades:

### A. Para usuarios que quieren la aplicación en su PC (Windows)
1. **Compartir directamente el archivo:** Envíales el archivo `Instalador_Generador_Etiquetas_Setup.exe` o `GeneradorEtiquetas.exe` por red interna, Google Drive, OneDrive o Teams. No necesitan tener Python instalado.
2. **Mediante GitHub Releases:** En tu repositorio de GitHub, entra a la sección **Releases**, selecciona tu tag (ej. `v1.2.0`) y adjunta el archivo `.exe`. Los usuarios podrán descargarlo directamente desde GitHub en cualquier momento.

### B. Para uso en la red de la empresa (Wi-Fi / LAN sin instalar nada)
1. En tu máquina, ejecuta `web\run_local.bat` (o déjalo corriendo en un servidor).
2. Pásales tu dirección IP local:
   👉 **`http://10.12.70.126:8000`**
3. Cualquier dispositivo (PC, tablet o celular en el depósito) podrá abrir la app en su navegador e incluso hacer clic en **"Instalar App"** para usarla en pantalla completa como una app nativa.

### C. Para mostrarla o probarla por Internet (Túnel temporal sin configurar routers)
1. Con la app corriendo en tu PC, abre una terminal y ejecuta:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
2. Te entregará un enlace HTTPS público temporal (ej: `https://palabras-aleatorias.trycloudflare.com`) que puedes pasarle a cualquier persona en el mundo.

### D. Para alojamiento permanente 24/7 (En Docker)
Copia la carpeta `web` a un servidor o VPS con Docker y ejecuta `docker compose up -d --build`. La app estará disponible permanentemente en la IP o dominio de tu servidor.

