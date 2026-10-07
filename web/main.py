import io
import os
import re
import zipfile
import base64
import textwrap
from typing import List, Optional, Tuple

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import openpyxl
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

# Inicializar FastAPI
app = FastAPI(
    title="Generador de Etiquetas de Depósito",
    description="API y SPA / PWA para generar etiquetas con código de barras e impresión térmica en PDF",
    version="2.1.0"
)

# Rutas base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
STATIC_DIR = os.path.join(BASE_DIR, "static")
CATALOG_PATH = os.path.join(DATA_DIR, "DATOS_DEPO.xlsx")

# Asegurar directorios
os.makedirs(DATA_DIR, exist_ok=True)

# Catálogo en memoria
catalog_cache: List[dict] = []
catalog_unique_codes = set()


def load_catalog():
    """Carga el catálogo Excel DATOS_DEPO.xlsx en memoria RAM para búsquedas instantáneas."""
    global catalog_cache, catalog_unique_codes
    if not os.path.exists(CATALOG_PATH):
        print(f"[Aviso] Archivo de catálogo {CATALOG_PATH} no encontrado.")
        return

    try:
        # header=None porque DATOS_DEPO.xlsx no tiene fila de títulos
        df = pd.read_excel(CATALOG_PATH, header=None, dtype=str)
        items = []
        codes = set()

        for _, row in df.iterrows():
            code = str(row[0] if not pd.isna(row[0]) else "").strip()
            uom = str(row[1] if not pd.isna(row[1]) else "").strip()
            desc = str(row[3] if not pd.isna(row[3]) else "").strip()
            if code and code not in codes:
                codes.add(code)
                items.append({
                    "item": code,
                    "uom": uom or "CU",
                    "description": desc
                })

        catalog_cache = items
        catalog_unique_codes = codes
        print(f"[Catálogo] Cargados {len(catalog_cache)} ítems únicos de {len(df)} registros.")
    except Exception as e:
        print(f"[Error] Falló la carga del catálogo {CATALOG_PATH}: {e}")


@app.on_event("startup")
def on_startup():
    load_catalog()


# Carga de fuentes segura
def get_font(font_name: str, size: int) -> ImageFont.ImageFont:
    font_path = os.path.join(FONTS_DIR, font_name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    try:
        return ImageFont.truetype(font_name, size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def clean_filename(name: str) -> str:
    """Sanitiza nombres de ítems para nombres de archivos."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(name).strip())


def generate_barcode_image(item: str, target_size: Tuple[int, int] = (595, 120)) -> Optional[Image.Image]:
    """Genera la imagen del código de barras Code39 recortado al 70% de altura."""
    try:
        item_str = str(item).strip().upper()
        if not item_str:
            return None

        code39 = barcode.get_barcode_class('code39')
        writer = ImageWriter()
        writer.set_options({"write_text": True})

        bc = code39(item_str, writer=writer, add_checksum=False)
        
        fp = io.BytesIO()
        bc.write(fp)
        fp.seek(0)

        with Image.open(fp) as raw_img:
            img_rgb = raw_img.convert("RGB")
            width, height = img_rgb.size
            img_cropped = img_rgb.crop((0, 0, width, int(height * 0.70)))
            return img_cropped.resize(target_size)
    except Exception as e:
        print(f"Error generando código de barras para '{item}': {e}")
        return None


def create_label_image(item: str, description: str, size: str = "60x30") -> Optional[Image.Image]:
    """Genera la imagen completa de la etiqueta térmica:
       - 60x30 mm: 600x300 px (horizontal estándar)
       - 60x90 mm: 600x900 px (vertical extendida con descripción multilínea)
    """
    item_text = str(item).upper().strip()
    desc_text = str(description).upper().strip()

    if size in ("60x95", "60x90"):
        # Formato Grande 60x95 mm (600x950 px) - Formato institucional DLS Archer Depósito Neuquén
        w, h = 600, 950
        label = Image.new('RGB', (w, h), 'white')
        draw = ImageDraw.Draw(label)

        # 1. Logo DLS Archer (arriba centrado)
        logo_path = os.path.join(STATIC_DIR, "img", "logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(BASE_DIR, "logo.png")

        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                lh = 150
                lw = int(logo.width * (lh / logo.height))
                logo_resized = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                label.paste(logo_resized, ((w - lw) // 2, 25), logo_resized)
            except Exception as e:
                print(f"Error cargando logo en etiqueta 60x95: {e}")

        # 2. Píldora / Encabezado DEPOSITO DLS NEUQUEN
        pill_top, pill_bottom = 185, 245
        pill_left, pill_right = 30, w - 30
        draw.rounded_rectangle([pill_left, pill_top, pill_right, pill_bottom], radius=18, outline='#042433', width=5)

        font_h = get_font("arialbd.ttf", 28)
        text_h = "DEPOSITO DLS NEUQUEN"
        hb = draw.textbbox((0, 0), text_h, font=font_h)
        hx = (w - (hb[2] - hb[0])) // 2
        hy = pill_top + (pill_bottom - pill_top - (hb[3] - hb[1])) // 2 - 3
        draw.text((hx, hy), text_h, font=font_h, fill='#042433')

        # 3. Código de Barras Code39
        bc_img = generate_barcode_image(item_text, target_size=(540, 140))
        if bc_img:
            label.paste(bc_img, (30, 265))

        # 4. Franja central negra con Código de Ítem en blanco
        band_top, band_bottom = 425, 545
        draw.rectangle([pill_left, band_top, pill_right, band_bottom], fill='black')

        it_font_size = 72
        font_item = get_font("arialbd.ttf", it_font_size)
        ib = draw.textbbox((0, 0), item_text, font=font_item)
        while (ib[2] - ib[0]) > (pill_right - pill_left - 30) and it_font_size > 36:
            it_font_size -= 4
            font_item = get_font("arialbd.ttf", it_font_size)
            ib = draw.textbbox((0, 0), item_text, font=font_item)

        ix = (w - (ib[2] - ib[0])) // 2
        iy = band_top + (band_bottom - band_top - (ib[3] - ib[1])) // 2 - 5
        draw.text((ix, iy), item_text, font=font_item, fill='white')

        # 5. Cuadro inferior con Descripción Enmarcado
        desc_top, desc_bottom = 570, 920
        draw.rectangle([pill_left, desc_top, pill_right, desc_bottom], outline='black', width=4, fill='white')

        box_w = pill_right - pill_left - 40
        box_h = desc_bottom - desc_top

        font_size = 48
        font_desc = get_font("arialbd.ttf", font_size)
        lines = [desc_text]

        if draw.textbbox((0, 0), desc_text, font=font_desc)[2] > box_w:
            font_size = 38
            font_desc = get_font("arialbd.ttf", font_size)
            lines = textwrap.wrap(desc_text, width=25)
            if len(lines) > 3:
                font_size = 30
                font_desc = get_font("arialbd.ttf", font_size)
                lines = textwrap.wrap(desc_text, width=32)[:5]

        line_h = font_size + 14
        total_text_h = len(lines) * line_h
        start_y = desc_top + (box_h - total_text_h) // 2

        for i, line in enumerate(lines):
            bb = draw.textbbox((0, 0), line, font=font_desc)
            lw_text = bb[2] - bb[0]
            lx = pill_left + (pill_right - pill_left - lw_text) // 2
            draw.text((lx, start_y + i * line_h), line, font=font_desc, fill='black')

        return label

    else:
        # Formato estándar 60x30 mm (600x300 px)
        bc_img = generate_barcode_image(item_text, target_size=(595, 120))
        if bc_img is None:
            return None

        ancho, alto = 600, 300
        label = Image.new('RGB', (ancho, alto), 'white')
        draw = ImageDraw.Draw(label)

        font_item = get_font("arialbd.ttf", 80)
        font_description = get_font("arial.ttf", 22)

        # Pegar código de barras
        bc_x = (ancho - bc_img.width) // 2
        bc_y = 10
        label.paste(bc_img, (bc_x, bc_y))

        # Número de ítem debajo del código
        bbox_item = draw.textbbox((0, 0), item_text, font=font_item)
        item_w = bbox_item[2] - bbox_item[0]
        item_x = (ancho - item_w) // 2
        item_y = bc_y + 120 - 15
        draw.text((item_x, item_y), item_text, fill='black', font=font_item)

        # Descripción debajo del ítem
        bbox_desc = draw.textbbox((0, 0), desc_text, font=font_description)
        desc_w = bbox_desc[2] - bbox_desc[0]

        if desc_w > (ancho - 20):
            while len(desc_text) > 4 and (draw.textbbox((0, 0), desc_text + "...", font=font_description)[2] - draw.textbbox((0, 0), desc_text + "...", font=font_description)[0]) > (ancho - 20):
                desc_text = desc_text[:-1]
            desc_text = desc_text + "..."
            bbox_desc = draw.textbbox((0, 0), desc_text, font=font_description)
            desc_w = bbox_desc[2] - bbox_desc[0]

        desc_x = (ancho - desc_w) // 2
        desc_y = item_y + (bbox_item[3] - bbox_item[1]) + 25
        draw.text((desc_x, desc_y), desc_text, fill='black', font=font_description)

        return label


# ==========================================
# MODELOS PYDANTIC
# ==========================================
class ItemRequest(BaseModel):
    item: str
    description: str
    qty: int = 1


class GeneratePdfRequest(BaseModel):
    items: List[ItemRequest]
    filename: Optional[str] = "etiquetas"
    size: Optional[str] = "60x30"
    width_mm: Optional[float] = 60.0
    height_mm: Optional[float] = 30.0


class AddCatalogItemRequest(BaseModel):
    item: str
    description: str
    uom: Optional[str] = "CU"


# ==========================================
# ENDPOINTS API - GENERAL Y PREVIEW
# ==========================================
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Generador de Etiquetas Web",
        "version": "2.1.0",
        "catalog_loaded": len(catalog_cache) > 0,
        "total_catalog_items": len(catalog_cache)
    }


@app.get("/api/preview-label")
def preview_label(
    item: str = Query("012345"),
    description: str = Query("EJEMPLO DE DESCRIPCIÓN"),
    size: str = Query("60x30")
):
    """Devuelve la imagen JPEG generada en vivo para previsualización (60x30 o 60x90)."""
    img = create_label_image(item, description, size=size)
    if not img:
        raise HTTPException(status_code=400, detail="No se pudo generar la etiqueta")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="image/jpeg")


# ==========================================
# ENDPOINTS API - BASE DE DATOS / CATÁLOGO
# ==========================================
@app.get("/api/catalog/stats")
def get_catalog_stats():
    """Devuelve estadísticas de la base de datos DATOS_DEPO.xlsx."""
    return {
        "total_items": len(catalog_cache),
        "filename": os.path.basename(CATALOG_PATH),
        "exists": os.path.exists(CATALOG_PATH)
    }


@app.get("/api/catalog/search")
def search_catalog(q: str = Query("", min_length=1), limit: int = 50):
    """Busca artículos en la base de datos por código o descripción."""
    query = q.strip().upper()
    if not query:
        return []

    results = []
    # 1. Priorizar los que coinciden al principio del código
    for item in catalog_cache:
        if item["item"].startswith(query):
            results.append(item)
            if len(results) >= limit:
                return results

    # 2. Agregar los que contengan el término en código o descripción
    for item in catalog_cache:
        if item in results:
            continue
        if query in item["item"] or query in item["description"].upper():
            results.append(item)
            if len(results) >= limit:
                break

    return results


@app.post("/api/catalog/add")
def add_catalog_item(req: AddCatalogItemRequest):
    """Agrega un nuevo ítem al archivo Excel DATOS_DEPO.xlsx manteniendo exactamente el formato de 4 columnas."""
    item_code = req.item.strip().upper()
    desc = req.description.strip().upper()
    uom = (req.uom or "CU").strip().upper()

    if not item_code or not desc:
        raise HTTPException(status_code=400, detail="El código de ítem y la descripción son obligatorios.")

    # Guardar en el archivo Excel DATOS_DEPO.xlsx con openpyxl
    try:
        if os.path.exists(CATALOG_PATH):
            wb = openpyxl.load_workbook(CATALOG_PATH)
            sheet = wb.active
        else:
            wb = openpyxl.Workbook()
            sheet = wb.active
            sheet.title = "Hoja1"

        # Formato exacto original de 4 columnas: [Item, UOM, None, Description]
        sheet.append([item_code, uom, None, desc])
        wb.save(CATALOG_PATH)
        wb.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error escribiendo en el archivo Excel: {str(e)}")

    # Actualizar caché en memoria RAM inmediatamente
    new_entry = {"item": item_code, "uom": uom, "description": desc}
    found = False
    for i, it in enumerate(catalog_cache):
        if it["item"] == item_code:
            catalog_cache[i] = new_entry
            found = True
            break
    if not found:
        catalog_cache.insert(0, new_entry)
        catalog_unique_codes.add(item_code)

    return {
        "status": "success",
        "message": f"Ítem '{item_code}' agregado exitosamente al catálogo.",
        "item": new_entry,
        "total_items": len(catalog_cache)
    }


@app.get("/api/catalog/download")
def download_catalog():
    """Permite descargar el archivo DATOS_DEPO.xlsx actualizado."""
    if not os.path.exists(CATALOG_PATH):
        raise HTTPException(status_code=404, detail="El archivo DATOS_DEPO.xlsx no se encuentra en el servidor.")
    return FileResponse(
        CATALOG_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="DATOS_DEPO.xlsx"
    )


# ==========================================
# ENDPOINTS API - EXCEL EXTERNO, PDF Y ZIP
# ==========================================
@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """Parsea un archivo Excel subido manteniendo ceros a la izquierda."""
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser formato .xlsx o .xls")

    contents = await file.read()
    buffer = io.BytesIO(contents)

    try:
        df = pd.read_excel(buffer, dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo Excel: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="El archivo Excel está vacío")

    columna_codigo = None
    inicio_fila = None

    for col in df.columns:
        col_series = df[col].dropna().astype(str)
        for i, val in col_series.items():
            if val.strip().startswith("0"):
                columna_codigo = col
                inicio_fila = i
                break
        if columna_codigo is not None:
            break

    if columna_codigo is None:
        raise HTTPException(
            status_code=422,
            detail="No se encontró ninguna fila con código que inicie con '0'. Verifique la estructura del archivo."
        )

    idx_col = df.columns.get_loc(columna_codigo)
    df_recortado = df.iloc[inicio_fila:, idx_col:idx_col + 3].copy()

    if df_recortado.shape[1] < 3:
        raise HTTPException(status_code=400, detail="Se requieren al menos 3 columnas consecutivas (Item, Descripción, Cantidad).")

    cols = list(df_recortado.columns)
    items_extraidos = []

    for _, row in df_recortado.iterrows():
        it = str(row[cols[0]] if not pd.isna(row[cols[0]]) else "").strip()
        desc = str(row[cols[1]] if not pd.isna(row[cols[1]]) else "").strip()
        cant_raw = str(row[cols[2]] if not pd.isna(row[cols[2]]) else "1").strip()

        if cant_raw.endswith(".0"):
            cant_raw = cant_raw[:-2]

        try:
            qty = int(cant_raw)
        except ValueError:
            qty = 1

        if it:
            items_extraidos.append({
                "item": it,
                "description": desc,
                "qty": max(0, qty)
            })

    return {
        "filename": os.path.splitext(file.filename)[0],
        "total_items": len(items_extraidos),
        "items": items_extraidos
    }


@app.post("/api/generate-pdf")
def generate_pdf(req: GeneratePdfRequest):
    """Genera el documento PDF de etiquetas en memoria adaptado a 60x30 mm o 60x95 mm."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    # Determinar tamaño efectivo y orientación (ambos formatos en orientación Portrait para rollo térmico de 60 mm)
    label_size = req.size or ("60x95" if (req.height_mm or 30.0) >= 50.0 else "60x30")
    if label_size in ("60x95", "60x90"):
        w_mm, h_mm = 60.0, 95.0
        pdf = FPDF("P", "mm", (60.0, 95.0))
    else:
        w_mm, h_mm = 60.0, 30.0
        pdf = FPDF("P", "mm", (60.0, 30.0))

    total_etiquetas = 0

    for it in req.items:
        if it.qty <= 0 or not it.item.strip():
            continue

        label_img = create_label_image(it.item, it.description, size=label_size)
        if not label_img:
            continue

        img_buf = io.BytesIO()
        label_img.save(img_buf, format="JPEG", quality=95)
        img_buf.seek(0)

        for _ in range(it.qty):
            pdf.add_page()
            pdf.image(img_buf, x=0, y=0, w=w_mm, h=h_mm)
            total_etiquetas += 1

    if total_etiquetas == 0:
        raise HTTPException(status_code=400, detail="No se generaron etiquetas válidas con cantidad mayor a 0.")

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    nombre_descarga = f"{clean_filename(req.filename or 'etiquetas')}_{label_size}.pdf"

    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={nombre_descarga}"
        }
    )


@app.post("/api/print-html")
def generate_print_html(req: GeneratePdfRequest):
    """Genera un documento HTML optimizado para impresión térmica directa en navegador sin pasar por plugin de PDF."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    label_size = req.size or ("60x95" if (req.height_mm or 30.0) >= 50.0 else "60x30")
    if label_size in ("60x95", "60x90"):
        w_mm = 60
        h_mm = 95
    else:
        w_mm = 60
        h_mm = 30

    cache_images = {}
    html_pages = []

    for it in req.items:
        if it.qty <= 0 or not it.item.strip():
            continue
        cache_key = f"{it.item}_{it.description}_{label_size}"
        if cache_key not in cache_images:
            img = create_label_image(it.item, it.description, size=label_size)
            if not img:
                continue
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            cache_images[cache_key] = f"data:image/jpeg;base64,{b64_str}"

        img_src = cache_images[cache_key]
        for _ in range(it.qty):
            html_pages.append(f'<div class="label-page"><img src="{img_src}" alt="{it.item}"></div>')

    if not html_pages:
        raise HTTPException(status_code=400, detail="No se generaron etiquetas válidas con cantidad mayor a 0.")

    pages_joined = "".join(html_pages)
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Impresión Térmica - {len(html_pages)} Etiquetas ({w_mm:.0f}x{h_mm:.0f} mm)</title>
  <style>
    @page {{
      size: {w_mm}mm {h_mm}mm;
      margin: 0mm;
    }}
    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    html, body {{
      margin: 0 !important;
      padding: 0 !important;
      background: #ffffff !important;
      width: {w_mm}mm !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      font-family: sans-serif;
    }}
    .label-page {{
      width: {w_mm}mm !important;
      height: {h_mm}mm !important;
      max-width: {w_mm}mm !important;
      max-height: {h_mm}mm !important;
      page-break-after: always !important;
      page-break-inside: avoid !important;
      break-after: page !important;
      break-inside: avoid !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      overflow: hidden !important;
      margin: 0 !important;
      padding: 0 !important;
    }}
    .label-page:last-child {{
      page-break-after: avoid !important;
      break-after: avoid !important;
    }}
    .label-page img {{
      width: {w_mm}mm !important;
      height: {h_mm}mm !important;
      display: block !important;
      object-fit: contain !important;
    }}
    @media screen {{
      body {{
        background: #e2e8f0 !important;
        padding: 20px 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 16px !important;
        min-height: 100vh !important;
        width: 100% !important;
      }}
      .no-print-bar {{
        position: sticky;
        top: 0;
        z-index: 999;
        background: #1e293b;
        color: #ffffff;
        padding: 10px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 10px;
      }}
      .no-print-bar button {{
        background: #10b981;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
        font-size: 14px;
      }}
      .no-print-bar button:hover {{
        background: #059669;
      }}
      .label-page {{
        background: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        border-radius: 4px;
      }}
    }}
    @media print {{
      .no-print-bar {{
        display: none !important;
      }}
    }}
  </style>
</head>
<body>
  <div class="no-print-bar">
    <span>Listo para imprimir <strong>{len(html_pages)} etiqueta(s)</strong> ({w_mm:.0f}x{h_mm:.0f} mm)</span>
    <button onclick="window.print()">🖨️ Imprimir Ahora</button>
    <button onclick="window.close()" style="background:#64748b;">Cerrar</button>
  </div>
  {pages_joined}
</body>
</html>"""

    return Response(content=html_content, media_type="text/html; charset=utf-8")


@app.post("/api/download-zip")
def download_zip(req: GeneratePdfRequest):
    """Descarga todas las imágenes JPEG únicas de las etiquetas en un archivo .zip."""
    if not req.items:
        raise HTTPException(status_code=400, detail="No hay ítems para comprimir")

    label_size = req.size or ("60x95" if (req.height_mm or 30.0) >= 50.0 else "60x30")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for it in req.items:
            if not it.item.strip():
                continue
            label_img = create_label_image(it.item, it.description, size=label_size)
            if label_img:
                img_buf = io.BytesIO()
                label_img.save(img_buf, format="JPEG", quality=95)
                filename = f"{clean_filename(it.item)}_{label_size}.jpg"
                zip_file.writestr(filename, img_buf.getvalue())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={clean_filename(req.filename or 'etiquetas')}.zip"
        }
    )


# ==========================================
# RUTAS DE PWA / SPA / STATIC
# ==========================================
@app.get("/manifest.json")
def get_manifest():
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json no encontrado")


@app.get("/service-worker.js")
def get_service_worker():
    sw_path = os.path.join(STATIC_DIR, "js", "service-worker.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="service-worker.js no encontrado")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_spa():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SPA index.html no encontrado"}
