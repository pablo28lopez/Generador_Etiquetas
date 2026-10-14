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
from PIL import Image, ImageDraw, ImageFont, ImageOps
from fpdf import FPDF

# Motor de comandos directos Brother QL (RAW)
try:
    from brother_raw import (
        list_installed_printers,
        find_brother_printer,
        send_raw_to_printer,
        convert_images_to_brother_raster,
        is_brother_usb_connected,
        BROTHER_QL_AVAILABLE
    )
except ImportError:
    try:
        from web.brother_raw import (
            list_installed_printers,
            find_brother_printer,
            send_raw_to_printer,
            convert_images_to_brother_raster,
            is_brother_usb_connected,
            BROTHER_QL_AVAILABLE
        )
    except ImportError:
        BROTHER_QL_AVAILABLE = False
        def list_installed_printers(): return []
        def find_brother_printer(preferred_name=None): return None
        def is_brother_usb_connected(): return False
        def send_raw_to_printer(printer_name, raw_data, doc_name="Etiquetas"): raise RuntimeError("brother_raw no disponible")
        def convert_images_to_brother_raster(*args, **kwargs): raise RuntimeError("brother_raw no disponible")

# Inicializar FastAPI
app = FastAPI(
    title="Generador de Etiquetas de Depósito",
    description="API y SPA / PWA para generar etiquetas con código de barras e impresión térmica en PDF o Comandos RAW Brother QL",
    version="2.6.0"
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


# Carga de fuentes segura (Arial y Arial Black)
def get_font(font_name: str, size: int) -> ImageFont.ImageFont:
    fn_lower = font_name.lower()
    if "black" in fn_lower or "blk" in fn_lower:
        target_name = "ariblk.ttf"
    elif "bd" in fn_lower or "bold" in fn_lower:
        target_name = "arialbd.ttf"
    else:
        target_name = "arial.ttf"

    candidate_paths = [
        os.path.join(FONTS_DIR, font_name),
        os.path.join(FONTS_DIR, target_name),
        os.path.join("C:\\Windows\\Fonts", font_name),
        os.path.join("C:\\Windows\\Fonts", target_name),
        os.path.join(BASE_DIR, font_name),
        os.path.join(BASE_DIR, target_name),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.truetype(target_name, size)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def clean_filename(name: str) -> str:
    """Sanitiza nombres de ítems para nombres de archivos."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(name).strip())


def get_font_path(name: str = "arial.ttf") -> Optional[str]:
    """Obtiene la ruta física del archivo de fuente."""
    candidate_paths = [
        os.path.join(FONTS_DIR, name),
        os.path.join(STATIC_DIR, "fonts", name),
        os.path.join(BASE_DIR, name),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", name),
        name
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return None


def generate_barcode_image(item: str, target_size: Tuple[int, int] = (560, 110)) -> Image.Image:
    """Genera la imagen del código de barras (Code39 o Code128) 100% nítida y blindada en memoria."""
    item_str = str(item).strip().upper() if item else "012345"
    if not item_str:
        item_str = "012345"

    writer = ImageWriter()
    writer._callbacks["paint_text"] = None
    fp_arial = get_font_path("arial.ttf")
    if fp_arial and os.path.exists(fp_arial):
        writer.font_path = fp_arial

    bc = None
    # 1. Probar Code39 (estándar depósito)
    try:
        code39 = barcode.get_barcode_class('code39')
        bc = code39(item_str, writer=writer, add_checksum=False)
    except Exception:
        # 2. Si falla por caracteres especiales (_ # / etc.), usar Code128
        try:
            code128 = barcode.get_barcode_class('code128')
            bc = code128(item_str, writer=writer)
        except Exception:
            # 3. Sanitizar caracteres a sólo alfanuméricos
            clean_str = re.sub(r'[^A-Z0-9]', '', item_str) or "012345"
            try:
                code39 = barcode.get_barcode_class('code39')
                bc = code39(clean_str, writer=writer, add_checksum=False)
            except Exception:
                pass

    if bc is not None:
        try:
            fp = io.BytesIO()
            bc.write(fp, options={"write_text": False})
            fp.seek(0)
            with Image.open(fp) as raw_img:
                raw_l = raw_img.convert("L")
                inv = ImageOps.invert(raw_l)
                bbox = inv.getbbox()
                if bbox:
                    qz = 8
                    bars = raw_l.crop((max(0, bbox[0] - qz), bbox[1], min(raw_l.width, bbox[2] + qz), bbox[3]))
                else:
                    bars = raw_l
                return bars.resize(target_size, Image.Resampling.NEAREST).convert("RGB")
        except Exception as e:
            print(f"Error procesando imagen de barras para '{item_str}': {e}")

    # Fallback infalible: código de barras sintético
    dummy = Image.new('RGB', target_size, 'white')
    d_draw = ImageDraw.Draw(dummy)
    for x in range(15, target_size[0] - 15, 6):
        d_draw.line([(x, 10), (x, target_size[1] - 10)], fill='black', width=3)
    return dummy


def create_label_image(item: str, description: str, size: str = "60x30") -> Optional[Image.Image]:
    """Genera la imagen completa de la etiqueta térmica:
       - 60x30 mm: 600x300 px (horizontal estándar Brother DK-11209 / DK-22205)
       - 60x95 mm (o 62x100 mm): 1000x620 px (horizontal extendida Brother DK-11202 / DK-22205)
       100% fuentes Arial / Arial Black para ID, fondo blanco con bordes limpios.
    """
    item_text = str(item).upper().strip() if item else "012345"
    if not item_text:
        item_text = "012345"
    desc_text = str(description).upper().strip() if description else "EJEMPLO DE ETIQUETA"
    if not desc_text:
        desc_text = "EJEMPLO DE ETIQUETA"

    if size in ("60x95", "60x90", "62x100"):
        # Formato Grande Horizontal 100x62 mm (1000x620 px) - Formato institucional DLS Archer Depósito Neuquén
        w, h = 1000, 620
        label = Image.new('RGB', (w, h), 'white')
        draw = ImageDraw.Draw(label)
        margin_x = 35

        # 1. Logo DLS Archer (arriba a la izquierda) y al lado DLS DEPOSITO NEUQUEN
        logo_path = os.path.join(STATIC_DIR, "img", "logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(BASE_DIR, "logo.png")

        lh = 130
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                lw = int(logo.width * (lh / logo.height))
                logo_resized = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                label.paste(logo_resized, (margin_x, 25), logo_resized)
                pill_left = margin_x + lw + 20
            except Exception as e:
                print(f"Error cargando logo en etiqueta 60x95: {e}")
                pill_left = margin_x
        else:
            pill_left = margin_x

        pill_right = w - margin_x
        pill_top = 25
        pill_bottom = 25 + lh

        # Recuadro redondeado sin relleno (borde negro, fondo blanco)
        draw.rounded_rectangle([pill_left, pill_top, pill_right, pill_bottom], radius=18, outline='black', width=4, fill='white')

        # Texto DLS DEPOSITO NEUQUEN en Arial Bold negro sólido (tamaño 52)
        font_header = get_font("arialbd.ttf", 52)
        header_text = "DLS DEPOSITO NEUQUEN"
        hb = draw.textbbox((0, 0), header_text, font=font_header)
        hw = hb[2] - hb[0]
        hx = pill_left + (pill_right - pill_left - hw) // 2
        hy = pill_top + (pill_bottom - pill_top - (hb[3] - hb[1])) // 2 - 4
        draw.text((hx, hy), header_text, font=font_header, fill='black')

        # 2. Recuadro del Código de Ítem (Fondo NEGRO sólido con texto en BLANCO en Arial Black maximizado y perfectamente centrado)
        code_top = 175
        code_bottom = 320
        box_h = code_bottom - code_top
        box_w = w - 2 * margin_x
        draw.rectangle([margin_x, code_top, w - margin_x, code_bottom], fill='black')

        # Buscar el mayor tamaño de fuente posible dejando el margen mínimo (14-18 px)
        it_size = 150
        font_item = get_font("ariblk.ttf", it_size)
        ib = draw.textbbox((0, 0), item_text, font=font_item)
        tw = ib[2] - ib[0]
        th = ib[3] - ib[1]
        while (tw > (box_w - 28) or th > (box_h - 22)) and it_size > 36:
            it_size -= 2
            font_item = get_font("ariblk.ttf", it_size)
            ib = draw.textbbox((0, 0), item_text, font=font_item)
            tw = ib[2] - ib[0]
            th = ib[3] - ib[1]

        # Centrado matemático exacto compensando offsets internos de la fuente (márgenes idénticos arriba/abajo y lados)
        ix = margin_x + (box_w - tw) // 2 - ib[0]
        iy = code_top + (box_h - th) // 2 - ib[1]
        draw.text((ix, iy), item_text, font=font_item, fill='white')

        # 3. Cuadro inferior con Descripción Enmarcado (SIN RELLENO - Fondo blanco, borde negro, texto Arial Bold)
        desc_top = 340
        desc_bottom = 595
        draw.rectangle([margin_x, desc_top, w - margin_x, desc_bottom], outline='black', width=4, fill='white')

        box_w = w - 2 * margin_x - 40
        box_h = desc_bottom - desc_top

        font_size = 52
        font_desc = get_font("arialbd.ttf", font_size)
        lines = [desc_text]

        if draw.textbbox((0, 0), desc_text, font=font_desc)[2] > box_w:
            font_size = 42
            font_desc = get_font("arialbd.ttf", font_size)
            lines = textwrap.wrap(desc_text, width=34)
            if len(lines) > 2:
                font_size = 34
                font_desc = get_font("arialbd.ttf", font_size)
                lines = textwrap.wrap(desc_text, width=42)[:3]

        line_h = font_size + 14
        total_text_h = len(lines) * line_h
        start_y = desc_top + (box_h - total_text_h) // 2

        for i, line in enumerate(lines):
            bb = draw.textbbox((0, 0), line, font=font_desc)
            lw_text = bb[2] - bb[0]
            lx = margin_x + (w - 2 * margin_x - lw_text) // 2
            draw.text((lx, start_y + i * line_h), line, font=font_desc, fill='black')

        return label

    else:
        # Formato estándar 62x29 mm (620x290 px) Brother DK-11209 / Cinta continua 62mm
        # Contenido 100% centrado horizontal y verticalmente con MÁRGENES MÍNIMOS ABSOLUTOS (~6-12 px)
        ancho, alto = 620, 290
        label = Image.new('RGB', (ancho, alto), 'white')
        draw = ImageDraw.Draw(label)

        # 1. Código de Ítem en Arial Bold maximizado (tamaño base 94 pt con auto-ajuste rápido)
        it_size = 94
        font_item = get_font("arialbd.ttf", it_size)
        ib = draw.textbbox((0, 0), item_text, font=font_item)
        iw = ib[2] - ib[0]
        while iw > (ancho - 14) and it_size > 36:
            it_size -= 2
            font_item = get_font("arialbd.ttf", it_size)
            ib = draw.textbbox((0, 0), item_text, font=font_item)
            iw = ib[2] - ib[0]
        ih = ib[3] - ib[1]

        # 2. Descripción en Arial Regular maximizada (tamaño base 28 pt)
        desc_size = 28
        font_desc = get_font("arial.ttf", desc_size)
        db = draw.textbbox((0, 0), desc_text, font=font_desc)
        dw = db[2] - db[0]
        lines = [desc_text]
        if dw > (ancho - 14):
            desc_size = 24
            font_desc = get_font("arial.ttf", desc_size)
            db = draw.textbbox((0, 0), desc_text, font=font_desc)
            dw = db[2] - db[0]
            if dw > (ancho - 14):
                desc_size = 21
                font_desc = get_font("arial.ttf", desc_size)
                lines = textwrap.wrap(desc_text, width=44)[:2]

        line_bboxes = [draw.textbbox((0, 0), l, font=font_desc) for l in lines]
        line_heights = [b[3] - b[1] for b in line_bboxes]
        line_sp = 3
        total_desc_ink_h = sum(line_heights) + (len(lines) - 1) * line_sp

        # 3. Código de barras ultra nítido ocupando el ancho completo (608 px de 620 px)
        gap1 = 7
        gap2 = 5
        target_margin = 6
        available_bc_h = alto - (2 * target_margin) - (gap1 + ih + gap2 + total_desc_ink_h)
        bc_h = max(95, min(165, available_bc_h))
        bc_w = min(608, ancho - 12)

        bc_img = generate_barcode_image(item_text, target_size=(bc_w, bc_h))

        total_ink_h = bc_h + gap1 + ih + gap2 + total_desc_ink_h
        start_y = (alto - total_ink_h) // 2

        # Pegar código de barras centrado
        bc_y = start_y
        bc_x = (ancho - bc_w) // 2
        label.paste(bc_img, (bc_x, bc_y))

        # Texto del Ítem centrado matemáticamente
        item_y = bc_y + bc_h + gap1 - ib[1]
        item_x = (ancho - iw) // 2 - ib[0]
        draw.text((item_x, item_y), item_text, font=font_item, fill='black')

        # Descripción centrada línea por línea
        curr_desc_y = bc_y + bc_h + gap1 + ih + gap2
        for i, line in enumerate(lines):
            lb = line_bboxes[i]
            lw = lb[2] - lb[0]
            lh = line_heights[i]
            lx = (ancho - lw) // 2 - lb[0]
            ly = curr_desc_y - lb[1]
            draw.text((lx, ly), line, font=font_desc, fill='black')
            curr_desc_y += lh + line_sp

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


class PrintBrotherRawRequest(BaseModel):
    items: List[ItemRequest]
    size: Optional[str] = "60x30"
    printer_name: Optional[str] = None
    roll_type: Optional[str] = "auto"


# ==========================================
# ENDPOINTS API - GENERAL Y PREVIEW
# ==========================================
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Generador de Etiquetas Web",
        "version": app.version,
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
    """Genera el documento PDF de etiquetas en memoria adaptado exactamente a las medidas térmicas Brother QL (62x29 mm y 62x100 mm)."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    # Determinar tamaño efectivo y orientación (Brother DK: 62x100 mm grande o 62x29 mm estándar)
    label_size = req.size or ("60x95" if (req.height_mm or 30.0) >= 50.0 else "60x30")
    if label_size in ("60x95", "60x90", "62x100"):
        w_mm, h_mm = 100.0, 62.0
        pdf = FPDF("L", "mm", (62.0, 100.0))
    else:
        w_mm, h_mm = 62.0, 29.0
        pdf = FPDF("L", "mm", (29.0, 62.0))

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
    """Genera un documento HTML optimizado para impresión térmica directa en navegador en Brother QL-800."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    label_size = req.size or ("60x95" if (req.height_mm or 30.0) >= 50.0 else "60x30")
    if label_size in ("60x95", "60x90", "62x100"):
        w_mm = 100
        h_mm = 62
        page_size_css = "100mm 62mm"
        paper_badge = "62mm x 100mm (DK-11202 / Rollo 62mm)"
    else:
        w_mm = 62
        h_mm = 29
        page_size_css = "62mm 29mm"
        paper_badge = "62mm x 29mm (DK-11209 / Rollo 62mm)"

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
  <title>Impresión Térmica Brother QL - {len(html_pages)} Etiquetas ({w_mm}x{h_mm} mm)</title>
  <script>
    window.addEventListener('load', function() {{
      var ua = navigator.userAgent;
      var bName = "Navegador Web";
      if (ua.indexOf("Edg/") !== -1) bName = "Microsoft Edge (Seteo activo)";
      else if (ua.indexOf("Chrome") !== -1) bName = "Google Chrome (Seteo activo)";
      var bEl = document.getElementById("detected-browser-name");
      if (bEl) bEl.textContent = bName;

      setTimeout(function() {{
        try {{
          window.focus();
          window.print();
        }} catch (e) {{
          console.warn('Auto print:', e);
        }}
      }}, 400);
    }});
  </script>
  <style>
    @page {{
      size: {page_size_css};
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
      font-family: Arial, sans-serif;
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
      object-fit: fill !important;
    }}
    @media screen {{
      body {{
        background: #f1f5f9 !important;
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
        background: #0f172a;
        color: #ffffff;
        padding: 12px 24px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        max-width: 900px;
        width: 95%;
        margin-bottom: 12px;
        border: 1px solid #334155;
      }}
      .bar-info {{
        display: flex;
        flex-direction: column;
        gap: 4px;
      }}
      .bar-title {{
        font-weight: 700;
        font-size: 14px;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .bar-badges {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        font-size: 11px;
      }}
      .badge {{
        background: #1e293b;
        color: #cbd5e1;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid #475569;
      }}
      .badge strong {{
        color: #38bdf8;
      }}
      .bar-buttons {{
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .btn-print {{
        background: #10b981;
        color: white;
        border: none;
        padding: 8px 18px;
        border-radius: 8px;
        font-weight: 700;
        cursor: pointer;
        font-size: 13px;
        box-shadow: 0 2px 6px rgba(16,185,129,0.3);
      }}
      .btn-print:hover {{
        background: #059669;
      }}
      .btn-close {{
        background: #475569;
        color: white;
        border: none;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        font-size: 13px;
      }}
      .btn-close:hover {{
        background: #64748b;
      }}
      .label-page {{
        background: white;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
        border-radius: 4px;
      }}
    }}
    @media print {{
      @page {{
        size: {page_size_css};
        margin: 0 !important;
      }}
      *, *::before, *::after {{
        box-sizing: border-box !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}
      html, body {{
        width: {w_mm}mm !important;
        height: {h_mm}mm !important;
        margin: 0 !important;
        padding: 0 !important;
        background: #ffffff !important;
        overflow: hidden !important;
      }}
      .label-page {{
        width: {w_mm}mm !important;
        height: {h_mm}mm !important;
        max-width: {w_mm}mm !important;
        max-height: {h_mm}mm !important;
        margin: 0 !important;
        padding: 0 !important;
        page-break-after: always !important;
        break-after: page !important;
        page-break-inside: avoid !important;
        break-inside: avoid !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
        box-shadow: none !important;
        border-radius: 0 !important;
      }}
      .label-page:last-child {{
        page-break-after: avoid !important;
        break-after: avoid !important;
      }}
      .label-page img {{
        width: {w_mm}mm !important;
        height: {h_mm}mm !important;
        max-width: {w_mm}mm !important;
        max-height: {h_mm}mm !important;
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
        object-fit: fill !important;
      }}
      .no-print-bar {{
        display: none !important;
      }}
    }}
  </style>
</head>
<body>
  <div class="no-print-bar">
    <div class="bar-info">
      <div class="bar-title">
        <span>🖨️ Impresión Térmica Brother QL-800</span>
        <span style="font-size: 12px; color: #a7f3d0; font-weight: normal;">({len(html_pages)} etiqueta{"" if len(html_pages)==1 else "s"})</span>
      </div>
      <div class="bar-badges">
        <span class="badge">Navegador: <strong id="detected-browser-name">Chrome / Edge</strong></span>
        <span class="badge">Papel: <strong>{paper_badge}</strong></span>
        <span class="badge">Márgenes: <strong>0mm (Automático)</strong></span>
        <span class="badge">Orientación: <strong>Horizontal</strong></span>
      </div>
    </div>
    <div class="bar-buttons">
      <button class="btn-print" onclick="window.print()">🖨️ Imprimir (Ctrl + P)</button>
      <button class="btn-close" onclick="window.close()">Cerrar</button>
    </div>
  </div>
  {pages_joined}
  <script>
    window.addEventListener('load', function() {{
      setTimeout(function() {{
        try {{ window.print(); }} catch(e) {{}}
      }}, 350);
    }});
  </script>
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
# ENDPOINTS DE IMPRESIÓN DIRECTA BROTHER QL (COMANDOS NATIVOS RAW)
# ==========================================
@app.get("/api/printers")
def get_printers():
    """Retorna las impresoras instaladas en Windows y si hay una Brother QL conectada."""
    all_p = list_installed_printers()
    detected = find_brother_printer()
    usb_ok = is_brother_usb_connected()
    import socket
    host_name = os.environ.get("COMPUTERNAME") or socket.gethostname()
    return {
        "all_printers": all_p,
        "detected_brother": detected,
        "brother_found": detected is not None,
        "usb_physically_connected": usb_ok,
        "host_name": host_name,
        "raw_engine_ready": BROTHER_QL_AVAILABLE
    }


@app.post("/api/print-brother-raw")
def print_brother_raw(req: PrintBrotherRawRequest):
    """Envía comandos de impresión binarios nativos (Brother Raster) directo a la Brother QL-800 sin usar drivers ni diálogos."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    # Determinar impresora
    target_printer = req.printer_name or find_brother_printer()
    if not target_printer:
        printers_list = list_installed_printers()
        raise HTTPException(
            status_code=400,
            detail=f"No se detectó ninguna impresora Brother QL conectada por USB en este equipo. Impresoras Windows detectadas: {', '.join(printers_list) if printers_list else 'Ninguna'}. Conecta la Brother QL-800 por USB o selecciona una impresora."
        )

    label_size = req.size or "60x30"

    # Generar imágenes de etiquetas
    images_to_print = []
    for it in req.items:
        if it.qty <= 0 or not it.item.strip():
            continue
        label_img = create_label_image(it.item, it.description, size=label_size)
        if not label_img:
            continue
        for _ in range(it.qty):
            images_to_print.append(label_img)

    if not images_to_print:
        raise HTTPException(status_code=400, detail="No se generaron etiquetas válidas con cantidad mayor a 0.")

    # Convertir a comandos binarios RAW de Brother QL
    try:
        raw_bytes = convert_images_to_brother_raster(
            images=images_to_print,
            size=label_size,
            roll_type="continuous" if (not req.roll_type or req.roll_type == "auto") else req.roll_type,
            model="QL-800",
            cut_each=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando comandos raster Brother QL: {str(e)}")

    # Enviar al spooler en modo RAW
    try:
        bytes_sent = send_raw_to_printer(target_printer, raw_bytes, doc_name=f"Etiquetas ({len(images_to_print)})")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando comandos a '{target_printer}': {str(e)}")

    return {
        "status": "success",
        "message": f"¡Éxito! Se enviaron {len(images_to_print)} etiqueta(s) directamente a '{target_printer}' mediante comandos RAW (sin driver).",
        "printer": target_printer,
        "total_labels": len(images_to_print),
        "bytes_sent": bytes_sent
    }


@app.post("/api/download-prn")
def download_prn(req: PrintBrotherRawRequest):
    """Descarga el archivo binario de comandos nativos .prn de Brother QL para depuración o copia directa."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    label_size = req.size or "60x30"
    images_to_print = []
    for it in req.items:
        if it.qty <= 0 or not it.item.strip():
            continue
        label_img = create_label_image(it.item, it.description, size=label_size)
        if not label_img:
            continue
        for _ in range(it.qty):
            images_to_print.append(label_img)

    if not images_to_print:
        raise HTTPException(status_code=400, detail="No se generaron etiquetas válidas.")

    raw_bytes = convert_images_to_brother_raster(
        images=images_to_print,
        size=label_size,
        roll_type=req.roll_type or "auto",
        model="QL-800",
        cut_each=True
    )

    return Response(
        content=raw_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=etiquetas_brother_{label_size}.prn"
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
