"""Comprueba que el mapa sigue siendo cierto y que se cumple la norma de modos.

    python mapa/comprobar.py

No reescribe nada. Dice en qué línea está ahora cada ancla del mapa, avisa de
las que ya no existen, y lista los estados invertidos pintados con tinta cruda.
Sólo biblioteca estándar: este proyecto no lleva npm ni build.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MAPA = RAIZ / "mapa"

# Anclas: texto que debe seguir existiendo, y en qué archivo.
ANCLAS = {
    "app.py": [
        'ESQUEMA = """', "def poner_al_dia", "def cuanto", "async def puerta",
        "NOMBRE_VISIBLE_SQL", "ORDENES = {", "PERSONAS_POR_PAGINA",
        "QUEDADAS_POR_PAGINA", "FALLOS_FOTO = {", "async def cambiar_foto",
        "TABLAS_EXPORTABLES", "CIRCULOS_DE_FABRICA",
    ],
    "main.py": [
        "PUERTO = 9765", "def comprobar_puerto", "def servidor",
        "def espera_a_que_responda", "def mostrar_error",
    ],
    "estatico/estilo.css": [
        ".ficha {", ".bloque-cabecera {", 'data-edicion="no"',
        ".bloque-identidad {", ".vistazo {", ".lineas {",
        ".accion-eliminar:hover", ".opciones {", ".fecha-atajos {",
        "--inverso-fondo", "--alarma",
    ],
    "estatico/app.js": [
        "function enfocar", "// 9 bis.", "// 9 ter.", "// 10.", "// 11.",
    ],
    "estatico/grafo.js": [
        "function colocar", "function pintar", "function prepararMandos",
        "function montarCirculos", "var toques = new Map",
        "function protegerDelToque", "function verFicha",
    ],
    "plantillas/ficha.html": [
        "{% macro cabecera(", "{% macro hilo_linea(", "bloque-identidad",
        'cabecera("De un vistazo"', 'cabecera("Queda pendiente"',
        'cabecera("Relaciones"', 'class="zona-peligrosa"',
    ],
}

# Ids de la ficha que app.py usa para redirigir.
ANCLAS_REDIRECCION = ["atencion", "quedadas", "datos", "relaciones"]


def buscar(texto, aguja):
    for numero, linea in enumerate(texto.splitlines(), 1):
        if aguja in linea:
            return numero
    return None


def revisar_anclas():
    print("=== ANCLAS DEL MAPA ===")
    rotas = 0
    for archivo, agujas in ANCLAS.items():
        ruta = RAIZ / archivo
        if not ruta.exists():
            print(f"  FALTA EL ARCHIVO: {archivo}")
            rotas += len(agujas)
            continue
        texto = ruta.read_text(encoding="utf-8")
        perdidas = [a for a in agujas if buscar(texto, a) is None]
        estado = "ok" if not perdidas else f"{len(perdidas)} PERDIDAS"
        print(f"  {archivo}: {len(agujas)} anclas, {estado}")
        for a in perdidas:
            print(f"      no encuentro: {a!r}")
        rotas += len(perdidas)
    return rotas


def revisar_redirecciones():
    print("\n=== IDS QUE USA app.py PARA REDIRIGIR ===")
    ficha = (RAIZ / "plantillas" / "ficha.html").read_text(encoding="utf-8")
    fallos = 0
    for ident in ANCLAS_REDIRECCION:
        if f'id="{ident}"' not in ficha:
            print(f"  ROTO: ficha.html ya no tiene id={ident!r}")
            fallos += 1
    if not fallos:
        print("  ok: los cuatro siguen en ficha.html")
    return fallos


def revisar_norma_modos():
    """Estados invertidos con tinta cruda y sin corrección nocturna.

    Las reglas antiguas tienen su parche en la lista gigante de
    `html[data-modo="noche"]`. Esas no son deuda nueva: se toleran, pero la
    lista no crece (regla 3). Aquí sólo se avisa de las que no tienen parche.
    """
    print("\n=== NORMA DE LOS DOS MODOS ===")
    css = (RAIZ / "estatico" / "estilo.css").read_text(encoding="utf-8")

    parcheados = set()
    for bloque in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = bloque.group(1).strip()
        if "data-modo" not in selector:
            continue
        for parte in selector.split(","):
            limpio = re.sub(r'html\[data-modo="\w+"\]\s*', "", parte).strip()
            if limpio:
                parcheados.add(" ".join(limpio.split()))

    def tiene_parche(sel):
        sel = " ".join(sel.split())
        # `.ventana-titulo` puede estar parcheado como
        # `.grafo-mandos > .ventana-titulo`: vale si algún parche lo termina.
        return any(p == sel or p.endswith(" " + sel) or p.endswith("> " + sel)
                   for p in parcheados)

    # Marcas pequeñas admitidas por la regla 2: pseudoelementos.
    permitido = re.compile(r"::(before|after)\b")
    sospechosas = []
    for bloque in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, cuerpo = bloque.group(1).strip(), bloque.group(2)
        if selector.startswith("@") or "data-modo" in selector:
            continue
        if not re.search(r"background(-color)?:\s*var\(--tinta\)", cuerpo):
            continue
        if permitido.search(selector):
            continue
        partes = [p.strip() for p in selector.split(",") if p.strip()]
        if all(tiene_parche(p) for p in partes):
            continue
        sospechosas.append(" ".join(selector.split())[:80])

    if sospechosas:
        print(f"  {len(sospechosas)} superficies rellenas sin corrección nocturna:")
        for s in sospechosas:
            print(f"      {s}")
        print("  (deben usar var(--inverso-fondo) / var(--inverso-texto))")
    else:
        print("  ok: ninguna superficie rellena queda sin resolver")
    return len(sospechosas)


def revisar_botones_destructivos():
    """Todo botón que borre algo lleva `accion-eliminar`, o no se pone rojo."""
    print("\n=== BOTONES QUE BORRAN ===")
    destructivo = re.compile(r"quitar|eliminar|borrar", re.I)
    sueltos = []
    total = 0
    for ruta in sorted((RAIZ / "plantillas").glob("*.html")):
        texto = ruta.read_text(encoding="utf-8")
        for etiqueta in re.finditer(r"<button\b[^>]*>(.*?)</button>", texto, re.S):
            rotulo = re.sub(r"<[^>]+>|\{[{%].*?[}%]\}", "", etiqueta.group(1))
            rotulo = " ".join(rotulo.split())
            if not destructivo.search(rotulo):
                continue
            total += 1
            if "accion-eliminar" not in etiqueta.group(0):
                linea = texto[: etiqueta.start()].count("\n") + 1
                sueltos.append(f"{ruta.name}:{linea}  {rotulo[:40]!r}")
    if sueltos:
        print(f"  {len(sueltos)} de {total} sin la clase `accion-eliminar`:")
        for s in sueltos:
            print(f"      {s}")
    else:
        print(f"  ok: los {total} llevan `accion-eliminar`")
    return len(sueltos)


def revisar_hover():
    print("\n=== :hover SÓLO CON RATÓN ===")
    css = (RAIZ / "estatico" / "estilo.css").read_text(encoding="utf-8")
    fuera = 0
    profundidad_hover = []
    profundidad = 0
    i = 0
    pendiente = ""
    while i < len(css):
        if css.startswith("/*", i):
            i = css.find("*/", i) + 2
            continue
        c = css[i]
        if c == "{":
            cabecera = " ".join(pendiente.split())
            if cabecera.startswith("@media") and "hover: hover" in cabecera:
                profundidad_hover.append(profundidad)
            elif ":hover" in cabecera and not profundidad_hover:
                fuera += 1
            profundidad += 1
            pendiente = ""
        elif c == "}":
            profundidad -= 1
            if profundidad_hover and profundidad_hover[-1] == profundidad:
                profundidad_hover.pop()
            pendiente = ""
        else:
            pendiente += c
        i += 1
    if fuera:
        print(f"  {fuera} reglas :hover fuera de @media (hover: hover)")
    else:
        print("  ok: todas dentro de @media (hover: hover)")
    return fuera


if __name__ == "__main__":
    total = (revisar_anclas() + revisar_redirecciones()
             + revisar_norma_modos() + revisar_botones_destructivos()
             + revisar_hover())
    print()
    if total:
        print(f"{total} cosas que revisar. El mapa o el código se han movido.")
        sys.exit(1)
    print("Todo cuadra.")
