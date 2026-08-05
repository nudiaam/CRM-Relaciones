# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata


raiz = Path(SPECPATH)
datos = [
    (str(raiz / "plantillas"), "plantillas"),
    (str(raiz / "estatico"), "estatico"),
]
binarios = []
ocultos = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]

for paquete in (
    "av",
    "ctranslate2",
    "faster_whisper",
    "onnxruntime",
    "webview",
):
    datos_paquete, binarios_paquete, ocultos_paquete = collect_all(paquete)
    datos += datos_paquete
    binarios += binarios_paquete
    ocultos += ocultos_paquete

for distribucion in (
    "ctranslate2",
    "faster-whisper",
    "huggingface-hub",
    "onnxruntime",
    "pywebview",
    "tokenizers",
):
    datos += copy_metadata(distribucion)

analisis = Analysis(
    [str(raiz / "main.py")],
    pathex=[str(raiz)],
    binaries=binarios,
    datas=datos,
    hiddenimports=ocultos,
    excludes=["torch", "tensorflow"],
    noarchive=False,
)
pyz = PYZ(analisis.pure)

exe = EXE(
    pyz,
    analisis.scripts,
    analisis.binaries,
    analisis.datas,
    [],
    name="Relaciones",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(raiz / "estatico" / "icono" / "relaciones.ico"),
)
