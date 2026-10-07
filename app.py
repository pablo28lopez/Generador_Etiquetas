import os
import re
import sys
import tempfile
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont, ImageTk
from fpdf import FPDF

# ==========================================
# RUTAS DE RECURSOS (COMPATIBLE PYINSTALLER)
# ==========================================
def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, compatible con desarrollo y PyInstaller .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ==========================================
# CONFIGURACIÓN DE DIRECTORIOS
# ==========================================
descargas_path = os.path.join(os.path.expanduser("~"), "Downloads")
directorio_etiquetas = os.path.join(descargas_path, "Etiquetas")
directorio_pdf = os.path.join(descargas_path, "PDFs")

# Directorio temporal seguro del sistema para evitar problemas de permisos
directorio_temp = os.path.join(tempfile.gettempdir(), "GeneradorEtiquetas_Temp")

os.makedirs(directorio_etiquetas, exist_ok=True)
os.makedirs(directorio_pdf, exist_ok=True)
os.makedirs(directorio_temp, exist_ok=True)


# ==========================================
# UTILIDADES Y TIPOGRAFÍA
# ==========================================
def limpiar_nombre_archivo(nombre):
    """Limpia caracteres no permitidos en nombres de archivo de Windows."""
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(nombre).strip())


def obtener_fuente(nombre_fuente, tamano):
    """Carga la fuente empaquetada o del sistema operativo."""
    # 1. Intentar desde recursos locales / PyInstaller
    ruta_local = resource_path(nombre_fuente)
    if os.path.exists(ruta_local):
        try:
            return ImageFont.truetype(ruta_local, tamano)
        except Exception:
            pass

    # 2. Intentar desde las fuentes de Windows
    rutas_sistema = [
        nombre_fuente,
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", nombre_fuente),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts", nombre_fuente)
    ]
    for ruta in rutas_sistema:
        try:
            return ImageFont.truetype(ruta, tamano)
        except Exception:
            continue

    # 3. Fallback seguro por defecto
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:
        return ImageFont.load_default()


# ==========================================
# GENERACIÓN DE CÓDIGO DE BARRAS Y ETIQUETA
# ==========================================
def generar_codigo_barras(item):
    """Genera imagen de código Code39 recortando la parte inferior del texto."""
    try:
        item = str(item).strip().upper()
        item_limpio = limpiar_nombre_archivo(item)
        if not item_limpio:
            return None

        code39 = barcode.get_barcode_class('code39')
        writer = ImageWriter()
        writer.set_options({"write_text": True})

        codigo = code39(item, writer=writer, add_checksum=False)
        temp_filename = os.path.join(directorio_temp, item_limpio)
        codigo_path = codigo.save(temp_filename)

        # Recortar texto inferior (70% superior)
        with Image.open(codigo_path) as img:
            img_rgb = img.convert("RGB")
            width, height = img_rgb.size
            img_cropped = img_rgb.crop((0, 0, width, int(height * 0.70)))
            img_resized = img_cropped.resize((595, 120))

            jpg_filename = f"{temp_filename}.jpg"
            img_resized.save(jpg_filename, "JPEG")

        if os.path.exists(codigo_path):
            os.remove(codigo_path)

        return jpg_filename
    except Exception as e:
        print(f"Error generando código de barras para '{item}': {e}")
        return None


def crear_etiqueta(item, description):
    """Genera la imagen final de 600x300 px con código de barras, ítem y descripción."""
    barcode_path = generar_codigo_barras(item)
    if barcode_path is None:
        return None

    ancho, alto = 600, 300
    etiqueta = Image.new('RGB', (ancho, alto), 'white')
    draw = ImageDraw.Draw(etiqueta)

    font_item = obtener_fuente("arialbd.ttf", 80)
    font_description = obtener_fuente("arial.ttf", 22)

    # Pegar código de barras
    with Image.open(barcode_path) as barcode_image:
        barcode_x = (ancho - barcode_image.width) // 2
        barcode_y = 10
        etiqueta.paste(barcode_image, (barcode_x, barcode_y))

    # Número de ítem debajo del código
    item_text = str(item).upper().strip()
    item_bbox = draw.textbbox((0, 0), item_text, font=font_item)
    item_w = item_bbox[2] - item_bbox[0]
    item_x = (ancho - item_w) // 2
    item_y = barcode_y + 120 - 15
    draw.text((item_x, item_y), item_text, fill='black', font=font_item)

    # Descripción debajo del ítem (con truncado inteligente si es demasiado ancha)
    desc_text = str(description).upper().strip()
    desc_bbox = draw.textbbox((0, 0), desc_text, font=font_description)
    desc_w = desc_bbox[2] - desc_bbox[0]

    if desc_w > (ancho - 20):
        while len(desc_text) > 4 and (draw.textbbox((0, 0), desc_text + "...", font=font_description)[2] - draw.textbbox((0, 0), desc_text + "...", font=font_description)[0]) > (ancho - 20):
            desc_text = desc_text[:-1]
        desc_text = desc_text + "..."
        desc_bbox = draw.textbbox((0, 0), desc_text, font=font_description)
        desc_w = desc_bbox[2] - desc_bbox[0]

    desc_x = (ancho - desc_w) // 2
    desc_y = item_y + (item_bbox[3] - item_bbox[1]) + 25
    draw.text((desc_x, desc_y), desc_text, fill='black', font=font_description)

    # Guardar etiqueta final
    nombre_limpio = limpiar_nombre_archivo(item)
    etiqueta_path = os.path.join(directorio_etiquetas, f"{nombre_limpio}.jpg")
    etiqueta.save(etiqueta_path, "JPEG")

    # Limpiar archivo temporal intermedio
    if os.path.exists(barcode_path):
        try:
            os.remove(barcode_path)
        except OSError:
            pass

    return etiqueta_path


def generar_pdf(etiquetas, nombre_pdf):
    """Genera archivo PDF de 60x30 mm con las etiquetas solicitadas."""
    pdf_filename = os.path.join(directorio_pdf, f"{nombre_pdf}.pdf")

    if os.path.exists(pdf_filename):
        try:
            os.remove(pdf_filename)
        except PermissionError:
            messagebox.showerror(
                "Archivo en Uso",
                f"El archivo '{nombre_pdf}.pdf' está abierto en otro programa.\nPor favor, ciérrelo e intente nuevamente."
            )
            return None

    if not etiquetas:
        messagebox.showerror("Sin Datos", "No se generaron etiquetas. Verifique el archivo o las cantidades.")
        return None

    try:
        pdf = FPDF("P", "mm", (60, 30))
        for etiqueta_path in etiquetas:
            pdf.add_page()
            pdf.image(etiqueta_path, x=0, y=0, w=60, h=30)
        pdf.output(pdf_filename)
        return pdf_filename
    except Exception as e:
        messagebox.showerror("Error PDF", f"Error al generar el PDF:\n{e}")
        return None


def imprimir_pdf(pdf_filename):
    """Abre el PDF en Windows con su aplicación predeterminada."""
    try:
        if sys.platform == "win32":
            os.startfile(pdf_filename)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", pdf_filename])
        else:
            subprocess.Popen(["xdg-open", pdf_filename])
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el archivo PDF:\n{e}")


# ==========================================
# EXCEL Y VENTANA DE EDICIÓN
# ==========================================
def encontrar_columna_codigo(df):
    """Busca la celda que comience con '0' para detectar el encabezado/datos."""
    for col in df.columns:
        col_series = df[col].dropna().astype(str)
        for i, valor in col_series.items():
            if valor.strip().startswith("0"):
                return col, i
    return None, None


def editar_cantidades(df_original, nombre_pdf):
    """Ventana para revisar y modificar cantidades."""
    ventana = tk.Toplevel()
    ventana.title("Editar Cantidades - Generador de Etiquetas")
    ventana.geometry("820x620")
    ventana.minsize(650, 400)

    ico = resource_path("icono.ico")
    if os.path.exists(ico):
        try:
            ventana.iconbitmap(ico)
        except Exception:
            pass

    top_bar = tk.Frame(ventana, padx=10, pady=10)
    top_bar.pack(fill=tk.X)

    tk.Label(top_bar, text="Buscar por Nº de Item:", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
    entry_busqueda = tk.Entry(top_bar, font=("Segoe UI", 10), width=20)
    entry_busqueda.pack(side=tk.LEFT, padx=5)

    container = tk.Frame(ventana)
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def _ajustar_ancho(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _ajustar_ancho)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    ventana.bind_all("<MouseWheel>", _on_mousewheel)

    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    encabezados = ["Item", "Descripción", "Cantidad Requerida"]
    header_frame = tk.Frame(scrollable_frame, bg="#e0e0e0")
    header_frame.pack(fill=tk.X, pady=(0, 2))

    tk.Label(header_frame, text=encabezados[0], font=("Segoe UI", 10, "bold"), bg="#e0e0e0", width=20, anchor="w").pack(side=tk.LEFT, padx=5, pady=4)
    tk.Label(header_frame, text=encabezados[1], font=("Segoe UI", 10, "bold"), bg="#e0e0e0", width=45, anchor="w").pack(side=tk.LEFT, padx=5, pady=4)
    tk.Label(header_frame, text=encabezados[2], font=("Segoe UI", 10, "bold"), bg="#e0e0e0", width=15, anchor="center").pack(side=tk.LEFT, padx=5, pady=4)

    entradas = []
    columnas_orig = list(df_original.columns)

    for _, row in df_original.iterrows():
        fila_cont = tk.Frame(scrollable_frame)
        fila_cont.pack(fill=tk.X, pady=1)

        val_item = str(row[columnas_orig[0]] if not pd.isna(row[columnas_orig[0]]) else "").strip()
        val_desc = str(row[columnas_orig[1]] if not pd.isna(row[columnas_orig[1]]) else "").strip()
        val_cant = str(row[columnas_orig[2]] if not pd.isna(row[columnas_orig[2]]) else "1").strip()

        if val_cant.endswith(".0"):
            val_cant = val_cant[:-2]

        e_item = tk.Entry(fila_cont, font=("Segoe UI", 9), width=20)
        e_item.insert(0, val_item)
        e_item.config(state="readonly")
        e_item.pack(side=tk.LEFT, padx=5)

        e_desc = tk.Entry(fila_cont, font=("Segoe UI", 9), width=45)
        e_desc.insert(0, val_desc)
        e_desc.config(state="readonly")
        e_desc.pack(side=tk.LEFT, padx=5)

        e_cant = tk.Entry(fila_cont, font=("Segoe UI", 9), width=15, justify="center")
        e_cant.insert(0, val_cant)
        e_cant.pack(side=tk.LEFT, padx=5)

        entradas.append({
            "frame": fila_cont,
            "item_entry": e_item,
            "desc_entry": e_desc,
            "cant_entry": e_cant,
            "item_text": val_item.lower()
        })

    def buscar():
        termino = entry_busqueda.get().strip().lower()
        for item_data in entradas:
            visible = termino in item_data["item_text"] if termino else True
            if visible:
                item_data["frame"].pack(fill=tk.X, pady=1)
            else:
                item_data["frame"].pack_forget()

    btn_buscar = tk.Button(top_bar, text="Buscar", command=buscar, font=("Segoe UI", 9))
    btn_buscar.pack(side=tk.LEFT, padx=5)
    entry_busqueda.bind("<Return>", lambda event: buscar())

    def restablecer_busqueda():
        entry_busqueda.delete(0, tk.END)
        for item_data in entradas:
            item_data["frame"].pack(fill=tk.X, pady=1)

    tk.Button(top_bar, text="Mostrar Todos", command=restablecer_busqueda, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

    def confirmar():
        etiquetas_generadas = []
        for item_data in entradas:
            item = item_data["item_entry"].get().strip()
            description = item_data["desc_entry"].get().strip()
            try:
                qty = int(item_data["cant_entry"].get().strip())
            except ValueError:
                qty = 0

            if qty > 0 and item:
                etiqueta = crear_etiqueta(item, description)
                if etiqueta:
                    for _ in range(qty):
                        etiquetas_generadas.append(etiqueta)

        if not etiquetas_generadas:
            messagebox.showwarning("Atención", "No se generaron etiquetas (cantidades en 0 o no válidas).")
            return

        pdf_filename = generar_pdf(etiquetas_generadas, nombre_pdf)
        if pdf_filename:
            messagebox.showinfo("Éxito", f"Se generó el archivo PDF exitosamente en:\n{pdf_filename}")
            imprimir_pdf(pdf_filename)

        ventana.destroy()
        if 'entry_archivo' in globals():
            entry_archivo.delete(0, tk.END)

    btn_confirmar = tk.Button(
        top_bar,
        text="✔ Confirmar y Generar",
        command=confirmar,
        bg="#2e7d32",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=10
    )
    btn_confirmar.pack(side=tk.RIGHT, padx=10)


def procesar_excel(ruta_excel):
    """Procesa el archivo Excel manteniendo ceros iniciales."""
    if not os.path.exists(ruta_excel):
        messagebox.showerror("Error", "El archivo seleccionado no existe.")
        return

    try:
        df = pd.read_excel(ruta_excel, dtype=str)
    except Exception as e:
        messagebox.showerror("Error al leer Excel", f"No se pudo leer el archivo Excel:\n{e}\n\nVerifique el formato (.xlsx o .xls).")
        return

    if df.empty:
        messagebox.showerror("Error", "El archivo Excel está vacío.")
        return

    columna_codigo, inicio_fila = encontrar_columna_codigo(df)
    if columna_codigo is None:
        messagebox.showerror(
            "Formato no reconocido",
            "No se encontraron celdas con código que comiencen con '0'.\nVerifique la estructura del archivo."
        )
        return

    idx_col = df.columns.get_loc(columna_codigo)
    df_recortado = df.iloc[inicio_fila:, idx_col:idx_col + 3].copy()

    if df_recortado.shape[1] < 3:
        messagebox.showerror("Columnas insuficientes", "Se requieren al menos 3 columnas consecutivas (Item, Descripción, Cantidad).")
        return

    df_recortado.columns = ["Item", "Description", "Qty Req."]
    nombre_pdf = os.path.splitext(os.path.basename(ruta_excel))[0]
    editar_cantidades(df_recortado, nombre_pdf)


# ==========================================
# CÓDIGO MANUAL
# ==========================================
def abrir_generador_manual():
    manual_window = tk.Toplevel()
    manual_window.title("Generar Códigos Manuales")
    manual_window.geometry("640x480")
    manual_window.minsize(500, 350)

    ico = resource_path("icono.ico")
    if os.path.exists(ico):
        try:
            manual_window.iconbitmap(ico)
        except Exception:
            pass

    canvas = tk.Canvas(manual_window, highlightthickness=0)
    scrollbar = tk.Scrollbar(manual_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    bottom_bar = tk.Frame(manual_window, pady=10)
    bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

    frame_tabla = tk.Frame(scrollable_frame)
    frame_tabla.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame_tabla, text="Código del Ítem", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=5)
    tk.Label(frame_tabla, text="Descripción", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=5, pady=5)
    tk.Label(frame_tabla, text="Cantidad", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=5, pady=5)

    filas = []

    def agregar_fila():
        r = len(filas) + 1
        e_item = tk.Entry(frame_tabla, font=("Segoe UI", 9), width=18)
        e_desc = tk.Entry(frame_tabla, font=("Segoe UI", 9), width=35)
        e_cant = tk.Entry(frame_tabla, font=("Segoe UI", 9), width=8, justify="center")
        e_cant.insert(0, "1")

        e_item.grid(row=r, column=0, padx=5, pady=3)
        e_desc.grid(row=r, column=1, padx=5, pady=3)
        e_cant.grid(row=r, column=2, padx=5, pady=3)

        filas.append({'item': e_item, 'desc': e_desc, 'cant': e_cant})

    def procesar_filas():
        etiquetas = []
        for f in filas:
            item = f['item'].get().strip()
            descripcion = f['desc'].get().strip()
            try:
                cantidad = int(f['cant'].get().strip())
            except ValueError:
                cantidad = 0

            if item and cantidad > 0:
                etiqueta = crear_etiqueta(item, descripcion)
                if etiqueta:
                    for _ in range(cantidad):
                        etiquetas.append(etiqueta)

        if etiquetas:
            nombre_pdf = "etiquetas_manuales"
            pdf_filename = generar_pdf(etiquetas, nombre_pdf)
            if pdf_filename:
                messagebox.showinfo("Éxito", f"Se generó el PDF en:\n{pdf_filename}")
                imprimir_pdf(pdf_filename)
                manual_window.destroy()
        else:
            messagebox.showwarning("Atención", "Complete al menos un código válido con cantidad mayor a 0.")

    for _ in range(3):
        agregar_fila()

    tk.Button(bottom_bar, text="+ Agregar Otra Fila", command=agregar_fila, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=15)
    tk.Button(bottom_bar, text="✔ Generar Etiquetas", bg="#1565c0", fg="white", font=("Segoe UI", 10, "bold"), command=procesar_filas, padx=10).pack(side=tk.RIGHT, padx=15)


# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
def seleccionar_archivo():
    archivo = filedialog.askopenfilename(
        title="Seleccione archivo Excel",
        filetypes=[
            ("Archivos Excel (*.xlsx, *.xls)", "*.xlsx;*.xls"),
            ("Todos los archivos", "*.*")
        ]
    )
    if archivo:
        entry_archivo.delete(0, tk.END)
        entry_archivo.insert(0, archivo)


def main():
    global entry_archivo

    root = tk.Tk()
    root.title("Generador de Etiquetas de Depósito")
    root.geometry("600x320")
    root.resizable(False, False)

    ico = resource_path("icono.ico")
    if os.path.exists(ico):
        try:
            root.iconbitmap(ico)
        except Exception:
            pass

    root.update_idletasks()
    ancho, alto = 600, 320
    x = (root.winfo_screenwidth() // 2) - (ancho // 2)
    y = (root.winfo_screenheight() // 2) - (alto // 2)
    root.geometry(f"{ancho}x{alto}+{x}+{y}")

    logo_path = resource_path("logo.png")
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path)
            logo_img.thumbnail((180, 45), Image.Resampling.LANCZOS)
            logo_tk = ImageTk.PhotoImage(logo_img)
            lbl_logo = tk.Label(root, image=logo_tk)
            lbl_logo.image = logo_tk
            lbl_logo.pack(pady=(8, 0))
        except Exception:
            pass

    lbl_titulo = tk.Label(root, text="Generador de Etiquetas", font=("Segoe UI", 15, "bold"), fg="#1a237e")
    lbl_titulo.pack(pady=(5, 2))

    lbl_sub = tk.Label(root, text="Cargue una planilla Excel o cree etiquetas de forma manual", font=("Segoe UI", 9), fg="#555555")
    lbl_sub.pack(pady=(0, 10))

    frame_archivo = tk.LabelFrame(root, text=" Planilla Excel (.xlsx / .xls) ", font=("Segoe UI", 9, "bold"), padx=15, pady=8)
    frame_archivo.pack(fill=tk.X, padx=25, pady=5)

    entry_archivo = tk.Entry(frame_archivo, font=("Segoe UI", 9), width=44)
    entry_archivo.pack(side=tk.LEFT, padx=(0, 5), ipady=2)

    tk.Button(frame_archivo, text="Examinar...", font=("Segoe UI", 9), command=seleccionar_archivo).pack(side=tk.LEFT, padx=3)
    tk.Button(frame_archivo, text="Borrar", font=("Segoe UI", 9), command=lambda: entry_archivo.delete(0, tk.END)).pack(side=tk.LEFT, padx=3)

    frame_acciones = tk.Frame(root, pady=8)
    frame_acciones.pack(fill=tk.X, padx=25)

    tk.Button(
        frame_acciones,
        text="▶ Procesar Excel y Generar",
        bg="#2e7d32",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        command=lambda: procesar_excel(entry_archivo.get()),
        cursor="hand2",
        padx=10,
        pady=5
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        frame_acciones,
        text="✏ Código Manual",
        bg="#37474f",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        command=abrir_generador_manual,
        cursor="hand2",
        padx=10,
        pady=5
    ).pack(side=tk.RIGHT, padx=5)

    tk.Label(root, text="Etiquetas y PDFs se guardan en Descargas/Etiquetas y Descargas/PDFs", font=("Segoe UI", 8), fg="#888888").pack(side=tk.BOTTOM, pady=6)

    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_log = os.path.join(tempfile.gettempdir(), "GeneradorEtiquetas_error.log")
        with open(error_log, "w", encoding="utf-8") as f:
            f.write(str(e))
        messagebox.showerror("Error Crítico", f"Ha ocurrido un error inesperado:\n{e}\n\nDetalles guardados en:\n{error_log}")
