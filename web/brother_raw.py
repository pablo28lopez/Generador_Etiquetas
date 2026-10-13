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


def find_brother_printer(preferred_name: Optional[str] = None) -> Optional[str]:
    """Busca automáticamente una impresora Brother QL instalada en el sistema."""
    printers = list_installed_printers()
    if not printers:
        return preferred_name

    # 1. Si se especificó un nombre preferido y existe
    if preferred_name and preferred_name in printers:
        return preferred_name

    # 2. Buscar 'Brother QL-800'
    for p in printers:
        if "QL-800" in p.upper():
            return p

    # 3. Buscar cualquier Brother QL
    for p in printers:
        p_u = p.upper()
        if "BROTHER" in p_u and "QL" in p_u:
            return p

    # 4. Buscar cualquier Brother
    for p in printers:
        if "BROTHER" in p.upper():
            return p

    # 5. Si no se encontró ninguna Brother, retornar la primera o preferred
    return preferred_name


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
    if is_large:
        # Etiqueta Grande
        if roll_type == "continuous":
            label_id = "62"
        elif roll_type == "die-cut":
            label_id = "62x100"
        else:
            # Auto: preferir die-cut 62x100
            label_id = "62x100"
        target_size = (696, 1109)
    else:
        # Etiqueta Chica
        if roll_type == "continuous":
            label_id = "62"
        elif roll_type == "die-cut":
            label_id = "62x29"
        else:
            # Auto: preferir die-cut 62x29
            label_id = "62x29"
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
