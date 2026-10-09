import io
import os
import re
import sys
import tempfile
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Tuple

import pandas as pd
import openpyxl
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageOps
from fpdf import FPDF
import textwrap

# ==========================================
# RUTAS DE RECURSOS (COMPATIBLE PYINSTALLER)
# ==========================================
def resource_path(relative_path: str) -> str:
    """Obtiene la ruta absoluta al recurso, compatible con desarrollo y PyInstaller .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_data_file_path(filename: str = "DATOS_DEPO.xlsx") -> str:
    """
    Obtiene la ruta al archivo de datos editable.
    Si se ejecuta como .exe empaquetado, busca el archivo junto al ejecutable.
    Si no existe allí, lo copia desde el recurso empaquetado para permitir escritura persistente.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        external_path = os.path.join(exe_dir, filename)
        if not os.path.exists(external_path):
            bundled_path = resource_path(filename)
            if os.path.exists(bundled_path):
                try:
                    import shutil
                    shutil.copy2(bundled_path, external_path)
                except Exception as e:
                    print(f"No se pudo copiar datos iniciales: {e}")
                    return bundled_path
        return external_path
    else:
        # En desarrollo
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(base_dir, filename)
        if os.path.exists(local_path):
            return local_path
        web_data = os.path.join(base_dir, "web", "data", filename)
        if os.path.exists(web_data):
            return web_data
        return local_path


# ==========================================
# DIRECTORIOS DE TRABAJO
# ==========================================
descargas_path = os.path.join(os.path.expanduser("~"), "Downloads")
directorio_etiquetas = os.path.join(descargas_path, "Etiquetas")
directorio_pdf = os.path.join(descargas_path, "PDFs")
directorio_temp = os.path.join(tempfile.gettempdir(), "GeneradorEtiquetas_Temp")

os.makedirs(directorio_etiquetas, exist_ok=True)
os.makedirs(directorio_pdf, exist_ok=True)
os.makedirs(directorio_temp, exist_ok=True)


# ==========================================
# TIPOGRAFÍA Y FUENTES (100% ARIAL)
# ==========================================
def limpiar_nombre_archivo(nombre: str) -> str:
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(nombre).strip())


def obtener_fuente(nombre_fuente: str, tamano: int) -> ImageFont.ImageFont:
    """Carga fuentes de la familia Arial y Arial Black."""
    fn_lower = nombre_fuente.lower()
    if "black" in fn_lower or "blk" in fn_lower:
        target_name = "ariblk.ttf"
    elif "bd" in fn_lower or "bold" in fn_lower:
        target_name = "arialbd.ttf"
    else:
        target_name = "arial.ttf"

    candidate_paths = [
        resource_path(nombre_fuente),
        resource_path(target_name),
        resource_path(os.path.join("fonts", target_name)),
        resource_path(os.path.join("web", "fonts", target_name)),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", nombre_fuente),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", target_name),
        target_name,
    ]
    for ruta in candidate_paths:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano)
            except Exception:
                pass
    try:
        return ImageFont.truetype(target_name, tamano)
    except Exception:
        try:
            return ImageFont.load_default(size=tamano)
        except TypeError:
            return ImageFont.load_default()


def obtener_ruta_fuente(nombre_fuente: str = "arial.ttf") -> Optional[str]:
    """Busca la ruta física de la fuente para incrustación segura."""
    candidate_paths = [
        resource_path(nombre_fuente),
        resource_path(os.path.join("fonts", nombre_fuente)),
        resource_path(os.path.join("web", "fonts", nombre_fuente)),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", nombre_fuente),
        nombre_fuente,
    ]
    for ruta in candidate_paths:
        if os.path.exists(ruta):
            return ruta
    return None


# ==========================================
# GENERACIÓN DE CÓDIGO DE BARRAS Y ETIQUETAS
# ==========================================
def generar_imagen_codigo_barras(item: str, target_size: Tuple[int, int] = (560, 110)) -> Image.Image:
    """Genera la imagen del código de barras (Code39 o Code128) 100% nítida y blindada para PyInstaller portable."""
    item_str = str(item).strip().upper() if item else "012345"
    if not item_str:
        item_str = "012345"

    writer = ImageWriter()
    # CRÍTICO PARA PORTABLE (.EXE): Desactivar callback de texto para no depender de DejaVuSansMono.ttf
    writer._callbacks["paint_text"] = None
    ruta_arial = obtener_ruta_fuente("arial.ttf")
    if ruta_arial and os.path.exists(ruta_arial):
        writer.font_path = ruta_arial

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

    # Fallback si falla todo
    dummy = Image.new('RGB', target_size, 'white')
    d_draw = ImageDraw.Draw(dummy)
    for x in range(15, target_size[0] - 15, 6):
        d_draw.line([(x, 10), (x, target_size[1] - 10)], fill='black', width=3)
    return dummy


def crear_imagen_etiqueta(item: str, description: str, size: str = "60x30") -> Optional[Image.Image]:
    """
    Genera la imagen PIL de la etiqueta térmica:
    - 60x30 mm: 600x300 px (Brother DK-11209 62x29 mm / continuo 62mm)
    - 60x95 mm: 1000x620 px (Brother DK-11202 62x100 mm / continuo 62mm)
    100% Arial / Arial Black para el ID, fondo blanco con bordes limpios.
    """
    item_text = str(item).upper().strip() if item else "012345"
    if not item_text:
        item_text = "012345"
    desc_text = str(description).upper().strip() if description else "EJEMPLO DE ETIQUETA"
    if not desc_text:
        desc_text = "EJEMPLO DE ETIQUETA"

    if size in ("60x95", "60x90", "62x100"):
        # Formato Grande Horizontal 100x62 mm (1000x620 px)
        w, h = 1000, 620
        label = Image.new('RGB', (w, h), 'white')
        draw = ImageDraw.Draw(label)
        margin_x = 35

        # 1. Logo DLS Archer y Recuadro DLS DEPOSITO NEUQUEN
        logo_path = resource_path("logo.png")
        if not os.path.exists(logo_path):
            logo_path = resource_path(os.path.join("web", "static", "img", "logo.png"))

        lh = 130
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                lw = int(logo.width * (lh / logo.height))
                logo_resized = logo.resize((lw, lh), Image.Resampling.LANCZOS)
                label.paste(logo_resized, (margin_x, 25), logo_resized)
                pill_left = margin_x + lw + 20
            except Exception as e:
                print(f"Error cargando logo: {e}")
                pill_left = margin_x
        else:
            pill_left = margin_x

        pill_right = w - margin_x
        pill_top = 25
        pill_bottom = 25 + lh

        # Recuadro redondeado sin relleno
        draw.rounded_rectangle([pill_left, pill_top, pill_right, pill_bottom], radius=18, outline='black', width=4, fill='white')

        # Texto DLS DEPOSITO NEUQUEN en Arial Bold negro sólido (tamaño 52)
        font_header = obtener_fuente("arialbd.ttf", 52)
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
        font_item = obtener_fuente("ariblk.ttf", it_size)
        ib = draw.textbbox((0, 0), item_text, font=font_item)
        tw = ib[2] - ib[0]
        th = ib[3] - ib[1]
        while (tw > (box_w - 28) or th > (box_h - 22)) and it_size > 36:
            it_size -= 2
            font_item = obtener_fuente("ariblk.ttf", it_size)
            ib = draw.textbbox((0, 0), item_text, font=font_item)
            tw = ib[2] - ib[0]
            th = ib[3] - ib[1]

        # Centrado matemático exacto compensando offsets internos de la fuente
        ix = margin_x + (box_w - tw) // 2 - ib[0]
        iy = code_top + (box_h - th) // 2 - ib[1]
        draw.text((ix, iy), item_text, font=font_item, fill='white')

        # 3. Cuadro inferior de Descripción (SIN RELLENO - Fondo blanco con borde negro)
        desc_top = 340
        desc_bottom = 595
        draw.rectangle([margin_x, desc_top, w - margin_x, desc_bottom], outline='black', width=4, fill='white')

        box_w = w - 2 * margin_x - 40
        box_h = desc_bottom - desc_top

        font_size = 52
        font_desc = obtener_fuente("arialbd.ttf", font_size)
        lines = [desc_text]

        if draw.textbbox((0, 0), desc_text, font=font_desc)[2] > box_w:
            font_size = 42
            font_desc = obtener_fuente("arialbd.ttf", font_size)
            lines = textwrap.wrap(desc_text, width=34)
            if len(lines) > 2:
                font_size = 34
                font_desc = obtener_fuente("arialbd.ttf", font_size)
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
        # Contenido 100% centrado horizontal y verticalmente con márgenes mínimos equilibrados
        ancho, alto = 620, 290
        label = Image.new('RGB', (ancho, alto), 'white')
        draw = ImageDraw.Draw(label)

        # 1. Código de Ítem en Arial Bold maximizado (tamaño base 94 pt con auto-ajuste rápido)
        it_size = 94
        font_item = obtener_fuente("arialbd.ttf", it_size)
        ib = draw.textbbox((0, 0), item_text, font=font_item)
        iw = ib[2] - ib[0]
        while iw > (ancho - 14) and it_size > 36:
            it_size -= 2
            font_item = obtener_fuente("arialbd.ttf", it_size)
            ib = draw.textbbox((0, 0), item_text, font=font_item)
            iw = ib[2] - ib[0]
        ih = ib[3] - ib[1]

        # 2. Descripción en Arial Regular maximizada (tamaño base 28 pt)
        desc_size = 28
        font_desc = obtener_fuente("arial.ttf", desc_size)
        db = draw.textbbox((0, 0), desc_text, font=font_desc)
        dw = db[2] - db[0]
        lines = [desc_text]
        if dw > (ancho - 14):
            desc_size = 24
            font_desc = obtener_fuente("arial.ttf", desc_size)
            db = draw.textbbox((0, 0), desc_text, font=font_desc)
            dw = db[2] - db[0]
            if dw > (ancho - 14):
                desc_size = 21
                font_desc = obtener_fuente("arial.ttf", desc_size)
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

        bc_img = generar_imagen_codigo_barras(item_text, target_size=(bc_w, bc_h))

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


def generar_documento_pdf(items_con_cant: List[Dict], size: str = "60x30", nombre_pdf: str = "etiquetas") -> Optional[str]:
    """Genera el PDF con las medidas térmicas exactas de Brother QL (62x100 mm o 62x29 mm)."""
    pdf_filename = os.path.join(directorio_pdf, f"{nombre_pdf}_{size}.pdf")

    if size in ("60x95", "60x90", "62x100"):
        w_mm, h_mm = 100.0, 62.0
        pdf = FPDF("L", "mm", (62.0, 100.0))
    else:
        w_mm, h_mm = 62.0, 29.0
        pdf = FPDF("L", "mm", (29.0, 62.0))

    total = 0
    cache_temp = {}

    for it in items_con_cant:
        code = it["item"]
        desc = it["description"]
        qty = it["qty"]
        if qty <= 0 or not code:
            continue

        key = f"{code}_{desc}_{size}"
        if key not in cache_temp:
            img = crear_imagen_etiqueta(code, desc, size=size)
            if not img:
                continue
            tmp_path = os.path.join(directorio_temp, f"lbl_{limpiar_nombre_archivo(code)}_{size}.jpg")
            img.save(tmp_path, "JPEG", quality=95)
            cache_temp[key] = tmp_path

        img_path = cache_temp[key]
        for _ in range(qty):
            pdf.add_page()
            pdf.image(img_path, x=0, y=0, w=w_mm, h=h_mm)
            total += 1

    if total == 0:
        return None

    try:
        pdf.output(pdf_filename)
        return pdf_filename
    except Exception as e:
        messagebox.showerror("Error al guardar PDF", f"No se pudo crear el archivo PDF:\n{e}")
        return None


# ==========================================
# GESTIÓN DEL CATÁLOGO (DATOS_DEPO.xlsx)
# ==========================================
class CatalogoManager:
    def __init__(self):
        self.ruta_archivo = get_data_file_path("DATOS_DEPO.xlsx")
        self.items: List[Dict] = []
        self.codigos_unicos = set()
        self.cargado = False

    def cargar(self):
        if not os.path.exists(self.ruta_archivo):
            print(f"[Aviso] Archivo {self.ruta_archivo} no encontrado.")
            return

        try:
            df = pd.read_excel(self.ruta_archivo, header=None, dtype=str)
            items_list = []
            codigos = set()
            for _, row in df.iterrows():
                code = str(row[0] if not pd.isna(row[0]) else "").strip().upper()
                uom = str(row[1] if not pd.isna(row[1]) else "CU").strip().upper()
                desc = str(row[3] if not pd.isna(row[3]) else "").strip().upper()
                if code and code not in codigos:
                    codigos.add(code)
                    items_list.append({"item": code, "uom": uom or "CU", "description": desc})

            self.items = items_list
            self.codigos_unicos = codigos
            self.cargado = True
            print(f"[Catálogo] Cargados {len(self.items)} registros desde {self.ruta_archivo}")
        except Exception as e:
            print(f"[Error Catálogo] {e}")

    def buscar(self, texto: str, limite: int = 50) -> List[Dict]:
        q = texto.strip().upper()
        if not q:
            return []
        res = []
        for it in self.items:
            if it["item"].startswith(q):
                res.append(it)
                if len(res) >= limite:
                    return res
        for it in self.items:
            if it in res:
                continue
            if q in it["item"] or q in it["description"]:
                res.append(it)
                if len(res) >= limite:
                    break
        return res

    def agregar_item(self, item_code: str, description: str, uom: str = "CU") -> bool:
        item_code = item_code.strip().upper()
        description = description.strip().upper()
        uom = (uom or "CU").strip().upper()

        if not item_code or not description:
            return False

        try:
            if os.path.exists(self.ruta_archivo):
                wb = openpyxl.load_workbook(self.ruta_archivo)
                sheet = wb.active
            else:
                wb = openpyxl.Workbook()
                sheet = wb.active
                sheet.title = "Hoja1"

            sheet.append([item_code, uom, None, description])
            wb.save(self.ruta_archivo)
            wb.close()

            new_it = {"item": item_code, "uom": uom, "description": description}
            found = False
            for i, it in enumerate(self.items):
                if it["item"] == item_code:
                    self.items[i] = new_it
                    found = True
                    break
            if not found:
                self.items.insert(0, new_it)
                self.codigos_unicos.add(item_code)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el ítem en {self.ruta_archivo}:\n{e}")
            return False


# ==========================================
# VENTANA PRINCIPAL DE ESCRITORIO
# ==========================================
class AppEscritorio:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Generador de Etiquetas de Depósito - DLS Archer")
        self.root.geometry("1100x720")
        self.root.minsize(980, 650)

        # Icono de ventana
        ico = resource_path("icono.ico")
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

        # Estado
        self.catalogo = CatalogoManager()
        self.cola_impresion: List[Dict] = []  # Lista de dicts: {"item": str, "description": str, "qty": int}
        self.tamano_actual = tk.StringVar(value="60x30")
        self.ultimo_preview_item = "012345"
        self.ultimo_preview_desc = "EJEMPLO DE ETIQUETA"
        self.foto_preview_tk = None

        self._configurar_estilos()
        self._construir_interfaz()

        # Cargar catálogo en hilo secundario para inicio instantáneo
        threading.Thread(target=self._cargar_catalogo_async, daemon=True).start()

    def _configurar_estilos(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background="#f8fafc")
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#1e3a8a")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0")

    def _cargar_catalogo_async(self):
        self.catalogo.cargar()
        count = len(self.catalogo.items)
        self.root.after(0, lambda: self.lbl_cat_status.config(
            text=f"✔ Base de Datos: {count:,} artículos cargados".replace(",", ".")
        ))

    def _construir_interfaz(self):
        # 1. HEADER
        header_frame = tk.Frame(self.root, bg="#0f172a", height=60, padx=16, pady=8)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        logo_path = resource_path("logo.png")
        if not os.path.exists(logo_path):
            logo_path = resource_path(os.path.join("web", "static", "img", "logo.png"))

        if os.path.exists(logo_path):
            try:
                logo_im = Image.open(logo_path)
                logo_im.thumbnail((160, 44), Image.Resampling.LANCZOS)
                self.logo_header_tk = ImageTk.PhotoImage(logo_im)
                lbl_logo = tk.Label(header_frame, image=self.logo_header_tk, bg="#0f172a")
                lbl_logo.pack(side=tk.LEFT, padx=(0, 14))
            except Exception:
                pass

        title_box = tk.Frame(header_frame, bg="#0f172a")
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="Generador de Etiquetas",
            font=("Segoe UI", 13, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="DLS Archer - Depósito Neuquén",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a"
        ).pack(anchor="w")

        self.lbl_cat_status = tk.Label(
            title_box,
            text="Cargando base de datos...",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a"
        )
        self.lbl_cat_status.pack(anchor="w")

        btn_nuevo_base = tk.Button(
            header_frame,
            text="+ Nuevo Ítem en Base",
            command=self._dialogo_nuevo_item,
            font=("Segoe UI", 9, "bold"),
            bg="#10b981",
            fg="white",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2"
        )
        btn_nuevo_base.pack(side=tk.RIGHT, padx=5)

        # 2. CONTENEDOR PRINCIPAL EN 2 COLUMNAS
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#cbd5e1", sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # COLUMNA IZQUIERDA: ENTRADAS Y COLA DE IMPRESIÓN (60% ANCHO)
        left_frame = tk.Frame(main_paned, bg="#f8fafc")
        main_paned.add(left_frame, minsize=520)

        # TABS DE ENTRADA
        notebook = ttk.Notebook(left_frame)
        notebook.pack(fill=tk.X, padx=6, pady=(4, 8))

        # TAB 1: Base de Datos
        tab_db = tk.Frame(notebook, bg="#ffffff", padx=10, pady=8)
        notebook.add(tab_db, text="🔍 Base de Datos (DATOS_DEPO)")
        self._construir_tab_db(tab_db)

        # TAB 2: Planilla Excel
        tab_excel = tk.Frame(notebook, bg="#ffffff", padx=10, pady=8)
        notebook.add(tab_excel, text="📁 Importar Excel (.xlsx)")
        self._construir_tab_excel(tab_excel)

        # TAB 3: Carga Manual
        tab_manual = tk.Frame(notebook, bg="#ffffff", padx=10, pady=8)
        notebook.add(tab_manual, text="✏ Carga Manual")
        self._construir_tab_manual(tab_manual)

        # TABLA DE COLA DE IMPRESIÓN
        queue_header = tk.Frame(left_frame, bg="#f8fafc")
        queue_header.pack(fill=tk.X, padx=6, pady=(4, 2))

        tk.Label(
            queue_header,
            text="Cola de Impresión:",
            font=("Segoe UI", 10, "bold"),
            fg="#1e293b",
            bg="#f8fafc"
        ).pack(side=tk.LEFT)

        btn_vaciar = tk.Button(
            queue_header,
            text="Vaciar Cola",
            command=self._vaciar_cola,
            font=("Segoe UI", 8),
            bg="#fee2e2",
            fg="#991b1b",
            relief=tk.FLAT,
            padx=6
        )
        btn_vaciar.pack(side=tk.RIGHT)

        btn_eliminar = tk.Button(
            queue_header,
            text="Quitar Ítem",
            command=self._eliminar_seleccionado,
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#475569",
            relief=tk.FLAT,
            padx=6
        )
        btn_eliminar.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(left_frame, bg="#ffffff")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        cols = ("item", "description", "qty")
        self.tree_queue = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        self.tree_queue.heading("item", text="Código")
        self.tree_queue.heading("description", text="Descripción")
        self.tree_queue.heading("qty", text="Cant.")
        self.tree_queue.column("item", width=120, anchor="w")
        self.tree_queue.column("description", width=320, anchor="w")
        self.tree_queue.column("qty", width=55, anchor="center")

        sb_queue = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree_queue.yview)
        self.tree_queue.configure(yscrollcommand=sb_queue.set)
        self.tree_queue.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_queue.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_queue.bind("<<TreeviewSelect>>", self._on_select_queue_item)

        # BARRA INFERIOR DE TOTALES
        bottom_totals = tk.Frame(left_frame, bg="#f1f5f9", padx=10, pady=6)
        bottom_totals.pack(fill=tk.X, padx=6, pady=(2, 4))

        self.lbl_totals = tk.Label(
            bottom_totals,
            text="Ítems en cola: 0   |   Total etiquetas: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            bg="#f1f5f9"
        )
        self.lbl_totals.pack(side=tk.LEFT)

        # COLUMNA DERECHA: PREVIEW Y ACCIONES (40% ANCHO)
        right_frame = tk.Frame(main_paned, bg="#ffffff", padx=14, pady=10)
        main_paned.add(right_frame, minsize=380)

        # 1. SELECTOR DE TAMAÑO
        size_box = tk.LabelFrame(
            right_frame,
            text=" Tamaño de Etiqueta Térmica ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1e293b",
            padx=10,
            pady=8
        )
        size_box.pack(fill=tk.X, pady=(0, 10))

        r1 = tk.Radiobutton(
            size_box,
            text="62 x 29 mm  (Chica - Brother DK-11209 / Cinta 62mm)",
            variable=self.tamano_actual,
            value="60x30",
            command=self._actualizar_preview,
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            activebackground="#ffffff",
            cursor="hand2"
        )
        r1.pack(anchor="w", pady=2)

        r2 = tk.Radiobutton(
            size_box,
            text="62 x 100 mm  (Grande - Brother DK-11202 / Cinta 62mm)",
            variable=self.tamano_actual,
            value="60x95",
            command=self._actualizar_preview,
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            activebackground="#ffffff",
            cursor="hand2"
        )
        r2.pack(anchor="w", pady=2)

        # 2. VISTA PREVIA EN VIVO
        prev_box = tk.LabelFrame(
            right_frame,
            text=" Vista Previa en Vivo ",
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#1e293b",
            padx=8,
            pady=8
        )
        prev_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.lbl_preview_img = tk.Label(prev_box, bg="#ffffff")
        self.lbl_preview_img.pack(fill=tk.BOTH, expand=True)

        # 3. BOTONES DE ACCIÓN DE IMPRESIÓN
        action_box = tk.Frame(right_frame, bg="#ffffff")
        action_box.pack(fill=tk.X, pady=(0, 8))

        btn_imprimir = tk.Button(
            action_box,
            text="🖨️ Generar PDF e Imprimir",
            command=self._imprimir_pdf_accion,
            font=("Segoe UI", 11, "bold"),
            bg="#059669",
            fg="white",
            relief=tk.FLAT,
            pady=8,
            cursor="hand2"
        )
        btn_imprimir.pack(fill=tk.X, pady=2)

        btn_guardar_jpg = tk.Button(
            action_box,
            text="💾 Guardar Imágenes de Etiquetas (.JPG)",
            command=self._guardar_imagenes_jpg,
            font=("Segoe UI", 9),
            bg="#f1f5f9",
            fg="#334155",
            relief=tk.FLAT,
            pady=4,
            cursor="hand2"
        )
        btn_guardar_jpg.pack(fill=tk.X, pady=2)

        # 4. TARJETA GUÍA BROTHER QL-800
        guide_box = tk.Frame(right_frame, bg="#fef3c7", padx=10, pady=8, highlightbackground="#fcd34d", highlightthickness=1)
        guide_box.pack(fill=tk.X)

        tk.Label(
            guide_box,
            text="Configuración Brother QL-800:",
            font=("Segoe UI", 8, "bold"),
            bg="#fef3c7",
            fg="#92400e"
        ).pack(anchor="w")

        info_text = (
            "• Papel: Seleccionar 62mm (Cinta continua) o 62mm x 100mm\n"
            "• NO seleccionar 29mm x 90mm si el rollo en la máquina es de 62mm\n"
            "• Márgenes: Ninguno  |  Orientación: Horizontal"
        )
        tk.Label(
            guide_box,
            text=info_text,
            font=("Segoe UI", 8),
            bg="#fef3c7",
            fg="#78350f",
            justify="left"
        ).pack(anchor="w")

        # Generar primer preview inicial
        self._actualizar_preview()

    # ==========================================
    # SUB-INTERFACES DE TABS
    # ==========================================
    def _construir_tab_db(self, parent: tk.Frame):
        search_bar = tk.Frame(parent, bg="#ffffff")
        search_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Label(search_bar, text="Buscar:", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 4))
        self.entry_db_search = tk.Entry(search_bar, font=("Segoe UI", 9), bg="#f8fafc")
        self.entry_db_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.entry_db_search.bind("<KeyRelease>", self._on_db_search_key)

        res_frame = tk.Frame(parent, bg="#ffffff")
        res_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        cols = ("item", "desc", "uom")
        self.tree_db = ttk.Treeview(res_frame, columns=cols, show="headings", height=5, selectmode="browse")
        self.tree_db.heading("item", text="Código")
        self.tree_db.heading("desc", text="Descripción")
        self.tree_db.heading("uom", text="UOM")
        self.tree_db.column("item", width=110)
        self.tree_db.column("desc", width=310)
        self.tree_db.column("uom", width=50, anchor="center")

        sb_db = ttk.Scrollbar(res_frame, orient=tk.VERTICAL, command=self.tree_db.yview)
        self.tree_db.configure(yscrollcommand=sb_db.set)
        self.tree_db.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_db.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_db.bind("<<TreeviewSelect>>", self._on_select_db_item)

        add_bar = tk.Frame(parent, bg="#ffffff")
        add_bar.pack(fill=tk.X)

        tk.Label(add_bar, text="Cant:", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 4))
        self.spin_db_qty = tk.Spinbox(add_bar, from_=1, to=9999, width=6, font=("Segoe UI", 9))
        self.spin_db_qty.delete(0, tk.END)
        self.spin_db_qty.insert(0, "1")
        self.spin_db_qty.pack(side=tk.LEFT, padx=(0, 10))

        btn_add_db = tk.Button(
            add_bar,
            text="+ Agregar a Cola de Impresión",
            command=self._agregar_desde_db,
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            cursor="hand2"
        )
        btn_add_db.pack(side=tk.RIGHT)

    def _construir_tab_excel(self, parent: tk.Frame):
        top_bar = tk.Frame(parent, bg="#ffffff")
        top_bar.pack(fill=tk.X, pady=(0, 6))

        self.entry_excel_path = tk.Entry(top_bar, font=("Segoe UI", 9), bg="#f8fafc")
        self.entry_excel_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_examinar = tk.Button(
            top_bar,
            text="Examinar...",
            command=self._examinar_excel,
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_examinar.pack(side=tk.LEFT, padx=2)

        btn_cargar = tk.Button(
            top_bar,
            text="Cargar Ítems",
            command=self._cargar_desde_excel,
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        btn_cargar.pack(side=tk.LEFT, padx=2)

        tk.Label(
            parent,
            text="Detecta automáticamente columnas que inicien con código '0' (Ítem, Descripción, Cantidad).",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#ffffff"
        ).pack(anchor="w")

    def _construir_tab_manual(self, parent: tk.Frame):
        f = tk.Frame(parent, bg="#ffffff")
        f.pack(fill=tk.X)

        tk.Label(f, text="Código:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.entry_man_code = tk.Entry(f, font=("Segoe UI", 9), width=16, bg="#f8fafc")
        self.entry_man_code.grid(row=0, column=1, sticky="w", padx=4, pady=2)
        self.entry_man_code.bind("<KeyRelease>", lambda e: self._actualizar_preview(self.entry_man_code.get(), self.entry_man_desc.get()))

        tk.Label(f, text="Descripción:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=2, sticky="w", padx=4, pady=2)
        self.entry_man_desc = tk.Entry(f, font=("Segoe UI", 9), width=32, bg="#f8fafc")
        self.entry_man_desc.grid(row=0, column=3, sticky="we", padx=4, pady=2)
        self.entry_man_desc.bind("<KeyRelease>", lambda e: self._actualizar_preview(self.entry_man_code.get(), self.entry_man_desc.get()))

        tk.Label(f, text="Cant:", font=("Segoe UI", 9, "bold"), bg="#ffffff").grid(row=0, column=4, sticky="w", padx=4, pady=2)
        self.spin_man_qty = tk.Spinbox(f, from_=1, to=9999, width=5, font=("Segoe UI", 9))
        self.spin_man_qty.delete(0, tk.END)
        self.spin_man_qty.insert(0, "1")
        self.spin_man_qty.grid(row=0, column=5, sticky="w", padx=4, pady=2)

        btn_add = tk.Button(
            f,
            text="+ Agregar",
            command=self._agregar_manual,
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8
        )
        btn_add.grid(row=0, column=6, padx=6, pady=2)

    # ==========================================
    # MANEJO DE EVENTOS Y BÚSQUEDA
    # ==========================================
    def _on_db_search_key(self, event=None):
        q = self.entry_db_search.get().strip()
        for row in self.tree_db.get_children():
            self.tree_db.delete(row)
        if len(q) < 2:
            return
        resultados = self.catalogo.buscar(q, limite=35)
        for it in resultados:
            self.tree_db.insert("", tk.END, values=(it["item"], it["description"], it["uom"]))

    def _on_select_db_item(self, event=None):
        sel = self.tree_db.selection()
        if not sel:
            return
        vals = self.tree_db.item(sel[0], "values")
        if vals:
            self._actualizar_preview(item=vals[0], desc=vals[1])

    def _agregar_desde_db(self):
        sel = self.tree_db.selection()
        if not sel:
            messagebox.showwarning("Atención", "Seleccione un artículo de la lista de búsqueda.")
            return
        vals = self.tree_db.item(sel[0], "values")
        try:
            qty = int(self.spin_db_qty.get().strip())
        except ValueError:
            qty = 1
        if qty <= 0:
            qty = 1

        self._agregar_a_cola(vals[0], vals[1], qty)

    def _examinar_excel(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Planilla Excel",
            filetypes=[("Archivos Excel (*.xlsx;*.xls)", "*.xlsx;*.xls")]
        )
        if archivo:
            self.entry_excel_path.delete(0, tk.END)
            self.entry_excel_path.insert(0, archivo)

    def _cargar_desde_excel(self):
        ruta = self.entry_excel_path.get().strip()
        if not os.path.exists(ruta):
            messagebox.showerror("Error", "El archivo Excel indicado no existe.")
            return
        try:
            df = pd.read_excel(ruta, dtype=str)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo Excel:\n{e}")
            return

        # Buscar celda con código que empiece con '0'
        col_cod = None
        inicio_fila = None
        for col in df.columns:
            series = df[col].dropna().astype(str)
            for idx, val in series.items():
                if val.strip().startswith("0"):
                    col_cod = col
                    inicio_fila = idx
                    break
            if col_cod is not None:
                break

        if col_cod is None:
            messagebox.showerror("Formato", "No se detectaron códigos que comiencen con '0'.")
            return

        idx_c = df.columns.get_loc(col_cod)
        df_cut = df.iloc[inicio_fila:, idx_c:idx_c + 3].copy()
        cols = list(df_cut.columns)

        agregados = 0
        for _, row in df_cut.iterrows():
            it = str(row[cols[0]] if not pd.isna(row[cols[0]]) else "").strip().upper()
            de = str(row[cols[1]] if not pd.isna(row[cols[1]]) else "").strip().upper()
            cant_raw = str(row[cols[2]] if not pd.isna(row[cols[2]]) else "1").strip()
            if cant_raw.endswith(".0"):
                cant_raw = cant_raw[:-2]
            try:
                q = int(cant_raw)
            except ValueError:
                q = 1
            if it and q > 0:
                self._agregar_a_cola(it, de, q, actualizar_preview=False)
                agregados += 1

        self._actualizar_totales()
        if agregados > 0:
            messagebox.showinfo("Éxito", f"Se cargaron {agregados} ítems desde la planilla Excel.")
            if self.cola_impresion:
                self._actualizar_preview(self.cola_impresion[0]["item"], self.cola_impresion[0]["description"])

    def _agregar_manual(self):
        c = self.entry_man_code.get().strip().upper()
        d = self.entry_man_desc.get().strip().upper()
        try:
            q = int(self.spin_man_qty.get().strip())
        except ValueError:
            q = 1
        if not c:
            messagebox.showwarning("Atención", "Ingrese el código del ítem.")
            return
        self._agregar_a_cola(c, d, max(1, q))
        self.entry_man_code.delete(0, tk.END)
        self.entry_man_desc.delete(0, tk.END)
        self.spin_man_qty.delete(0, tk.END)
        self.spin_man_qty.insert(0, "1")
        self.entry_man_code.focus()

    def _agregar_a_cola(self, item: str, description: str, qty: int, actualizar_preview: bool = True):
        # Si ya existe, sumar cantidad
        encontrado = False
        for it in self.cola_impresion:
            if it["item"] == item:
                it["qty"] += qty
                encontrado = True
                break
        if not encontrado:
            self.cola_impresion.append({"item": item, "description": description, "qty": qty})

        self._refrescar_tabla_cola()
        if actualizar_preview:
            self._actualizar_preview(item, description)

    def _refrescar_tabla_cola(self):
        for r in self.tree_queue.get_children():
            self.tree_queue.delete(r)
        for it in self.cola_impresion:
            self.tree_queue.insert("", tk.END, values=(it["item"], it["description"], it["qty"]))
        self._actualizar_totales()

    def _actualizar_totales(self):
        total_items = len(self.cola_impresion)
        total_labels = sum(it["qty"] for it in self.cola_impresion)
        self.lbl_totals.config(
            text=f"Ítems en cola: {total_items}   |   Total etiquetas a imprimir: {total_labels}"
        )

    def _on_select_queue_item(self, event=None):
        sel = self.tree_queue.selection()
        if not sel:
            return
        vals = self.tree_queue.item(sel[0], "values")
        if vals:
            self._actualizar_preview(item=vals[0], desc=vals[1])

    def _eliminar_seleccionado(self):
        sel = self.tree_queue.selection()
        if not sel:
            return
        idx = self.tree_queue.index(sel[0])
        del self.cola_impresion[idx]
        self._refrescar_tabla_cola()

    def _vaciar_cola(self):
        if not self.cola_impresion:
            return
        if messagebox.askyesno("Vaciar Cola", "¿Desea quitar todos los ítems de la lista de impresión?"):
            self.cola_impresion.clear()
            self._refrescar_tabla_cola()

    # ==========================================
    # PREVISUALIZACIÓN EN VIVO
    # ==========================================
    def _actualizar_preview(self, item: str = None, desc: str = None):
        if item:
            self.ultimo_preview_item = item
        if desc:
            self.ultimo_preview_desc = desc

        it = self.ultimo_preview_item or "012345"
        de = self.ultimo_preview_desc or "EJEMPLO DE ETIQUETA"
        sz = self.tamano_actual.get()

        img = crear_imagen_etiqueta(it, de, size=sz)
        if not img:
            return

        # Escalar para que entre comodamente en el panel derecho (max 380 px ancho)
        max_w, max_h = 360, 220
        ratio = min(max_w / img.width, max_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)

        img_scaled = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.foto_preview_tk = ImageTk.PhotoImage(img_scaled)
        self.lbl_preview_img.config(image=self.foto_preview_tk)

    # ==========================================
    # ACCIONES DE IMPRESIÓN Y EXPORTACIÓN
    # ==========================================
    def _imprimir_pdf_accion(self):
        if not self.cola_impresion:
            messagebox.showwarning("Atención", "Agregue al menos un ítem a la cola de impresión.")
            return

        sz = self.tamano_actual.get()
        pdf_path = generar_documento_pdf(self.cola_impresion, size=sz, nombre_pdf="Etiquetas_Depo")
        if not pdf_path:
            messagebox.showwarning("Atención", "No se pudieron generar etiquetas (cantidades en 0).")
            return

        # Abrir el PDF generado con el visor predeterminado de Windows
        try:
            if sys.platform == "win32":
                os.startfile(pdf_path)
            else:
                subprocess.Popen(["xdg-open", pdf_path])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo PDF:\n{e}")

    def _guardar_imagenes_jpg(self):
        if not self.cola_impresion:
            messagebox.showwarning("Atención", "Agregue al menos un ítem a la cola de impresión.")
            return

        sz = self.tamano_actual.get()
        guardados = 0
        for it in self.cola_impresion:
            img = crear_imagen_etiqueta(it["item"], it["description"], size=sz)
            if img:
                out_path = os.path.join(directorio_etiquetas, f"{limpiar_nombre_archivo(it['item'])}_{sz}.jpg")
                img.save(out_path, "JPEG", quality=95)
                guardados += 1

        messagebox.showinfo(
            "Imágenes Guardadas",
            f"Se guardaron {guardados} imágenes de alta resolución en:\n{directorio_etiquetas}"
        )

    # ==========================================
    # DIÁLOGO NUEVO ÍTEM EN BASE DE DATOS
    # ==========================================
    def _dialogo_nuevo_item(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Nuevo Ítem en Base de Datos")
        dlg.geometry("450x300")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ico = resource_path("icono.ico")
        if os.path.exists(ico):
            try:
                dlg.iconbitmap(ico)
            except Exception:
                pass

        header = tk.Frame(dlg, bg="#f1f5f9", padx=14, pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="Agregar Artículo a DATOS_DEPO.xlsx", font=("Segoe UI", 10, "bold"), bg="#f1f5f9", fg="#0f172a").pack(anchor="w")
        tk.Label(header, text="Se guardará permanentemente en el archivo Excel.", font=("Segoe UI", 8), bg="#f1f5f9", fg="#64748b").pack(anchor="w")

        body = tk.Frame(dlg, padx=20, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="Código del Ítem *:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        e_code = tk.Entry(body, font=("Segoe UI", 9), width=30)
        e_code.grid(row=0, column=1, pady=4, padx=4)

        tk.Label(body, text="Unidad (UOM):", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        e_uom = tk.Entry(body, font=("Segoe UI", 9), width=10)
        e_uom.insert(0, "CU")
        e_uom.grid(row=1, column=1, sticky="w", pady=4, padx=4)

        tk.Label(body, text="Descripción *:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=4)
        e_desc = tk.Entry(body, font=("Segoe UI", 9), width=30)
        e_desc.grid(row=2, column=1, pady=4, padx=4)

        var_add_queue = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(body, text="Agregar también a la cola de impresión", variable=var_add_queue, font=("Segoe UI", 9))
        cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=8)

        def guardar():
            code = e_code.get().strip().upper()
            desc = e_desc.get().strip().upper()
            uom = e_uom.get().strip().upper() or "CU"
            if not code or not desc:
                messagebox.showwarning("Campos Requeridos", "Debe completar Código y Descripción.")
                return

            exito = self.catalogo.agregar_item(code, desc, uom)
            if exito:
                self.lbl_cat_status.config(
                    text=f"✔ Base de Datos: {len(self.catalogo.items):,} artículos cargados".replace(",", ".")
                )
                if var_add_queue.get():
                    self._agregar_a_cola(code, desc, 1)
                messagebox.showinfo("Éxito", f"Ítem '{code}' guardado exitosamente en DATOS_DEPO.xlsx.")
                dlg.destroy()

        btn_box = tk.Frame(dlg, padx=14, pady=10, bg="#f8fafc")
        btn_box.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Button(btn_box, text="Cancelar", command=dlg.destroy, font=("Segoe UI", 9), padx=10).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_box, text="✔ Guardar en Base", command=guardar, bg="#10b981", fg="white", font=("Segoe UI", 9, "bold"), padx=12, relief=tk.FLAT).pack(side=tk.RIGHT, padx=4)

        e_code.focus()


# ==========================================
# PUNTO DE ENTRADA PRINCIPAL
# ==========================================
def main():
    root = tk.Tk()
    app = AppEscritorio(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_file = os.path.join(tempfile.gettempdir(), "GeneradorEtiquetas_Error.log")
        with open(err_file, "w", encoding="utf-8") as f:
            f.write(str(e))
        messagebox.showerror("Error Crítico", f"Ocurrió un error inesperado:\n{e}\n\nDetalles en:\n{err_file}")
