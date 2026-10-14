"""
Módulo de Impresión Directa por Comandos Nativos (RAW) para Brother QL-800 / QL Series
====================================================================================
Este módulo genera los comandos de raster binario (ESC/P y Brother Raster) directamente
y los envía a la impresora física mediante la API nativa de Windows Spooler (winspool.drv)
utilizando el tipo de datos 'RAW'.

Ventajas:
- OMIRE COMPLETAMENTE EL DRIVER DE WINDOWS.
- NO muestra diálogo de impresión de Chrome/Edge.
- NO produce error de papel/medida no coincidente (Paper Mismatch).
- Impresión 100% silenciosa, ultrarrápida y con corte automático.
"""

import sys
import ctypes
from ctypes import wintypes
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image

# Compatibilidad con Pillow >= 10 para brother_ql
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

try:
    from brother_ql.raster import BrotherQLRaster
    from brother_ql.conversion import convert
    from brother_ql.models import ALL_MODELS
    from brother_ql.labels import ALL_LABELS
    BROTHER_QL_AVAILABLE = True
except ImportError:
    BROTHER_QL_AVAILABLE = False


# ============================================================================
# ESTRUCTURAS Y LLAMADAS A WINSPOOL.DRV (WINDOWS RAW PRINTING)
# ============================================================================

class DOC_INFO_1(ctypes.Structure):
    _fields_ = [
        ("pDocName", wintypes.LPWSTR),
        ("pOutputFile", wintypes.LPWSTR),
        ("pDatatype", wintypes.LPWSTR),
    ]


class PRINTER_INFO_2(ctypes.Structure):
    _fields_ = [
        ("pServerName", wintypes.LPWSTR),
        ("pPrinterName", wintypes.LPWSTR),
        ("pShareName", wintypes.LPWSTR),
        ("pPortName", wintypes.LPWSTR),
        ("pDriverName", wintypes.LPWSTR),
        ("pComment", wintypes.LPWSTR),
        ("pLocation", wintypes.LPWSTR),
        ("pDevMode", ctypes.c_void_p),
        ("pSepFile", wintypes.LPWSTR),
        ("pPrintProcessor", wintypes.LPWSTR),
        ("pDatatype", wintypes.LPWSTR),
        ("pParameters", wintypes.LPWSTR),
        ("pSecurityDescriptor", ctypes.c_void_p),
        ("Attributes", wintypes.DWORD),
        ("Priority", wintypes.DWORD),
        ("DefaultPriority", wintypes.DWORD),
        ("StartTime", wintypes.DWORD),
        ("UntilTime", wintypes.DWORD),
        ("Status", wintypes.DWORD),
        ("cJobs", wintypes.DWORD),
        ("AveragePPM", wintypes.DWORD),
    ]


def _init_winspool():
    if sys.platform != "win32":
        return None
    try:
        ws = ctypes.WinDLL("winspool.drv")
        ws.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
        ws.OpenPrinterW.restype = wintypes.BOOL

        ws.StartDocPrinterW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
        ws.StartDocPrinterW.restype = wintypes.DWORD

        ws.StartPagePrinter.argtypes = [wintypes.HANDLE]
        ws.StartPagePrinter.restype = wintypes.BOOL

        ws.WritePrinter.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        ws.WritePrinter.restype = wintypes.BOOL

        ws.EndPagePrinter.argtypes = [wintypes.HANDLE]
        ws.EndPagePrinter.restype = wintypes.BOOL

        ws.EndDocPrinter.argtypes = [wintypes.HANDLE]
        ws.EndDocPrinter.restype = wintypes.BOOL

        ws.ClosePrinter.argtypes = [wintypes.HANDLE]
        ws.ClosePrinter.restype = wintypes.BOOL

        return ws
    except Exception as e:
        print(f"[Aviso] No se pudo cargar winspool.drv: {e}")
        return None


winspool = _init_winspool()


def list_installed_printers() -> List[str]:
    """Lista los nombres de todas las impresoras instaladas en Windows."""
    if not winspool:
        return []

    PRINTER_ENUM_LOCAL = 0x00000002
    PRINTER_ENUM_CONNECTIONS = 0x00000004
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS

    needed = wintypes.DWORD(0)
    returned = wintypes.DWORD(0)

    winspool.EnumPrintersW(flags, None, 2, None, 0, ctypes.byref(needed), ctypes.byref(returned))
    if needed.value == 0:
        return []

    buf = ctypes.create_string_buffer(needed.value)
    res = winspool.EnumPrintersW(flags, None, 2, buf, needed.value, ctypes.byref(needed), ctypes.byref(returned))
    if not res:
        return []

    printers = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_2))
    names = []
    for i in range(returned.value):
        p_name = printers[i].pPrinterName
        if p_name:
            names.append(p_name)
    return names


import os
import socket
import time
import subprocess

_usb_cache = {"time": 0.0, "local_status": False}
_active_printer_cache = {"time": 0.0, "data": None}


def is_host_alive(host: str, port: int = 445, timeout: float = 0.3) -> bool:
    """Verifica en pocos milisegundos si un host remoto de Windows está encendido y accesible en la red."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        res = s.connect_ex((host, port))
        s.close()
        return res == 0
    except Exception:
        return False


def probe_printer_open(printer_name: str) -> bool:
    """Verifica si winspool.drv puede abrir la impresora especificada (local o en red)."""
    if not winspool or not printer_name:
        return False
    if printer_name.startswith(r"\\"):
        parts = printer_name.lstrip("\\").split("\\")
        host = parts[0]
        if not is_host_alive(host):
            return False
    handle = wintypes.HANDLE()
    try:
        ok = winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None)
        if ok and handle.value:
            winspool.ClosePrinter(handle)
            return True
        return False
    except Exception:
        return False


def is_brother_usb_local() -> bool:
    """Verifica si la impresora Brother QL está físicamente conectada por USB a este host local."""
    if sys.platform != "win32":
        return False
    now = time.time()
    if now - _usb_cache["time"] < 2.5:
        return _usb_cache["local_status"]

    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -like '*Brother*' -or $_.InstanceId -like '*04F9*' }).Count"],
            capture_output=True,
            text=True,
            timeout=4
        )
        count = int(res.stdout.strip() or 0)
        status = count > 0
        _usb_cache["time"] = now
        _usb_cache["local_status"] = status
        return status
    except Exception:
        return False


def get_active_brother_printer(preferred_name: Optional[str] = None, configured_remote_host: Optional[str] = None) -> Dict[str, Any]:
    """
    Detecta automáticamente la impresora Brother QL activa donde sea que esté conectada por puerto USB:
    1. Si está conectada por USB localmente en este host.
    2. Si está conectada por USB en una máquina compañera en red (ej: 10.12.70.89 o host configurado).
    
    Retorna un diccionario completo de estado y nombres para el frontend y los endpoints.
    """
    now = time.time()
    if not preferred_name and now - _active_printer_cache["time"] < 2.0 and _active_printer_cache["data"] is not None:
        return _active_printer_cache["data"]

    local_host = os.environ.get("COMPUTERNAME") or socket.gethostname()
    installed = list_installed_printers()

    # 1. Si se solicitó un nombre preferido y es alcanzable
    if preferred_name:
        is_pref_remote = preferred_name.startswith(r"\\")
        if is_pref_remote:
            if probe_printer_open(preferred_name):
                parts = preferred_name.lstrip("\\").split("\\")
                r_host = parts[0]
                return {
                    "detected_brother": preferred_name,
                    "brother_found": True,
                    "connected": True,
                    "host_name": r_host,
                    "is_remote": True,
                    "location": f"USB en Red ({r_host})"
                }
        else:
            local_ok = is_brother_usb_local()
            return {
                "detected_brother": preferred_name,
                "brother_found": True,
                "connected": local_ok,
                "host_name": local_host,
                "is_remote": False,
                "location": f"USB Local ({local_host})" if local_ok else "Desconectada"
            }

    # 2. Verificar si está conectada físicamente por USB a esta máquina local
    if is_brother_usb_local():
        local_target = None
        for p in installed:
            if not p.startswith(r"\\") and "QL-800" in p.upper():
                local_target = p
                break
        if not local_target:
            for p in installed:
                if not p.startswith(r"\\") and "BROTHER" in p.upper():
                    local_target = p
                    break
        local_target = local_target or "Brother QL-800"

        res = {
            "detected_brother": local_target,
            "brother_found": True,
            "connected": True,
            "host_name": local_host,
            "is_remote": False,
            "location": f"USB Local ({local_host})"
        }
        _active_printer_cache["time"] = now
        _active_printer_cache["data"] = res
        return res

    # 3. Si NO está por USB local, comprobar impresoras Brother en red conocidas / conectadas
    network_candidates = []

    # a) Si hay un host configurado manualmente por el usuario en "En Red", probarlo en PRIMER lugar
    if configured_remote_host:
        clean_cfg = configured_remote_host.replace("http://", "").replace("https://", "").split(":")[0].strip()
        if clean_cfg:
            cand = rf"\\{clean_cfg}\Brother QL-800"
            if cand not in network_candidates:
                network_candidates.append(cand)

    # b) Si hay impresoras instaladas en Windows que son de red y contienen Brother
    for p in installed:
        if p.startswith(r"\\") and "BROTHER" in p.upper():
            if p not in network_candidates:
                network_candidates.append(p)

    # c) IP conocida de la máquina del compañero donde se trasladó la impresora
    known_coworker = r"\\10.12.70.89\Brother QL-800"
    if known_coworker not in network_candidates:
        network_candidates.append(known_coworker)

    for cand in network_candidates:
        if probe_printer_open(cand):
            parts = cand.lstrip("\\").split("\\")
            r_host = parts[0]

            # Si la conexión de red aún no está registrada en Windows, registrarla en segundo plano
            if cand not in installed and sys.platform == "win32":
                try:
                    subprocess.Popen(
                        ["powershell", "-NoProfile", "-Command", f'Add-Printer -ConnectionName "{cand}" -ErrorAction SilentlyContinue'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

            res = {
                "detected_brother": cand,
                "brother_found": True,
                "connected": True,
                "host_name": r_host,
                "is_remote": True,
                "location": f"USB en Red ({r_host})"
            }
            _active_printer_cache["time"] = now
            _active_printer_cache["data"] = res
            return res

    # 4. Fallback: No está conectada ni localmente ni en red
    fallback_p = "Brother QL-800"
    for p in installed:
        if "QL-800" in p.upper():
            fallback_p = p
            break
        elif "BROTHER" in p.upper():
            fallback_p = p

    res = {
        "detected_brother": fallback_p,
        "brother_found": True,
        "connected": False,
        "host_name": local_host,
        "is_remote": False,
        "location": "Desconectada"
    }
    _active_printer_cache["time"] = now
    _active_printer_cache["data"] = res
    return res


def find_brother_printer(preferred_name: Optional[str] = None) -> Optional[str]:
    """Busca automáticamente la impresora Brother QL activa (local o en red)."""
    info = get_active_brother_printer(preferred_name=preferred_name)
    return info.get("detected_brother") or preferred_name or "Brother QL-800"


def is_brother_usb_connected(printer_name: Optional[str] = None) -> bool:
    """Verifica si la impresora Brother QL está conectada por USB (en este equipo o en red)."""
    info = get_active_brother_printer(preferred_name=printer_name)
    return bool(info.get("connected", False))


def clear_printer_cache():
    """Limpia la memoria caché de estado de impresora para refresco inmediato."""
    _active_printer_cache["time"] = 0.0
    _active_printer_cache["data"] = None
    _usb_cache["time"] = 0.0


def draw_printer_icon(draw, cx, cy, size=40, fill="black"):
    """Dibuja un icono vectorial nítido de impresora térmica para las etiquetas."""
    half = size // 2
    x0 = int(cx - half)
    y0 = int(cy - half * 0.3)
    x1 = int(cx + half)
    y1 = int(cy + half * 0.5)

    # Entrada de papel superior
    draw.rectangle([cx - half * 0.6, cy - half * 0.9, cx + half * 0.6, y0], outline=fill, width=2)
    # Cuerpo principal de la impresora
    draw.rounded_rectangle([x0, y0, x1, y1], radius=4, outline=fill, width=3)
    # LED de estado
    draw.ellipse([x1 - 9, y0 + 5, x1 - 4, y0 + 10], fill=fill)
    # Salida de papel
    draw.rectangle([cx - half * 0.65, y0 + 8, cx + half * 0.65, y1 + half * 0.45], fill="white" if fill != "white" else "black", outline=fill, width=2)
    # Líneas de texto impreso saliendo
    draw.line([cx - half * 0.4, y0 + 14, cx + half * 0.4, y0 + 14], fill=fill, width=2)
    draw.line([cx - half * 0.4, y0 + 20, cx + half * 0.2, y0 + 20], fill=fill, width=2)


def generate_test_label_image(host_name: str = "Servidor", printer_name: str = "Brother QL-800") -> Image.Image:
    """Genera una imagen PIL de etiqueta de prueba 100% centrada y alineada con icono de impresora."""
    import datetime
    from PIL import ImageDraw, ImageFont

    w, h = 620, 290
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    margin = 8
    # Marcos exteriores
    draw.rectangle([margin, margin, w - margin, h - margin], outline="black", width=3)
    draw.rectangle([margin + 5, margin + 5, w - margin - 5, h - margin - 5], outline="black", width=1)

    try:
        font_title = ImageFont.truetype("arialbd.ttf", 25)
        font_sub = ImageFont.truetype("arialbd.ttf", 17)
        font_body = ImageFont.truetype("arial.ttf", 15)
        font_footer = ImageFont.truetype("arialbd.ttf", 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    # 1. Encabezado en Negro Inverso con Icono de Impresora y Título Centrado
    header_h = 56
    draw.rectangle([margin + 6, margin + 6, w - margin - 6, margin + 6 + header_h], fill="black")

    title_text = "TEST DE CONEXION BROTHER QL"
    tb = draw.textbbox((0, 0), title_text, font=font_title)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]

    icon_w = 38
    gap = 14
    total_w = icon_w + gap + tw
    start_x = (w - total_w) // 2

    # Icono de impresora en blanco sobre fondo negro
    draw_printer_icon(draw, start_x + icon_w // 2, margin + 6 + header_h // 2, size=34, fill="white")
    draw.text((start_x + icon_w + gap, margin + 6 + (header_h - th) // 2 - tb[1]), title_text, fill="white", font=font_title)

    # 2. Subtítulo centrado
    sub_text = f"{printer_name.upper()}  -  CALIBRACION 62mm"
    sb = draw.textbbox((0, 0), sub_text, font=font_sub)
    sw = sb[2] - sb[0]
    draw.text(((w - sw) // 2, 82), sub_text, fill="black", font=font_sub)

    # Línea divisoria centrada
    draw.line([(w - 420) // 2, 112, (w + 420) // 2, 112], fill="black", width=2)

    # 3. Líneas de información 100% centradas
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    lines = [
        f"Host: {host_name}  |  Puerto: USB",
        f"Fecha y Hora: {now_str}",
        "Comunicación: RAW Bytecode Directo OK"
    ]

    curr_y = 124
    for line in lines:
        lb = draw.textbbox((0, 0), line, font=font_body)
        lw = lb[2] - lb[0]
        draw.text(((w - lw) // 2, curr_y), line, fill="black", font=font_body)
        curr_y += 27

    # 4. Pie de estado enmarcado en negro 100% centrado
    footer_text = "[ OK ] CONEXION Y COMUNICACION EXITOSA"
    fb = draw.textbbox((0, 0), footer_text, font=font_footer)
    fw = fb[2] - fb[0]
    fh = fb[3] - fb[1]

    pill_w = fw + 36
    pill_h = 32
    pill_x0 = (w - pill_w) // 2
    pill_y0 = 236
    draw.rounded_rectangle([pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h], radius=6, fill="black")
    draw.text(((w - fw) // 2, pill_y0 + (pill_h - fh) // 2 - fb[1]), footer_text, fill="white", font=font_footer)

    return img


def send_raw_to_printer(printer_name: str, raw_data: bytes, doc_name: str = "Etiquetas Brother QL") -> int:
    """Envía un flujo de bytes crudos (RAW) directamente a la impresora usando winspool.drv."""
    if not winspool:
        raise RuntimeError("winspool.drv solo está disponible en sistemas Microsoft Windows.")

    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None):
        err = ctypes.GetLastError()
        raise RuntimeError(f"No se pudo abrir la impresora '{printer_name}'. Código de error Windows: {err}")

    try:
        doc_info = DOC_INFO_1(
            pDocName=doc_name,
            pOutputFile=None,
            pDatatype="RAW"
        )
        job_id = winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc_info))
        if job_id <= 0:
            err = ctypes.GetLastError()
            raise RuntimeError(f"Error al iniciar trabajo de impresión en '{printer_name}'. Código: {err}")

        try:
            if not winspool.StartPagePrinter(handle):
                err = ctypes.GetLastError()
                raise RuntimeError(f"Error en StartPagePrinter: {err}")

            written = wintypes.DWORD(0)
            if not winspool.WritePrinter(handle, raw_data, len(raw_data), ctypes.byref(written)):
                err = ctypes.GetLastError()
                raise RuntimeError(f"Error en WritePrinter: {err}")

            winspool.EndPagePrinter(handle)
            return written.value
        finally:
            winspool.EndDocPrinter(handle)
    finally:
        winspool.ClosePrinter(handle)


# ============================================================================
# CONVERSIÓN DE IMÁGENES PIL A COMANDOS BINARIOS RASTER BROTHER QL
# ============================================================================

def convert_images_to_brother_raster(
    images: List[Image.Image],
    size: str = "60x30",
    roll_type: str = "auto",
    model: str = "QL-800",
    cut_each: bool = True
) -> bytes:
    """
    Convierte una lista de imágenes PIL al flujo de comandos binarios nativos de Brother QL.
    
    Parámetros:
    - images: Lista de PIL.Image.Image en modo RGB o L.
    - size: '60x30' (o '62x29') / '60x95' (o '62x100').
    - roll_type: 'auto', 'die-cut' (troquelado), 'continuous' (rollo continuo 62mm).
    - model: Modelo de Brother QL ('QL-800', 'QL-700', etc.).
    - cut_each: Si es True, realiza el corte automático después de cada etiqueta.
    """
    if not BROTHER_QL_AVAILABLE:
        raise RuntimeError("El paquete brother_ql no está disponible en el servidor.")

    qlr = BrotherQLRaster(model)
    qlr.exception_on_warning = False

    is_large = size in ("60x95", "60x90", "62x100")

    # Determinar identificador de etiqueta para brother_ql
    # Por defecto se utiliza '62' (Cinta Continua 62mm DK-22205), que es el formato
    # instalado físicamente en la Brother QL-800 y permite imprimir tanto 29mm como 100mm con autocorte.
    if is_large:
        # Etiqueta Grande
        if roll_type == "die-cut":
            label_id = "62x100"
        else:
            label_id = "62"
        target_size = (696, 1109)
    else:
        # Etiqueta Chica
        if roll_type == "die-cut":
            label_id = "62x29"
        else:
            label_id = "62"
        target_size = (696, 271)

    # Preparar cada imagen con la orientación y dimensiones de puntos exactas del cabezal térmico
    prepared_images = []
    for img in images:
        # Asegurar modo RGB
        im = img.convert("RGB")
        if is_large:
            # La etiqueta grande se diseñó horizontal (ancho > alto, ej. 1000x620).
            # Para el cabezal de 62 mm (696 dots de ancho), debe rotarse 90 grados:
            if im.width > im.height:
                im = im.resize((1109, 696), Image.Resampling.LANCZOS)
                im = im.rotate(90, expand=True)
            else:
                im = im.resize(target_size, Image.Resampling.LANCZOS)
        else:
            # La etiqueta chica se redimensiona a (696, 271)
            im = im.resize(target_size, Image.Resampling.LANCZOS)

        prepared_images.append(im)

    # Convertir a comandos binarios RAW con brother_ql
    raw_bytes = convert(
        qlr=qlr,
        images=prepared_images,
        label=label_id,
        cut=cut_each
    )

    # Eliminar solicitud de estado ESC i S (b'\x1b\x69\x53')
    # En el Spooler de Windows en modo RAW unidireccional, ESC i S hace que la impresora
    # devuelva un paquete de 32 bytes que nunca se lee del endpoint USB IN, lo que provoca
    # que la impresora se trabe o parpadee en error esperando respuesta del host.
    raw_bytes = raw_bytes.replace(b'\x1b\x69\x53', b'')

    return raw_bytes
