import io
import os
import re
import zipfile
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

# Inicializar FastAPI
app = FastAPI(
    title="Generador de Etiquetas de Depósito",
    description="API y SPA / PWA para generar etiquetas con código de barras e impresión térmica en PDF",
    version="2.0.0"
)

# Rutas base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Carga de fuentes segura
def get_font(font_name: str, size: int) -> ImageFont.ImageFont:
    font_path = os.path.join(FONTS_DIR, font_name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    # Fallback al sistema operativo
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


def generate_barcode_image(item: str) -> Optional[Image.Image]:
    """Genera la imagen del código de barras Code39 recortado al 70% de altura."""
    try:
        item_str = str(item).strip().upper()
        if not item_str:
            return None

        code39 = barcode.get_barcode_class('code39')
        writer = ImageWriter()
        writer.set_options({"write_text": True})

        bc = code39(item_str, writer=writer, add_checksum=False)
        
        # Generar en memoria sin escribir en disco
        fp = io.BytesIO()
        bc.write(fp)
        fp.seek(0)

        with Image.open(fp) as raw_img:
            img_rgb = raw_img.convert("RGB")
            width, height = img_rgb.size
            # Recortar texto inferior (quedarse con el 70% superior)
            img_cropped = img_rgb.crop((0, 0, width, int(height * 0.70)))
            return img_cropped.resize((595, 120))
    except Exception as e:
        print(f"Error generando código de barras para '{item}': {e}")
        return None


def create_label_image(item: str, description: str) -> Optional[Image.Image]:
    """Genera la imagen completa de la etiqueta 600x300 px."""
    bc_img = generate_barcode_image(item)
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
    item_text = str(item).upper().strip()
    bbox_item = draw.textbbox((0, 0), item_text, font=font_item)
    item_w = bbox_item[2] - bbox_item[0]
    item_x = (ancho - item_w) // 2
    item_y = bc_y + 120 - 15
    draw.text((item_x, item_y), item_text, fill='black', font=font_item)

    # Descripción debajo del ítem
    desc_text = str(description).upper().strip()
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
    width_mm: Optional[float] = 60.0
    height_mm: Optional[float] = 30.0


# ==========================================
# ENDPOINTS API
# ==========================================
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Generador de Etiquetas Web", "version": "2.0.0"}


@app.get("/api/preview-label")
def preview_label(item: str = Query("012345"), description: str = Query("EJEMPLO DE DESCRIPCIÓN")):
    """Devuelve la imagen JPEG generada en vivo para previsualización."""
    img = create_label_image(item, description)
    if not img:
        raise HTTPException(status_code=400, detail="No se pudo generar la etiqueta")

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="image/jpeg")


@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    """Parsea el archivo Excel (.xlsx o .xls) manteniendo ceros a la izquierda."""
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

    # Buscar primera columna con valor que comience con '0'
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
    """Genera el documento PDF de etiquetas (por defecto 60x30 mm) en memoria."""
    if not req.items:
        raise HTTPException(status_code=400, detail="La lista de ítems está vacía")

    pdf = FPDF("P", "mm", (req.width_mm, req.height_mm))

    total_etiquetas = 0
    # Generar en memoria
    for it in req.items:
        if it.qty <= 0 or not it.item.strip():
            continue

        label_img = create_label_image(it.item, it.description)
        if not label_img:
            continue

        img_buf = io.BytesIO()
        label_img.save(img_buf, format="JPEG", quality=95)
        img_buf.seek(0)

        for _ in range(it.qty):
            pdf.add_page()
            pdf.image(img_buf, x=0, y=0, w=req.width_mm, h=req.height_mm)
            total_etiquetas += 1

    if total_etiquetas == 0:
        raise HTTPException(status_code=400, detail="No se generaron etiquetas válidas con cantidad mayor a 0.")

    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    nombre_descarga = f"{clean_filename(req.filename or 'etiquetas')}.pdf"

    return StreamingResponse(
        pdf_output,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={nombre_descarga}"
        }
    )


@app.post("/api/download-zip")
def download_zip(req: GeneratePdfRequest):
    """Descarga todas las imágenes JPEG únicas de las etiquetas en un archivo .zip."""
    if not req.items:
        raise HTTPException(status_code=400, detail="No hay ítems para comprimir")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for it in req.items:
            if not it.item.strip():
                continue
            label_img = create_label_image(it.item, it.description)
            if label_img:
                img_buf = io.BytesIO()
                label_img.save(img_buf, format="JPEG", quality=95)
                filename = f"{clean_filename(it.item)}.jpg"
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
