import os
import sys
import time
import socket
import subprocess
import webbrowser

PORT = 8000
APP_URL = f"http://localhost:{PORT}"

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def launch_browser():
    edge_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    chrome_candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    for edge in edge_candidates:
        if os.path.isfile(edge):
            subprocess.Popen([edge, f"--app={APP_URL}"])
            return

    for chrome in chrome_candidates:
        if os.path.isfile(chrome):
            subprocess.Popen([chrome, f"--app={APP_URL}"])
            return

    webbrowser.open(APP_URL)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 1. Si no está corriendo el servidor, lo iniciamos en segundo plano
    if not is_port_open(PORT):
        py_exe = sys.executable
        if py_exe.lower().endswith("pythonw.exe"):
            py_std = py_exe[:-5] + ".exe"
            if os.path.isfile(py_std):
                py_exe = py_std

        # Iniciar uvicorn con redirección para evitar crash en modo detached
        flags = 0
        if sys.platform == "win32":
            flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            [py_exe, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=script_dir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags
        )

        # 2. Esperar a que el servidor responda (máximo 15 segundos)
        for _ in range(30):
            time.sleep(0.5)
            if is_port_open(PORT):
                break

    # 3. Abrir la ventana de la aplicación
    launch_browser()

if __name__ == "__main__":
    main()
