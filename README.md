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

### Probar Localmente en Windows (Sin Docker):
1. Entra a la carpeta `web`.
2. Haz doble clic en **`run_local.bat`**.
3. Abre automáticamente tu navegador en `http://localhost:8000`.

### Desplegar en Docker:
En la carpeta `web`:
```bash
docker compose up -d --build
```
Acceso desde cualquier navegador en: `http://localhost:8000` (o la IP de tu servidor).

### Instalación como PWA:
- Abre la web en Chrome, Edge o móvil y haz clic en **"Instalar App"** en la barra superior para agregarla como aplicación de escritorio o acceso móvil.

---

## 🐙 3. Control de Versiones con Git y GitHub

Este proyecto utiliza ramas estándar y **tags anotados** para registrar el historial de versiones con sus cambios detallados:

### Historial de Tags y Versiones:
- **`v1.0.0`**: Versión inicial Desktop. Soporte de Excel (.xlsx/.xls), códigos Code39, recorte de código de barras, generación de etiquetas 600x300 px y exportación en PDF 60x30 mm.
- **`v1.1.0`**: Versión Web SPA y contenedorización Docker. Backend FastAPI con procesamiento en memoria RAM (`BytesIO`), drag & drop, live preview y compatibilidad con impresoras térmicas.
- **`v1.2.0`**: Soporte PWA (Progressive Web App). Manifiesto Web, Service Worker para caché estática, íconos de alta resolución (192px/512px) y botón directo de instalación en el navegador.

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

