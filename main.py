"""Arranque: uvicorn en un hilo demonio + una ventana de escritorio.

    python main.py
"""

import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn
import webview

import app as backend

# El 9765 está lejos de los puertos donde trabajas con otras cosas (8188 y
# compañía). Es fijo a propósito: Tailscale apunta ahí y la dirección del móvil
# no puede cambiar de un arranque a otro. Si cambias esto, cámbialo también en
# README.md.
PUERTO = 9765
ESPERA_MAXIMA = 20  # segundos


def comprobar_puerto(puerto=PUERTO):
    """El puerto es siempre el mismo. Si está ocupado, se dice y no se arranca."""
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", puerto))
        except OSError:
            raise SystemExit(
                f"El puerto {puerto} está ocupado y Relaciones no usa ningún otro.\n"
                "Cierra lo que lo esté usando y vuelve a abrir la app."
            )
    return puerto


def ips_locales():
    try:
        return socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return []


def servidor(puerto):
    uvicorn.run(backend.app, host="0.0.0.0", port=puerto, log_level="warning")


def espera_a_que_responda(puerto):
    limite = time.monotonic() + ESPERA_MAXIMA
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{puerto}/salud", timeout=0.5
            ) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.15)
    return False


def aviso(texto):
    print(texto, flush=True)  # que se vea aunque la salida esté redirigida


def mostrar_error(error):
    """Explica los fallos aunque el ejecutable no tenga una consola detrás."""
    carpeta = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    registro = carpeta / "relaciones-error.txt"
    registro.write_text(traceback.format_exc(), encoding="utf-8")
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            f"No se ha podido abrir Relaciones.\n\n{error}\n\n"
            f"Se han guardado más detalles en:\n{registro}",
            "Relaciones",
            0x10,
        )
    except Exception:
        pass


def main():
    nueva = backend.preparar()
    puerto = comprobar_puerto()

    aviso("Relaciones")
    if nueva:
        aviso(f"  Base de datos nueva creada en {backend.RUTA_DB}")
    aviso(f"  Ventana y ordenador:  http://127.0.0.1:{puerto}")
    for ip in ips_locales():
        aviso(f"  Desde el móvil:       http://{ip}:{puerto}")
    aviso(f"  Llave para entrar desde la red: {backend.llave()}")
    aviso("  (127.0.0.1 entra sin llave; cualquier otra IP la pide una vez)")

    threading.Thread(target=servidor, args=(puerto,), daemon=True).start()
    if not espera_a_que_responda(puerto):
        raise SystemExit("El servidor no ha respondido. No abro la ventana.")

    webview.create_window(
        "Relaciones", f"http://127.0.0.1:{puerto}", width=1100, height=850
    )
    # El mismo icono que la app instalada en el móvil. La documentación de
    # pywebview dice que `icon` es sólo de GTK/QT, pero está desactualizada:
    # platforms/winforms.py lo aplica en Windows. `backend.BASE` sirve tanto
    # desde el código como desde el ejecutable empaquetado.
    icono = backend.BASE / "estatico" / "icono" / "relaciones.ico"
    webview.start(icon=str(icono) if icono.exists() else None)


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        if getattr(sys, "frozen", False):
            mostrar_error(error)
        else:
            raise
