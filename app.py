"""Relaciones — backend completo. Ver CLAUDE.md antes de tocar nada.

Sin ORM y sin API JSON: formularios POST y redirección 303. La única excepción
es GET /api/grafo, para que grafo.js tenga qué dibujar.

El esquema se crea al arrancar si no existe. Las bases hechas con versiones
anteriores se ponen al día en poner_al_dia(), que es idempotente.
"""

import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from base64 import b64decode, b64encode
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Al ejecutar desde Python, recursos y datos viven junto al código. En el
# ejecutable autónomo, PyInstaller extrae los recursos a una carpeta temporal,
# pero los datos deben seguir junto al .exe para que nunca se pierdan al cerrar.
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
BASE_DATOS = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RUTA_DB = BASE_DATOS / "datos.db"

# Un círculo es de dónde conozco a alguien: amigos, familia, trabajo, barrio,
# hípica, universidad. Uno solo por persona, y la única forma de clasificar
# gente que existe en la aplicación.
CIRCULOS_DE_FABRICA = ("Amigos", "Familia", "Trabajo", "Barrio")

# Lo que queda pendiente lo tengo que hacer yo; por lo otro tengo que preguntar.
TIPOS = ("pendiente", "preguntar")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS circulo (
    id      INTEGER PRIMARY KEY,
    nombre  TEXT NOT NULL,
    orden   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS persona (
    id            INTEGER PRIMARY KEY,
    nombre        TEXT NOT NULL,
    apodo         TEXT,
    circulo_id    INTEGER REFERENCES circulo(id) ON DELETE SET NULL,
    color         TEXT,
    cumple        TEXT,
    notas_rapidas TEXT,
    foto          TEXT,
    creada        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hecho (
    id         INTEGER PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    texto      TEXT NOT NULL,
    creado     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hilo (
    id            INTEGER PRIMARY KEY,
    persona_id    INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    texto         TEXT NOT NULL,
    abierto_desde TEXT NOT NULL,
    cerrado_el    TEXT,
    tipo          TEXT NOT NULL DEFAULT 'preguntar'
);
CREATE TABLE IF NOT EXISTS nota (
    id      INTEGER PRIMARY KEY,
    fecha   TEXT NOT NULL,
    canal   TEXT,
    texto   TEXT NOT NULL,
    resumen TEXT,
    creada  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nota_persona (
    nota_id    INTEGER NOT NULL REFERENCES nota(id) ON DELETE CASCADE,
    persona_id INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    PRIMARY KEY (nota_id, persona_id)
);
CREATE TABLE IF NOT EXISTS relacion (
    persona_a        INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    persona_b        INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    etiqueta         TEXT NOT NULL,
    etiqueta_inversa TEXT,
    PRIMARY KEY (persona_a, persona_b)
);
CREATE TABLE IF NOT EXISTS ajuste (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audio (
    id                    INTEGER PRIMARY KEY,
    archivo               TEXT NOT NULL,
    grabado               TEXT NOT NULL,
    estado                TEXT NOT NULL DEFAULT 'pendiente',
    transcripcion         TEXT,
    transcripcion_editada INTEGER NOT NULL DEFAULT 0,
    borrador              TEXT,
    error                 TEXT,
    actualizado           TEXT,
    contrato_version      INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audio_registro (
    audio_id    INTEGER NOT NULL REFERENCES audio(id) ON DELETE CASCADE,
    tipo        TEXT NOT NULL,
    registro_id INTEGER NOT NULL,
    persona_id  INTEGER NOT NULL REFERENCES persona(id) ON DELETE CASCADE,
    PRIMARY KEY (audio_id, tipo, registro_id, persona_id)
);
"""

TABLAS_EXPORTABLES = (
    "circulo", "persona", "hecho", "hilo", "nota", "nota_persona", "relacion",
)

# Los audios son archivos sueltos junto a la base, nunca dentro de ella. La
# carpeta viaja con el .exe igual que datos.db, y queda fuera de git y de la
# copia de todo porque contiene voz. De momento no se procesan: sólo se guardan.
CARPETA_AUDIOS = BASE_DATOS / "audios"
CARPETA_AUDIOS_BORRADOS = BASE_DATOS / ".audios-borrados"
MAX_AUDIO_BYTES = 60 * 1024 * 1024  # una hora de voz en Opus cabe de sobra
MODELO_WHISPER = "large-v3"
MODELO_QWEN = "qwen3:14b"
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
MAX_TOKENS_QWEN_PENSANDO = 4096
MAX_TOKENS_QWEN_DIRECTO = 8192
ESPERA_QWEN_SEGUNDOS = 180
CONTRATO_BORRADOR = 2

# El navegador decide el contenedor según el móvil: Opus en webm/ogg donde se
# puede (Android), mp4/AAC donde no (iPhone). El servidor no transcodifica; sólo
# le pone la extensión que corresponde al tipo que llega.
EXT_POR_MIME = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/aac": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}


# --------------------------------------------------------------------------
# base de datos
# --------------------------------------------------------------------------

def conexion():
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def poner_al_dia(con):
    """Pone al día una base de una versión anterior. Se puede repetir sin daño.

    - Los temas ("de qué habláis") desaparecen: el círculo hace ese trabajo.
    - hilo.mio (sí/no) pasa a hilo.tipo: lo que era mío queda pendiente, el
      resto pasa a ser algo por lo que preguntar.
    - De los tres círculos viejos, Núcleo pasa a llamarse Amigos, y Cerca y
      Órbita se van si no tienen a nadie dentro.
    """
    tablas = {f["name"] for f in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    for sobra in ("nota_tema", "tema"):
        if sobra in tablas:
            con.execute(f"DROP TABLE {sobra}")

    columnas = {f["name"] for f in con.execute("PRAGMA table_info(hilo)")}
    if "mio" in columnas:
        if "tipo" not in columnas:
            con.execute(
                "ALTER TABLE hilo ADD COLUMN tipo TEXT NOT NULL DEFAULT 'preguntar'"
            )
        con.execute("UPDATE hilo SET tipo = 'pendiente' WHERE mio = 1")
        con.execute("ALTER TABLE hilo DROP COLUMN mio")

    columnas_persona = {
        f["name"] for f in con.execute("PRAGMA table_info(persona)")
    }
    if "foto" not in columnas_persona:
        con.execute("ALTER TABLE persona ADD COLUMN foto TEXT")

    columnas_nota = {
        f["name"] for f in con.execute("PRAGMA table_info(nota)")
    }
    if "resumen" not in columnas_nota:
        con.execute("ALTER TABLE nota ADD COLUMN resumen TEXT")

    columnas_audio = {
        f["name"] for f in con.execute("PRAGMA table_info(audio)")
    }
    columnas_audio_nuevas = {
        "transcripcion": "TEXT",
        "transcripcion_editada": "INTEGER NOT NULL DEFAULT 0",
        "borrador": "TEXT",
        "error": "TEXT",
        "actualizado": "TEXT",
        "contrato_version": "INTEGER NOT NULL DEFAULT 1",
    }
    for nombre, definicion in columnas_audio_nuevas.items():
        if nombre not in columnas_audio:
            con.execute(f"ALTER TABLE audio ADD COLUMN {nombre} {definicion}")

    # Si la app se cerró con un modelo trabajando, se retoma sin perder la
    # transcripción que ya estuviera terminada.
    con.execute(
        "UPDATE audio SET estado = 'pendiente' WHERE estado = 'transcribiendo'"
    )
    con.execute(
        "UPDATE audio SET estado = 'analisis_pendiente' "
        "WHERE estado = 'analizando' AND transcripcion IS NOT NULL"
    )

    viejos = {f["nombre"]: f["id"] for f in con.execute(
        "SELECT id, nombre FROM circulo"
    )}
    if "Núcleo" in viejos and "Amigos" not in viejos:
        con.execute(
            "UPDATE circulo SET nombre = 'Amigos' WHERE id = ?", (viejos["Núcleo"],)
        )
    for vacio in ("Cerca", "Órbita"):
        if vacio in viejos:
            con.execute(
                "DELETE FROM circulo WHERE id = ?"
                " AND NOT EXISTS (SELECT 1 FROM persona WHERE circulo_id = ?)",
                (viejos[vacio], viejos[vacio]),
            )


def fecha_del_nombre_audio(ruta):
    coincidencia = re.match(r"^(\d{8})-(\d{6})-", ruta.name)
    if coincidencia:
        try:
            return datetime.strptime(
                "".join(coincidencia.groups()), "%Y%m%d%H%M%S"
            ).isoformat(timespec="seconds")
        except ValueError:
            pass
    return datetime.fromtimestamp(ruta.stat().st_mtime).isoformat(timespec="seconds")


def reconciliar_audios(con):
    """Mantiene una relación uno-a-uno entre `audio` y los archivos reales.

    Los archivos sin fila se recuperan como pendientes. Las filas sin archivo y
    los duplicados se retiran porque no tienen una grabación distinta que servir.
    Los temporales de una subida o un borrado no cuentan como grabaciones.
    """
    extensiones = set(EXT_POR_MIME.values())
    archivos = {
        ruta.name: ruta for ruta in CARPETA_AUDIOS.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in extensiones
    }
    enlazados = set()
    for fila in con.execute(
        "SELECT id, archivo FROM audio ORDER BY id DESC"
    ).fetchall():
        nombre = Path(fila["archivo"]).name
        if nombre not in archivos or nombre in enlazados:
            con.execute("DELETE FROM audio WHERE id = ?", (fila["id"],))
        else:
            enlazados.add(nombre)

    for nombre, ruta in archivos.items():
        if nombre not in enlazados:
            con.execute(
                "INSERT INTO audio (archivo, grabado, estado) "
                "VALUES (?, ?, 'pendiente')",
                (nombre, fecha_del_nombre_audio(ruta)),
            )
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS audio_archivo_unico ON audio(archivo)"
    )


def preparar():
    """Crea el esquema y las semillas si hace falta. Idempotente."""
    nueva = not RUTA_DB.exists()
    CARPETA_AUDIOS.mkdir(exist_ok=True)
    con = conexion()
    with con:
        con.executescript(ESQUEMA)
        con.execute("PRAGMA journal_mode = WAL")
        poner_al_dia(con)
        reconciliar_audios(con)
        if nueva:
            for i, nombre in enumerate(CIRCULOS_DE_FABRICA):
                con.execute(
                    "INSERT INTO circulo (nombre, orden) VALUES (?, ?)", (nombre, i)
                )
        if not con.execute(
            "SELECT 1 FROM ajuste WHERE clave = 'llave'"
        ).fetchone():
            con.execute(
                "INSERT INTO ajuste (clave, valor) VALUES ('llave', ?)",
                (secrets.token_hex(4),),
            )
    con.close()
    return nueva


def llave():
    con = conexion()
    fila = con.execute("SELECT valor FROM ajuste WHERE clave = 'llave'").fetchone()
    con.close()
    return fila["valor"] if fila else ""


# --------------------------------------------------------------------------
# fechas: ISO dentro, lenguaje natural fuera
# --------------------------------------------------------------------------

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def hoy_iso():
    return date.today().isoformat()


def ahora_iso():
    return datetime.now().isoformat(timespec="seconds")


def _dias_desde(iso):
    try:
        return (date.today() - date.fromisoformat(str(iso)[:10])).days
    except (TypeError, ValueError):
        return None


CIFRAS = ("cero", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete",
          "ocho", "nueve", "diez", "once", "doce")


def _palabra(n):
    return CIFRAS[n] if n < len(CIFRAS) else str(n)


def cuanto(iso):
    """Sin el 'hace' delante: 'dos días', 'tres semanas', 'nunca'.

    Va donde el rótulo ya dice hace ("hablamos hace"), para no repetirlo.
    """
    if not iso:
        return "nunca"
    n = _dias_desde(iso)
    if n is None:
        return str(iso)
    if n < 0:
        return "está por venir"
    if n == 0:
        return "hoy"
    if n == 1:
        return "un día"
    if n < 7:
        return f"{_palabra(n)} días"
    if n < 14:
        return "una semana"
    if n < 31:
        return f"{_palabra(n // 7)} semanas"
    if n < 62:
        return "un mes"
    if n < 365:
        return f"{_palabra(n // 30)} meses"
    if n < 730:
        return "un año"
    return f"{_palabra(n // 365)} años"


def hace(iso):
    """'nunca', 'hoy', 'ayer', 'hace tres semanas'…"""
    if not iso:
        return "nunca"
    n = _dias_desde(iso)
    if n == 0:
        return "hoy"
    if n == 1:
        return "ayer"
    dicho = cuanto(iso)
    return dicho if dicho in ("nunca", "está por venir") else f"hace {dicho}"


def fecha_natural(iso):
    """'25 de julio' si es de este año, '25 de julio de 2024' si no."""
    if not iso:
        return ""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return str(iso)
    if d.year == date.today().year:
        return f"{d.day} de {MESES[d.month - 1]}"
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def cumple_natural(iso):
    """Acepta 'YYYY-MM-DD' y '--MM-DD' (cumpleaños sin año)."""
    if not iso:
        return ""
    m = re.fullmatch(r"(?:(\d{4})|-)?-(\d{2})-(\d{2})", str(iso).strip())
    if not m:
        return str(iso)
    anio, mes, dia = m.group(1), int(m.group(2)), int(m.group(3))
    if not 1 <= mes <= 12:
        return str(iso)
    texto = f"{dia} de {MESES[mes - 1]}"
    return f"{texto} de {anio}" if anio else texto


MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep",
                "oct", "nov", "dic")


def fecha_corta(iso):
    """'22 jul' si es de este año, '22 jul 2024' si no. Para los datos fríos."""
    if not iso:
        return ""
    try:
        d = date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return str(iso)
    corta = f"{d.day} {MESES_CORTOS[d.month - 1]}"
    return corta if d.year == date.today().year else f"{corta} {d.year}"


def cumple_iso(texto):
    """Normaliza lo que se escriba en el campo cumpleaños. '' si no se entiende."""
    texto = (texto or "").strip()
    if not texto:
        return ""
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?", texto)
    if m:
        dia, mes, anio = int(m.group(1)), int(m.group(2)), m.group(3)
        cabeza = f"{int(anio):04d}" if anio else "-"
        return f"{cabeza}-{mes:02d}-{dia:02d}"
    return ""


# --------------------------------------------------------------------------
# aplicación
# --------------------------------------------------------------------------

preparar()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/estatico", StaticFiles(directory=BASE / "estatico"), name="estatico")

plantillas = Jinja2Templates(directory=BASE / "plantillas")
plantillas.env.filters["hace"] = hace
plantillas.env.filters["cuanto"] = cuanto
plantillas.env.filters["fecha"] = fecha_natural
plantillas.env.filters["corta"] = fecha_corta
plantillas.env.filters["cumple"] = cumple_natural

# El navegador pide el manifest y el service worker antes de tener la cookie
# de la llave, así que entran sin ella. No revelan nada: sólo nombre e iconos.
LIBRES = ("/entrar", "/salud", "/manifest.json", "/sw.js")


def es_local(request: Request):
    ip = request.client.host if request.client else ""
    return ip in ("127.0.0.1", "::1", "localhost")


@app.middleware("http")
async def puerta(request: Request, siguiente):
    """La ventana (127.0.0.1) entra sin nada. Desde la red, hace falta la llave."""
    ruta = request.url.path
    if (
        es_local(request)
        or ruta in LIBRES
        or ruta.startswith("/estatico/")
        or request.cookies.get("llave") == llave()
    ):
        return await siguiente(request)
    destino = request.url.path
    if request.url.query:
        destino += "?" + request.url.query
    return RedirectResponse(f"/entrar?volver={quote(destino, safe='')}", status_code=303)


@app.get("/salud")
def salud():
    return Response("vale", media_type="text/plain")


@app.get("/manifest.json")
def manifest():
    """Lo que hace que el móvil ofrezca añadirla a la pantalla de inicio."""
    return FileResponse(
        BASE / "estatico" / "manifest.json",
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
def service_worker():
    """Se sirve desde la raíz a propósito: un service worker sólo alcanza a su
    propia carpeta y hacia abajo, así que desde /estatico/ no cubriría la app."""
    return FileResponse(
        BASE / "estatico" / "sw.js",
        media_type="text/javascript",
        headers={
            "Cache-Control": "no-cache",
            "Service-Worker-Allowed": "/",
        },
    )


def vuelve(volver, por_defecto="/"):
    """Redirección 303 a una ruta interna. Nunca fuera de la app."""
    destino = volver or por_defecto
    if not destino.startswith("/") or destino.startswith("//"):
        destino = por_defecto
    return RedirectResponse(destino, status_code=303)


def como(texto):
    """Patrón LIKE con los comodines escapados."""
    limpio = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{limpio}%"


# --------------------------------------------------------------------------
# la llave de red (no es un login: no hay usuarios, es una llave)
# --------------------------------------------------------------------------

@app.get("/entrar")
def entrar(request: Request, volver: str = "/", mal: int = 0):
    return plantillas.TemplateResponse(
        request, "entrar.html", {"volver": volver, "mal": mal}
    )


@app.post("/entrar")
def entrar_guardar(clave: str = Form(""), volver: str = Form("/")):
    if clave.strip() != llave():
        return RedirectResponse(
            f"/entrar?volver={quote(volver, safe='')}&mal=1", status_code=303
        )
    respuesta = vuelve(volver)
    respuesta.set_cookie(
        "llave", llave(), max_age=365 * 24 * 3600, httponly=True, samesite="lax"
    )
    return respuesta


# --------------------------------------------------------------------------
# consultas reutilizadas
# --------------------------------------------------------------------------

NOMBRE_VISIBLE_SQL = "COALESCE(NULLIF(TRIM(p.apodo), ''), p.nombre)"


SELECT_PERSONA = f"""
SELECT p.*, {NOMBRE_VISIBLE_SQL} AS nombre_visible,
       c.nombre AS circulo, c.orden AS circulo_orden,
       (SELECT n.fecha FROM nota n
          JOIN nota_persona np ON np.nota_id = n.id
         WHERE np.persona_id = p.id
         ORDER BY n.fecha DESC, n.id DESC LIMIT 1) AS ultima_fecha,
       (SELECT n.canal FROM nota n
          JOIN nota_persona np ON np.nota_id = n.id
         WHERE np.persona_id = p.id
         ORDER BY n.fecha DESC, n.id DESC LIMIT 1) AS ultimo_canal
  FROM persona p
  LEFT JOIN circulo c ON c.id = p.circulo_id
"""


def circulos(con):
    """Los círculos, de dentro a fuera."""
    return con.execute("SELECT * FROM circulo ORDER BY orden, id").fetchall()


def canales(con):
    return [
        f["canal"] for f in con.execute(
            "SELECT DISTINCT canal FROM nota "
            "WHERE canal IS NOT NULL AND canal <> '' ORDER BY canal COLLATE NOCASE"
        )
    ]


def personas_de_notas(con, ids_nota):
    """{nota_id: [personas]}, para los chips de quién sale en cada nota."""
    if not ids_nota:
        return {}
    huecos = ",".join("?" * len(ids_nota))
    mapa = {}
    for f in con.execute(
        f"SELECT np.nota_id, p.id, {NOMBRE_VISIBLE_SQL} AS nombre "
        "FROM nota_persona np "
        "JOIN persona p ON p.id = np.persona_id "
        f"WHERE np.nota_id IN ({huecos}) ORDER BY nombre COLLATE NOCASE",
        ids_nota,
    ):
        mapa.setdefault(f["nota_id"], []).append(f)
    return mapa


# --------------------------------------------------------------------------
# 1. portada: el grafo
# --------------------------------------------------------------------------

@app.get("/")
def portada(request: Request):
    """El grafo, siempre. Aunque haya una sola persona: lo primero que se ve al
    abrir la app es la red, nunca una lista con filtros."""
    con = conexion()
    datos = {
        "cuantas_personas": con.execute(
            "SELECT COUNT(*) AS n FROM persona"
        ).fetchone()["n"],
        "cuantos_circulos": con.execute(
            "SELECT COUNT(*) AS n FROM circulo"
        ).fetchone()["n"],
        "circulos": circulos(con),
    }
    con.close()
    return plantillas.TemplateResponse(request, "grafo.html", datos)


@app.get("/ajustes")
def ajustes(request: Request):
    con = conexion()
    datos = {"circulos": circulos(con)}
    con.close()
    return plantillas.TemplateResponse(request, "ajustes.html", datos)


@app.post("/hilo/{hilo_id}/cerrar")
def cerrar_hilo(hilo_id: int, volver: str = Form("/")):
    con = conexion()
    with con:
        con.execute(
            "UPDATE hilo SET cerrado_el = ? WHERE id = ?", (hoy_iso(), hilo_id)
        )
    con.close()
    return vuelve(volver)


@app.post("/hilo/{hilo_id}/reabrir")
def reabrir_hilo(hilo_id: int, volver: str = Form("/")):
    con = conexion()
    with con:
        con.execute("UPDATE hilo SET cerrado_el = NULL WHERE id = ?", (hilo_id,))
    con.close()
    return vuelve(volver)


@app.post("/hilo/{hilo_id}/borrar")
def borrar_hilo(hilo_id: int, volver: str = Form("/")):
    con = conexion()
    with con:
        con.execute("DELETE FROM hilo WHERE id = ?", (hilo_id,))
    con.close()
    return vuelve(volver)


# --------------------------------------------------------------------------
# 2. personas
# --------------------------------------------------------------------------

ORDENES = {
    "alfabetico": " ORDER BY nombre_visible COLLATE NOCASE",
    "circulo": " ORDER BY c.orden IS NULL, c.orden, nombre_visible COLLATE NOCASE",
    "ultima": " ORDER BY ultima_fecha IS NULL, ultima_fecha DESC,"
              " nombre_visible COLLATE NOCASE",
}

PERSONAS_POR_PAGINA = 5


@app.get("/personas")
def lista_personas(
    request: Request, q: str = "", circulo: str = "", orden: str = "alfabetico",
    busca: str = "", vista: str = "todas", persona: str = "", pagina: int = 1,
):
    con = conexion()
    sql, args = SELECT_PERSONA, []
    condiciones = []
    if q.strip():
        condiciones.append("(p.nombre LIKE ? ESCAPE '\\' OR p.apodo LIKE ? ESCAPE '\\')")
        args += [como(q.strip()), como(q.strip())]
    if circulo == "ninguno":
        condiciones.append("p.circulo_id IS NULL")
    elif circulo.isdigit():
        condiciones.append("p.circulo_id = ?")
        args.append(int(circulo))
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += ORDENES.get(orden, ORDENES["alfabetico"])
    personas_encontradas = con.execute(sql, args).fetchall()
    total_encontradas = len(personas_encontradas)
    paginas_personas = max(
        1, -(-total_encontradas // PERSONAS_POR_PAGINA)
    )
    pagina_personas = min(max(pagina, 1), paginas_personas)
    inicio = (pagina_personas - 1) * PERSONAS_POR_PAGINA
    personas = personas_encontradas[inicio:inicio + PERSONAS_POR_PAGINA]

    notas_halladas, hechos_hallados, quienes = [], [], {}
    if busca.strip():
        patron = como(busca.strip())
        notas_halladas = con.execute(
            "SELECT n.* FROM nota n WHERE "
            "(n.texto LIKE ? ESCAPE '\\' OR n.resumen LIKE ? ESCAPE '\\') "
            "ORDER BY n.fecha DESC, n.id DESC LIMIT 50",
            (patron, patron),
        ).fetchall()
        quienes = personas_de_notas(con, [n["id"] for n in notas_halladas])
        hechos_hallados = con.execute(
            f"SELECT h.*, {NOMBRE_VISIBLE_SQL} AS persona FROM hecho h "
            "JOIN persona p ON p.id = h.persona_id "
            "WHERE h.texto LIKE ? ESCAPE '\\' "
            "ORDER BY persona COLLATE NOCASE LIMIT 50",
            (patron,),
        ).fetchall()

    abiertos = con.execute(
        f"SELECT h.*, {NOMBRE_VISIBLE_SQL} AS persona FROM hilo h "
        "JOIN persona p ON p.id = h.persona_id "
        "WHERE h.cerrado_el IS NULL "
        "ORDER BY h.abierto_desde, h.id"
    ).fetchall()
    callados = con.execute(
        SELECT_PERSONA
        + " ORDER BY ultima_fecha IS NULL, ultima_fecha ASC,"
          " nombre_visible COLLATE NOCASE"
          " LIMIT 10"
    ).fetchall()

    # El archivador usa los círculos existentes como carpetas: no crea otra
    # clasificación. La ficha rápida siempre pertenece al resultado visible.
    carpetas = [dict(f) for f in con.execute(
        "SELECT c.id, c.nombre, c.orden, COUNT(p.id) AS personas "
        "FROM circulo c LEFT JOIN persona p ON p.circulo_id = c.id "
        "GROUP BY c.id ORDER BY c.orden, c.id"
    )]
    if circulo == "ninguno":
        carpeta_actual = "Sin círculo"
    elif circulo.isdigit():
        carpeta_actual = next(
            (c["nombre"] for c in carpetas if c["id"] == int(circulo)),
            "Todas",
        )
    else:
        carpeta_actual = "Todas"
    total_personas = con.execute("SELECT COUNT(*) AS n FROM persona").fetchone()["n"]
    sin_circulo = con.execute(
        "SELECT COUNT(*) AS n FROM persona WHERE circulo_id IS NULL"
    ).fetchone()["n"]

    ids_visibles = {p["id"] for p in personas}
    persona_solicitada = int(persona) if persona.isdigit() else None
    if persona_solicitada not in ids_visibles:
        persona_solicitada = None
    elegida = next(
        (p for p in personas if p["id"] == persona_solicitada),
        personas[0] if personas else None,
    )
    persona_resumen = None
    if elegida is not None:
        persona_resumen = dict(elegida)
        persona_resumen["tiene_foto"] = bool(persona_resumen.pop("foto", None))
        conteos = con.execute(
            "SELECT "
            " COUNT(CASE WHEN tipo = 'pendiente' AND cerrado_el IS NULL THEN 1 END)"
            "   AS pendientes,"
            " COUNT(CASE WHEN tipo = 'preguntar' AND cerrado_el IS NULL THEN 1 END)"
            "   AS preguntar"
            " FROM hilo WHERE persona_id = ?",
            (elegida["id"],),
        ).fetchone()
        persona_resumen.update(dict(conteos))
        hilos_resumen = [
            h for h in abiertos if h["persona_id"] == elegida["id"]
        ]
        persona_resumen["pendiente_texto"] = next(
            (h["texto"] for h in hilos_resumen if h["tipo"] == "pendiente"),
            "",
        )
        persona_resumen["preguntar_texto"] = next(
            (h["texto"] for h in hilos_resumen if h["tipo"] != "pendiente"),
            "",
        )
        persona_resumen["relaciones"] = con.execute(
            "SELECT COUNT(*) AS n FROM relacion "
            "WHERE persona_a = ? OR persona_b = ?",
            (elegida["id"], elegida["id"]),
        ).fetchone()["n"]
        relaciones_resumen = con.execute(
            "SELECT r.*, "
            " (SELECT COALESCE(NULLIF(TRIM(apodo), ''), nombre) "
            "    FROM persona WHERE id = r.persona_a) AS nombre_a, "
            " (SELECT COALESCE(NULLIF(TRIM(apodo), ''), nombre) "
            "    FROM persona WHERE id = r.persona_b) AS nombre_b "
            "FROM relacion r WHERE r.persona_a = ? OR r.persona_b = ?",
            (elegida["id"], elegida["id"]),
        ).fetchall()
        persona_resumen["relaciones_resumen"] = sorted(
            [
                {
                    "nombre": (
                        r["nombre_b"]
                        if r["persona_a"] == elegida["id"]
                        else r["nombre_a"]
                    ),
                    "etiqueta": (
                        r["etiqueta"]
                        if r["persona_a"] == elegida["id"]
                        else (r["etiqueta_inversa"] or r["etiqueta"])
                    ),
                }
                for r in relaciones_resumen
            ],
            key=lambda r: r["nombre"].casefold(),
        )[:3]
        persona_resumen["datos_resumen"] = [
            dict(hecho) for hecho in con.execute(
                "SELECT texto FROM hecho WHERE persona_id = ? "
                "ORDER BY id DESC LIMIT 2",
                (elegida["id"],),
            ).fetchall()
        ]
        ultima = con.execute(
            "SELECT n.fecha, n.canal, n.texto, n.resumen FROM nota n "
            "JOIN nota_persona np ON np.nota_id = n.id "
            "WHERE np.persona_id = ? "
            "ORDER BY n.fecha DESC, n.id DESC LIMIT 1",
            (elegida["id"],),
        ).fetchone()
        persona_resumen["ultima_quedada"] = dict(ultima) if ultima else None

    parametros_archivo = {
        "q": q.strip(),
        "circulo": circulo,
        "orden": orden if orden in ORDENES else "alfabetico",
        "busca": busca.strip(),
    }

    def enlace_archivo(persona_id=None, pagina_destino=None):
        parametros = {
            clave: valor for clave, valor in parametros_archivo.items()
            if valor and not (clave == "orden" and valor == "alfabetico")
        }
        pagina_destino = pagina_personas if pagina_destino is None else pagina_destino
        if pagina_destino > 1:
            parametros["pagina"] = pagina_destino
        if persona_id is not None:
            parametros["persona"] = persona_id
        consulta = urlencode(parametros)
        return "/personas" + (f"?{consulta}" if consulta else "")

    enlace_sin_persona = enlace_archivo()
    datos = {
        "personas": personas,
        "circulos": circulos(con),
        "personas_alta": con.execute(
            "SELECT p.id, p.circulo_id, "
            f"{NOMBRE_VISIBLE_SQL} AS nombre_visible, c.nombre AS circulo "
            "FROM persona p LEFT JOIN circulo c ON c.id = p.circulo_id "
            "ORDER BY nombre_visible COLLATE NOCASE"
        ).fetchall(),
        "carpetas": carpetas,
        "total_personas": total_personas,
        "total_encontradas": total_encontradas,
        "sin_circulo": sin_circulo,
        "carpeta_actual": carpeta_actual,
        "pagina_personas": pagina_personas,
        "paginas_personas": paginas_personas,
        "enlace_anterior": (
            enlace_archivo(pagina_destino=pagina_personas - 1) + "#archivo"
            if pagina_personas > 1 else None
        ),
        "enlace_siguiente": (
            enlace_archivo(pagina_destino=pagina_personas + 1) + "#archivo"
            if pagina_personas < paginas_personas else None
        ),
        "persona_resumen": persona_resumen,
        "persona_solicitada": persona_solicitada,
        "enlaces_persona": {
            p["id"]: enlace_archivo(p["id"]) + "#archivo" for p in personas
        },
        "enlace_sin_persona": enlace_sin_persona,
        "volver_archivo": enlace_sin_persona + "#archivo",
        "enlace_carpeta_actual": (
            "/personas" + (f"?{urlencode({'circulo': circulo})}" if circulo else "")
        ),
        "pendientes": [h for h in abiertos if h["tipo"] == "pendiente"],
        "preguntar": [h for h in abiertos if h["tipo"] != "pendiente"],
        "callados": callados,
        "q": q, "circulo": circulo, "orden": orden, "busca": busca,
        "vista": vista if vista in ("todas", "pendiente", "preguntar", "callados")
                 else "todas",
        "notas_halladas": notas_halladas,
        "hechos_hallados": hechos_hallados,
        "quienes": quienes,
    }
    con.close()
    return plantillas.TemplateResponse(request, "personas.html", datos)


@app.post("/persona")
def crear_persona(
    nombre: str = Form(""), apodo: str = Form(""),
    circulo_id: str = Form(""),
    otras: list[str] = Form(default=[]),
    etiquetas: list[str] = Form(default=[]),
    inversas: list[str] = Form(default=[]),
    varias: list[str] = Form(default=[]),
    etiqueta_varias: str = Form(""),
    inversa_varias: str = Form(""),
    volver: str = Form("/personas"),
):
    nombre = nombre.strip()
    if not nombre:
        return vuelve(volver)
    con = conexion()
    circulo_elegido = int(circulo_id) if circulo_id.isdigit() else None
    if circulo_elegido is not None and not con.execute(
        "SELECT 1 FROM circulo WHERE id = ?", (circulo_elegido,)
    ).fetchone():
        circulo_elegido = None
    with con:
        cur = con.execute(
            "INSERT INTO persona (nombre, apodo, circulo_id, creada) "
            "VALUES (?, ?, ?, ?)",
            (nombre, apodo.strip(), circulo_elegido, ahora_iso()),
        )
        persona_id = cur.lastrowid
        enlazadas = set()
        for indice, otra in enumerate(otras):
            if not otra.isdigit():
                continue
            otra_id = int(otra)
            etiqueta = etiquetas[indice].strip() if indice < len(etiquetas) else ""
            inversa = inversas[indice].strip() if indice < len(inversas) else ""
            if (
                otra_id in enlazadas or not etiqueta
                or not con.execute(
                    "SELECT 1 FROM persona WHERE id = ?", (otra_id,)
                ).fetchone()
            ):
                continue
            con.execute(
                "INSERT INTO relacion "
                "(persona_a, persona_b, etiqueta, etiqueta_inversa) "
                "VALUES (?, ?, ?, ?)",
                (persona_id, otra_id, etiqueta, inversa),
            )
            enlazadas.add(otra_id)

        # Las marcadas de golpe: mismo par de etiquetas para todas. Van
        # después, así que una fila escrita a mano manda sobre la marca.
        etiqueta_grupo = etiqueta_varias.strip()
        inversa_grupo = inversa_varias.strip()
        if etiqueta_grupo:
            for marcada in varias:
                if not marcada.isdigit():
                    continue
                otra_id = int(marcada)
                if otra_id in enlazadas or not con.execute(
                    "SELECT 1 FROM persona WHERE id = ?", (otra_id,)
                ).fetchone():
                    continue
                con.execute(
                    "INSERT INTO relacion "
                    "(persona_a, persona_b, etiqueta, etiqueta_inversa) "
                    "VALUES (?, ?, ?, ?)",
                    (persona_id, otra_id, etiqueta_grupo, inversa_grupo),
                )
                enlazadas.add(otra_id)
    con.close()
    carpeta = str(circulo_elegido) if circulo_elegido is not None else "ninguno"
    volver_archivo = f"/personas?circulo={carpeta}#archivo"
    return RedirectResponse(
        f"/persona/{persona_id}?volver={quote(volver_archivo, safe='')}",
        status_code=303,
    )


@app.post("/circulo")
def crear_circulo(nombre: str = Form(""), volver: str = Form("/personas")):
    nombre = nombre.strip()
    if nombre:
        con = conexion()
        with con:
            fila = con.execute("SELECT MAX(orden) AS m FROM circulo").fetchone()
            con.execute(
                "INSERT INTO circulo (nombre, orden) VALUES (?, ?)",
                (nombre, (fila["m"] or 0) + 1),
            )
        con.close()
    return vuelve(volver, "/personas")


@app.post("/circulo/{circulo_id}")
def renombrar_circulo(
    circulo_id: int, nombre: str = Form(""), volver: str = Form("/personas"),
):
    nombre = nombre.strip()
    if nombre:
        con = conexion()
        with con:
            con.execute(
                "UPDATE circulo SET nombre = ? WHERE id = ?", (nombre, circulo_id)
            )
        con.close()
    return vuelve(volver, "/personas")


@app.post("/circulo/{circulo_id}/mover")
def mover_circulo(
    circulo_id: int, hacia: str = Form(""), volver: str = Form("/personas"),
):
    """Intercambia el orden con el vecino de arriba o de abajo."""
    con = conexion()
    with con:
        fila = con.execute(
            "SELECT id, orden FROM circulo WHERE id = ?", (circulo_id,)
        ).fetchone()
        if fila:
            if hacia == "arriba":
                vecino = con.execute(
                    "SELECT id, orden FROM circulo WHERE orden < ? OR"
                    " (orden = ? AND id < ?) ORDER BY orden DESC, id DESC LIMIT 1",
                    (fila["orden"], fila["orden"], fila["id"]),
                ).fetchone()
            else:
                vecino = con.execute(
                    "SELECT id, orden FROM circulo WHERE orden > ? OR"
                    " (orden = ? AND id > ?) ORDER BY orden, id LIMIT 1",
                    (fila["orden"], fila["orden"], fila["id"]),
                ).fetchone()
            if vecino:
                # si empataban en orden, hay que desempatarlos de verdad
                a, b = fila["orden"], vecino["orden"]
                if a == b:
                    a, b = (a, b + 1) if hacia != "arriba" else (a, b - 1)
                con.execute("UPDATE circulo SET orden = ? WHERE id = ?", (b, fila["id"]))
                con.execute(
                    "UPDATE circulo SET orden = ? WHERE id = ?", (a, vecino["id"])
                )
    con.close()
    return vuelve(volver, "/personas")


@app.post("/circulo/{circulo_id}/borrar")
def borrar_circulo(circulo_id: int, volver: str = Form("/personas")):
    """La gente que estaba dentro se queda sin circulo, pero no se borra
    (persona.circulo_id es ON DELETE SET NULL)."""
    con = conexion()
    with con:
        con.execute("DELETE FROM circulo WHERE id = ?", (circulo_id,))
    con.close()
    return vuelve(volver, "/personas")


# --------------------------------------------------------------------------
# 3. ficha
# --------------------------------------------------------------------------

QUEDADAS_POR_PAGINA = 10

# Lo que se dice en la ficha cuando una foto no ha llegado a guardarse.
FALLOS_FOTO = {
    "pesa": "Esa imagen pesa más de 8 MB. No se ha guardado.",
    "formato": "No he podido leer esa imagen. Prueba con otra.",
    "falta": "No se ha podido preparar la imagen en este ordenador.",
}


@app.get("/persona/{persona_id}")
def ficha(
    request: Request, persona_id: int, pagina: int = 1, volver: str = "",
    foto: str = "",
):
    con = conexion()
    persona = con.execute(
        SELECT_PERSONA + " WHERE p.id = ?", (persona_id,)
    ).fetchone()
    if persona is None:
        con.close()
        return RedirectResponse("/personas", status_code=303)

    abiertos = con.execute(
        "SELECT * FROM hilo WHERE persona_id = ? AND cerrado_el IS NULL "
        "ORDER BY abierto_desde, id",
        (persona_id,),
    ).fetchall()
    cerrados = con.execute(
        "SELECT * FROM hilo WHERE persona_id = ? AND cerrado_el IS NOT NULL "
        "ORDER BY cerrado_el DESC, id DESC",
        (persona_id,),
    ).fetchall()
    hechos = con.execute(
        "SELECT * FROM hecho WHERE persona_id = ? ORDER BY id", (persona_id,)
    ).fetchall()

    crudas = con.execute(
        "SELECT r.*, "
        "  (SELECT COALESCE(NULLIF(TRIM(apodo), ''), nombre) "
        "     FROM persona WHERE id = r.persona_a) AS nombre_a, "
        "  (SELECT COALESCE(NULLIF(TRIM(apodo), ''), nombre) "
        "     FROM persona WHERE id = r.persona_b) AS nombre_b "
        "FROM relacion r WHERE r.persona_a = ? OR r.persona_b = ?",
        (persona_id, persona_id),
    ).fetchall()
    relaciones = []
    for r in crudas:
        directa = r["persona_a"] == persona_id
        etiqueta_otra = (
            r["etiqueta"]
            if directa
            else (r["etiqueta_inversa"] or r["etiqueta"])
        )
        etiqueta_persona = (
            (r["etiqueta_inversa"] or r["etiqueta"])
            if directa
            else r["etiqueta"]
        )
        relaciones.append({
            "otra_id": r["persona_b"] if directa else r["persona_a"],
            "otra_nombre": r["nombre_b"] if directa else r["nombre_a"],
            "etiqueta": etiqueta_otra,
            "etiqueta_inversa": etiqueta_persona,
            "persona_a": r["persona_a"],
            "persona_b": r["persona_b"],
        })
    relaciones.sort(key=lambda r: (r["otra_nombre"] or "").lower())

    # Las quedadas van de diez en diez, de la más reciente a la más antigua.
    total_notas = con.execute(
        "SELECT COUNT(*) AS n FROM nota_persona WHERE persona_id = ?", (persona_id,)
    ).fetchone()["n"]
    paginas = max(1, -(-total_notas // QUEDADAS_POR_PAGINA))
    pagina = min(max(pagina, 1), paginas)
    notas = con.execute(
        "SELECT n.* FROM nota n JOIN nota_persona np ON np.nota_id = n.id "
        "WHERE np.persona_id = ? ORDER BY n.fecha DESC, n.id DESC "
        "LIMIT ? OFFSET ?",
        (persona_id, QUEDADAS_POR_PAGINA, (pagina - 1) * QUEDADAS_POR_PAGINA),
    ).fetchall()

    datos = {
        "p": persona,
        "fallo_foto": FALLOS_FOTO.get(foto, ""),
        "volver_personas": (
            volver
            if volver.startswith("/personas") and "\n" not in volver
            else "/personas#archivo"
        ),
        "circulos": circulos(con),
        "pendientes": [h for h in abiertos if h["tipo"] == "pendiente"],
        "preguntar": [h for h in abiertos if h["tipo"] != "pendiente"],
        "cerrados": cerrados,
        "hechos": hechos,
        "relaciones": relaciones,
        "notas": notas,
        "quienes": personas_de_notas(con, [n["id"] for n in notas]),
        "total_notas": total_notas,
        "pagina": pagina,
        "paginas": paginas,
        "otras": con.execute(
            "SELECT id, nombre, apodo, circulo_id, "
            "  COALESCE(NULLIF(TRIM(apodo), ''), nombre) AS nombre_visible, "
            "  (SELECT nombre FROM circulo WHERE id = persona.circulo_id) AS circulo "
            "FROM persona WHERE id <> ? ORDER BY nombre_visible COLLATE NOCASE",
            (persona_id,),
        ).fetchall(),
    }
    con.close()
    return plantillas.TemplateResponse(request, "ficha.html", datos)


MAX_FOTO_BYTES = 8 * 1024 * 1024
LADO_FOTO = 256


@app.get("/persona/{persona_id}/foto")
def foto_persona(persona_id: int):
    con = conexion()
    fila = con.execute(
        "SELECT foto FROM persona WHERE id = ?", (persona_id,)
    ).fetchone()
    con.close()
    if fila is None or not fila["foto"]:
        return Response(status_code=404)
    try:
        cabecera, contenido = fila["foto"].split(",", 1)
        if cabecera != "data:image/png;base64":
            raise ValueError
        return Response(b64decode(contenido), media_type="image/png")
    except (ValueError, TypeError):
        return Response(status_code=404)


@app.post("/persona/{persona_id}/foto")
async def cambiar_foto(
    persona_id: int,
    foto: UploadFile | None = File(None),
    quitar: str = Form(""),
):
    nueva = None
    cambiar = quitar == "si"
    fallo = ""
    if not cambiar and foto is not None and foto.filename:
        contenido = await foto.read(MAX_FOTO_BYTES + 1)
        if len(contenido) > MAX_FOTO_BYTES:
            fallo = "pesa"
        else:
            try:
                from PIL import Image, ImageOps

                with Image.open(BytesIO(contenido)) as original:
                    original.load()
                    # El móvil guarda la foto girada y anota la vuelta en EXIF.
                    # Sin esto, los retratos entran tumbados.
                    derecha = ImageOps.exif_transpose(original)
                    grises = ImageOps.fit(
                        derecha.convert("L"),
                        (LADO_FOTO, LADO_FOTO),
                        method=Image.Resampling.LANCZOS,
                    )
                    salida = BytesIO()
                    grises.save(salida, format="PNG", optimize=True)
                nueva = (
                    "data:image/png;base64,"
                    + b64encode(salida.getvalue()).decode("ascii")
                )
                cambiar = True
            except ImportError:
                fallo = "falta"
            except (OSError, ValueError):
                fallo = "formato"
    if cambiar:
        con = conexion()
        with con:
            con.execute(
                "UPDATE persona SET foto = ? WHERE id = ?", (nueva, persona_id)
            )
        con.close()
    destino = f"/persona/{persona_id}"
    if fallo:
        destino += f"?foto={fallo}"
    return RedirectResponse(destino, status_code=303)


@app.post("/persona/{persona_id}")
def editar_persona(
    persona_id: int,
    nombre: str = Form(""), apodo: str = Form(""), circulo_id: str = Form(""),
    color: str = Form(""), cumple: str = Form(""), notas_rapidas: str = Form(""),
):
    nombre = nombre.strip()
    if nombre:
        con = conexion()
        with con:
            con.execute(
                "UPDATE persona SET nombre = ?, apodo = ?, circulo_id = ?, "
                "color = ?, cumple = ?, notas_rapidas = ? WHERE id = ?",
                (nombre, apodo.strip(), int(circulo_id) if circulo_id.isdigit() else None,
                 color.strip(), cumple_iso(cumple), notas_rapidas.strip(), persona_id),
            )
        con.close()
    return RedirectResponse(f"/persona/{persona_id}", status_code=303)


@app.post("/persona/{persona_id}/borrar")
def borrar_persona(persona_id: int):
    con = conexion()
    with con:
        con.execute("DELETE FROM persona WHERE id = ?", (persona_id,))
    con.close()
    return RedirectResponse("/personas", status_code=303)


@app.post("/persona/{persona_id}/hecho")
def crear_hecho(persona_id: int, texto: str = Form("")):
    texto = texto.strip()
    if texto:
        con = conexion()
        with con:
            con.execute(
                "INSERT INTO hecho (persona_id, texto, creado) VALUES (?, ?, ?)",
                (persona_id, texto, ahora_iso()),
            )
        con.close()
    return RedirectResponse(f"/persona/{persona_id}", status_code=303)


@app.post("/hecho/{hecho_id}")
def editar_hecho(hecho_id: int, texto: str = Form("")):
    """El formulario de un hecho lleva un solo campo y ningún botón: Enter basta.
    Por eso no recibe 'volver' y la vuelta se deduce del propio hecho."""
    con = conexion()
    fila = con.execute(
        "SELECT persona_id FROM hecho WHERE id = ?", (hecho_id,)
    ).fetchone()
    with con:
        if texto.strip():
            con.execute(
                "UPDATE hecho SET texto = ? WHERE id = ?", (texto.strip(), hecho_id)
            )
        else:
            con.execute("DELETE FROM hecho WHERE id = ?", (hecho_id,))
    con.close()
    if fila is None:
        return RedirectResponse("/personas", status_code=303)
    return RedirectResponse(f"/persona/{fila['persona_id']}", status_code=303)


@app.post("/hecho/{hecho_id}/borrar")
def borrar_hecho(hecho_id: int):
    con = conexion()
    fila = con.execute(
        "SELECT persona_id FROM hecho WHERE id = ?", (hecho_id,)
    ).fetchone()
    with con:
        con.execute("DELETE FROM hecho WHERE id = ?", (hecho_id,))
    con.close()
    if fila is None:
        return RedirectResponse("/personas", status_code=303)
    return RedirectResponse(f"/persona/{fila['persona_id']}", status_code=303)


@app.post("/persona/{persona_id}/hilo")
def crear_hilo(persona_id: int, texto: str = Form(""), tipo: str = Form("preguntar")):
    """El formulario trae dos botones: uno pone 'pendiente' y el otro 'preguntar'."""
    texto = texto.strip()
    if texto:
        con = conexion()
        with con:
            con.execute(
                "INSERT INTO hilo (persona_id, texto, abierto_desde, tipo) "
                "VALUES (?, ?, ?, ?)",
                (persona_id, texto, hoy_iso(),
                 tipo if tipo in TIPOS else "preguntar"),
            )
        con.close()
    return RedirectResponse(f"/persona/{persona_id}", status_code=303)


def enlazar(con, persona_id, otra_id, etiqueta, inversa):
    """Crea o actualiza la relación entre dos personas. Una sola fila por pareja."""
    reves = con.execute(
        "SELECT 1 FROM relacion WHERE persona_a = ? AND persona_b = ?",
        (otra_id, persona_id),
    ).fetchone()
    if reves:
        # Ya existe la fila en el otro sentido: se actualiza cambiando papeles.
        con.execute(
            "UPDATE relacion SET etiqueta = ?, etiqueta_inversa = ? "
            "WHERE persona_a = ? AND persona_b = ?",
            (inversa or etiqueta, etiqueta, otra_id, persona_id),
        )
    else:
        con.execute(
            "INSERT OR REPLACE INTO relacion "
            "(persona_a, persona_b, etiqueta, etiqueta_inversa) "
            "VALUES (?, ?, ?, ?)",
            (persona_id, otra_id, etiqueta, inversa),
        )


@app.post("/persona/{persona_id}/relacion")
def crear_relacion(
    persona_id: int, otra: str = Form(""), etiqueta: str = Form(""),
    etiqueta_inversa: str = Form(""),
):
    etiqueta, inversa = etiqueta.strip(), etiqueta_inversa.strip()
    if otra.isdigit() and int(otra) != persona_id and etiqueta:
        con = conexion()
        with con:
            enlazar(con, persona_id, int(otra), etiqueta, inversa)
        con.close()
    return RedirectResponse(f"/persona/{persona_id}", status_code=303)


@app.post("/persona/{persona_id}/relaciones")
def crear_relaciones(
    persona_id: int, personas: list[str] = Form([]), etiqueta: str = Form(""),
    etiqueta_inversa: str = Form(""),
):
    """Varias de golpe con la misma etiqueta: compañeros de trabajo, primos…

    Enlaza a cada elegido con esta persona, no a todos entre sí: quien decide
    quién va con quién eres tú, y así no se generan relaciones inventadas.
    """
    etiqueta, inversa = etiqueta.strip(), etiqueta_inversa.strip()
    elegidas = {
        int(x) for x in personas if x.isdigit() and int(x) != persona_id
    }
    if elegidas and etiqueta:
        con = conexion()
        with con:
            for otra_id in sorted(elegidas):
                enlazar(con, persona_id, otra_id, etiqueta, inversa)
        con.close()
    return RedirectResponse(f"/persona/{persona_id}#relaciones", status_code=303)


@app.post("/relacion/editar")
def editar_relacion(
    persona_a: int = Form(...),
    persona_b: int = Form(...),
    persona_vista: int = Form(...),
    etiqueta: str = Form(""),
    etiqueta_inversa: str = Form(""),
):
    """Edita los dos sentidos usando como referencia la ficha que está abierta."""
    etiqueta = etiqueta.strip()
    inversa = etiqueta_inversa.strip()
    if persona_vista not in (persona_a, persona_b) or not etiqueta:
        return RedirectResponse(f"/persona/{persona_vista}", status_code=303)

    if persona_vista == persona_a:
        guardada, guardada_inversa = etiqueta, inversa or etiqueta
    else:
        guardada, guardada_inversa = inversa or etiqueta, etiqueta

    con = conexion()
    with con:
        con.execute(
            "UPDATE relacion SET etiqueta = ?, etiqueta_inversa = ? "
            "WHERE persona_a = ? AND persona_b = ?",
            (guardada, guardada_inversa, persona_a, persona_b),
        )
    con.close()
    return RedirectResponse(
        f"/persona/{persona_vista}#relaciones", status_code=303
    )


@app.post("/relacion/borrar")
def borrar_relacion(
    persona_a: int = Form(...), persona_b: int = Form(...), volver: str = Form("/"),
):
    con = conexion()
    with con:
        con.execute(
            "DELETE FROM relacion WHERE persona_a = ? AND persona_b = ?",
            (persona_a, persona_b),
        )
    con.close()
    return vuelve(volver)


# --------------------------------------------------------------------------
# 4. escribir nota
# --------------------------------------------------------------------------

AUDIOS_POR_PAGINA = 5


def audios_disponibles(con, solo_pendientes=False):
    """Devuelve sólo grabaciones que aún conservan su archivo en disco.

    Una fila antigua sin archivo no se borra a escondidas: simplemente deja de
    ofrecerse para escuchar o procesar. Así el archivo visible coincide con la
    carpeta real sin convertir una lectura de pantalla en una acción destructiva.
    """
    condicion = " WHERE estado <> 'revisado'" if solo_pendientes else ""
    filas = con.execute(
        "SELECT * FROM audio" + condicion + " ORDER BY grabado DESC, id DESC"
    ).fetchall()
    return [
        fila for fila in filas
        if (CARPETA_AUDIOS / Path(fila["archivo"]).name).is_file()
    ]


def archivo_audios(con, pagina, base):
    grabaciones = audios_disponibles(con)
    paginas = max(1, -(-len(grabaciones) // AUDIOS_POR_PAGINA))
    pagina = min(max(pagina, 1), paginas)
    inicio = (pagina - 1) * AUDIOS_POR_PAGINA

    def enlace(destino):
        return f"{base}?audios_pagina={destino}&archivo=1#audios"

    return {
        "audios": grabaciones[inicio:inicio + AUDIOS_POR_PAGINA],
        "audios_total": len(grabaciones),
        "audios_pagina": pagina,
        "audios_paginas": paginas,
        "audios_anterior": enlace(pagina - 1) if pagina > 1 else None,
        "audios_siguiente": enlace(pagina + 1) if pagina < paginas else None,
        "volver_audios": enlace(pagina),
    }


ESTADO_AUDIO_VISIBLE = {
    "pendiente": "Esperando transcripción",
    "transcribiendo": "Transcribiendo",
    "analisis_pendiente": "Esperando análisis",
    "analizando": "Preparando el borrador",
    "listo": "Listo para revisar",
    "revisado": "Revisado",
    "error_transcripcion": "No se pudo transcribir",
    "error_analisis": "No se pudo preparar el borrador",
}


def audio_para_pantalla(con, audio_id):
    audio = con.execute("SELECT * FROM audio WHERE id = ?", (audio_id,)).fetchone()
    if audio is None:
        return None
    resultado = dict(audio)
    try:
        borrador = json.loads(audio["borrador"]) if audio["borrador"] else {}
    except (TypeError, json.JSONDecodeError):
        borrador = {}
    personas_db = [dict(p) for p in con.execute(
        "SELECT p.id, p.nombre, p.apodo, "
        f"{NOMBRE_VISIBLE_SQL} AS nombre_visible, c.nombre AS circulo "
        "FROM persona p LEFT JOIN circulo c ON c.id = p.circulo_id "
        "ORDER BY nombre_visible COLLATE NOCASE, p.id"
    )]
    por_id = {p["id"]: p for p in personas_db}
    bloques = []
    for bloque in borrador.get("personas", []):
        if not isinstance(bloque, dict) or bloque.get("confirmado"):
            continue
        copia = dict(bloque)
        copia["persona"] = por_id.get(copia.get("persona_id"))
        copia["candidatos_detalle"] = [
            por_id[pid] for pid in copia.get("candidatos", []) if pid in por_id
        ]
        bloques.append(copia)
    resultado.update({
        "borrador_datos": borrador,
        "bloques": bloques,
        "personas": personas_db,
        "estado_visible": ESTADO_AUDIO_VISIBLE.get(audio["estado"], audio["estado"]),
        "trabajando": audio["estado"] in ESTADOS_TRABAJANDO,
    })
    return resultado


@app.get("/nota")
def pantalla_nota(
    request: Request, volver: str = "/", persona: str = "",
    audios_pagina: int = 1, archivo: str = "", audio: int = 0,
):
    con = conexion()
    datos = {
        "fecha": hoy_iso(),
        "personas": con.execute(
            SELECT_PERSONA + ORDENES["ultima"]
        ).fetchall(),
        "persona_inicial": int(persona) if persona.isdigit() else None,
        "audios_pendientes": audios_disponibles(con, solo_pendientes=True),
        "audio_inicial": audio,
        "archivo_abierto": archivo == "1" or audios_pagina > 1,
        "volver": volver,
    }
    datos.update(archivo_audios(con, audios_pagina, "/nota"))
    con.close()
    return plantillas.TemplateResponse(request, "notas.html", datos)


@app.get("/nota/audio/{audio_id}/proceso")
def proceso_audio(request: Request, audio_id: int):
    con = conexion()
    audio = audio_para_pantalla(con, audio_id)
    con.close()
    if audio is None:
        return Response(status_code=404)
    return plantillas.TemplateResponse(
        request, "_audio_proceso.html", {"audio_proceso": audio}
    )


@app.post("/nota/persona/{persona_id}")
def guardar_captura_persona(
    persona_id: int,
    pendientes: list[str] = Form(default=[]),
    preguntas: list[str] = Form(default=[]),
    datos: list[str] = Form(default=[]),
    quedada_fecha: str = Form(""),
    quedada_canal: str = Form(""),
    quedada_resumen: str = Form(""),
    quedada_texto: str = Form(""),
    audio_id: int = Form(0),
    volver: str = Form("/nota#captura"),
):
    """Guarda un bloque de la captura manual, aislado de los demás.

    Cada colección admite varias entradas. La quedada es una sola por bloque;
    si sólo se ha escrito una de sus dos versiones, se usa también como
    alternativa de la otra para no perder lo que la persona haya redactado.
    """
    pendientes = [texto.strip() for texto in pendientes if texto.strip()]
    preguntas = [texto.strip() for texto in preguntas if texto.strip()]
    datos = [texto.strip() for texto in datos if texto.strip()]
    resumen = quedada_resumen.strip()
    texto = quedada_texto.strip()
    canal = quedada_canal.strip()

    con = conexion()
    existe = con.execute(
        "SELECT 1 FROM persona WHERE id = ?", (persona_id,)
    ).fetchone()
    audio_existe = audio_id and con.execute(
        "SELECT 1 FROM audio WHERE id = ?", (audio_id,)
    ).fetchone()
    if existe is None:
        con.close()
        return vuelve(volver, "/nota#captura")

    with con:
        for contenido in pendientes:
            cur = con.execute(
                "INSERT INTO hilo (persona_id, texto, abierto_desde, tipo) "
                "VALUES (?, ?, ?, 'pendiente')",
                (persona_id, contenido, hoy_iso()),
            )
            if audio_existe:
                con.execute(
                    "INSERT OR IGNORE INTO audio_registro VALUES (?, 'hilo', ?, ?)",
                    (audio_id, cur.lastrowid, persona_id),
                )
        for contenido in preguntas:
            cur = con.execute(
                "INSERT INTO hilo (persona_id, texto, abierto_desde, tipo) "
                "VALUES (?, ?, ?, 'preguntar')",
                (persona_id, contenido, hoy_iso()),
            )
            if audio_existe:
                con.execute(
                    "INSERT OR IGNORE INTO audio_registro VALUES (?, 'hilo', ?, ?)",
                    (audio_id, cur.lastrowid, persona_id),
                )
        for contenido in datos:
            cur = con.execute(
                "INSERT INTO hecho (persona_id, texto, creado) VALUES (?, ?, ?)",
                (persona_id, contenido, ahora_iso()),
            )
            if audio_existe:
                con.execute(
                    "INSERT OR IGNORE INTO audio_registro VALUES (?, 'hecho', ?, ?)",
                    (audio_id, cur.lastrowid, persona_id),
                )
        if resumen or texto:
            try:
                fecha = date.fromisoformat(quedada_fecha.strip()).isoformat()
            except ValueError:
                fecha = hoy_iso()
            cur = con.execute(
                "INSERT INTO nota (fecha, canal, texto, resumen, creada) "
                "VALUES (?, ?, ?, ?, ?)",
                (fecha, canal, texto or resumen, resumen or texto, ahora_iso()),
            )
            con.execute(
                "INSERT INTO nota_persona (nota_id, persona_id) VALUES (?, ?)",
                (cur.lastrowid, persona_id),
            )
            if audio_existe:
                con.execute(
                    "INSERT OR IGNORE INTO audio_registro VALUES (?, 'nota', ?, ?)",
                    (audio_id, cur.lastrowid, persona_id),
                )
    con.close()
    return vuelve(volver, "/nota#captura")


@app.get("/nota/{nota_id}")
def pantalla_editar_nota(request: Request, nota_id: int, volver: str = "/"):
    con = conexion()
    nota = con.execute("SELECT * FROM nota WHERE id = ?", (nota_id,)).fetchone()
    if nota is None:
        con.close()
        return vuelve(volver)
    marcadas = [
        fila["persona_id"] for fila in con.execute(
            "SELECT persona_id FROM nota_persona WHERE nota_id = ?", (nota_id,)
        )
    ]
    datos = {
        "fecha": nota["fecha"],
        "texto": nota["texto"],
        "resumen": nota["resumen"] or "",
        "canal": nota["canal"] or "",
        "editando": True,
        "nota": nota,
        "canales": canales(con),
        "personas": con.execute(
            SELECT_PERSONA + ORDENES["ultima"]
        ).fetchall(),
        "marcadas": marcadas,
        "volver": volver,
    }
    con.close()
    return plantillas.TemplateResponse(request, "nota.html", datos)


@app.post("/nota")
def guardar_nota(
    texto: str = Form(""), fecha: str = Form(""), canal: str = Form(""),
    resumen: str = Form(""),
    personas: list[int] = Form(default=[]), personas_nuevas: str = Form(""),
    volver: str = Form("/"),
):
    texto = texto.strip()
    if not texto:
        return vuelve(volver)
    try:
        fecha = date.fromisoformat(fecha.strip()).isoformat()
    except ValueError:
        fecha = hoy_iso()

    con = conexion()
    with con:
        cur = con.execute(
            "INSERT INTO nota (fecha, canal, texto, resumen, creada) "
            "VALUES (?, ?, ?, ?, ?)",
            (fecha, canal.strip(), texto, resumen.strip(), ahora_iso()),
        )
        nota_id = cur.lastrowid

        ids = set(personas)
        for nombre in (n.strip() for n in personas_nuevas.split(",")):
            if nombre:
                nueva = con.execute(
                    "INSERT INTO persona (nombre, creada) VALUES (?, ?)",
                    (nombre, ahora_iso()),
                )
                ids.add(nueva.lastrowid)
        for pid in ids:
            con.execute(
                "INSERT OR IGNORE INTO nota_persona (nota_id, persona_id) VALUES (?, ?)",
                (nota_id, pid),
            )
    con.close()
    return vuelve(volver)


@app.post("/nota/{nota_id}")
def editar_nota(
    nota_id: int,
    texto: str = Form(""),
    resumen: str = Form(""),
    fecha: str = Form(""),
    canal: str = Form(""),
    personas: list[int] = Form(default=[]),
    personas_nuevas: str = Form(""),
    volver: str = Form("/"),
):
    texto = texto.strip()
    if not texto:
        return vuelve(volver)
    try:
        fecha = date.fromisoformat(fecha.strip()).isoformat()
    except ValueError:
        fecha = hoy_iso()

    con = conexion()
    existe = con.execute(
        "SELECT 1 FROM nota WHERE id = ?", (nota_id,)
    ).fetchone()
    if existe is None:
        con.close()
        return vuelve(volver)

    with con:
        con.execute(
            "UPDATE nota SET fecha = ?, canal = ?, texto = ?, resumen = ? "
            "WHERE id = ?",
            (fecha, canal.strip(), texto, resumen.strip(), nota_id),
        )
        con.execute("DELETE FROM nota_persona WHERE nota_id = ?", (nota_id,))

        ids = set(personas)
        for nombre in (n.strip() for n in personas_nuevas.split(",")):
            if nombre:
                nueva = con.execute(
                    "INSERT INTO persona (nombre, creada) VALUES (?, ?)",
                    (nombre, ahora_iso()),
                )
                ids.add(nueva.lastrowid)
        for pid in ids:
            con.execute(
                "INSERT OR IGNORE INTO nota_persona (nota_id, persona_id) "
                "VALUES (?, ?)",
                (nota_id, pid),
            )
    con.close()
    return vuelve(volver)


@app.post("/nota/{nota_id}/borrar")
def borrar_nota(nota_id: int, volver: str = Form("/")):
    """Una quedada puede mencionar a varias personas, así que al borrarla
    desaparece de todas sus fichas, no sólo de la que estabas mirando. Las
    filas de `nota_persona` se van solas por ON DELETE CASCADE."""
    con = conexion()
    with con:
        con.execute("DELETE FROM nota WHERE id = ?", (nota_id,))
    con.close()
    return vuelve(volver)


# --------------------------------------------------------------------------
# captura por voz: transcripción local y borrador estructurado local
# --------------------------------------------------------------------------

ESTADOS_TRABAJANDO = ("pendiente", "transcribiendo", "analisis_pendiente", "analizando")
_aviso_modelos = threading.Event()
_hilo_modelos = None
_whisper = None


def contexto_para_qwen(con):
    """La libreta existente es el contexto: nombres, apodos, círculos y red.

    No se mandan fotos, notas ni otros datos privados que no ayudan a resolver
    quién es quién. Todo permanece en la máquina (Ollama escucha en localhost).
    """
    personas = [dict(f) for f in con.execute(
        "SELECT p.id, p.nombre, p.apodo, c.nombre AS circulo, "
        "CASE WHEN LOWER(TRIM(COALESCE(c.nombre, ''))) = 'yo' THEN 1 ELSE 0 END AS es_yo "
        "FROM persona p LEFT JOIN circulo c ON c.id = p.circulo_id ORDER BY p.id"
    )]
    relaciones = []
    for f in con.execute(
        "SELECT persona_a, persona_b, etiqueta, etiqueta_inversa FROM relacion"
    ):
        relaciones.append({
            "desde": f["persona_a"], "hacia": f["persona_b"],
            "papel": f["etiqueta"],
        })
        relaciones.append({
            "desde": f["persona_b"], "hacia": f["persona_a"],
            "papel": f["etiqueta_inversa"] or f["etiqueta"],
        })
    return {"personas": personas, "relaciones": relaciones}


def contrato_qwen():
    texto = {"type": "string"}
    quedada = {
        "anyOf": [
            {"type": "null"},
            {
                "type": "object",
                "properties": {
                    "fecha": texto, "canal": texto, "resumen": texto, "texto": texto,
                },
                "required": ["fecha", "canal", "resumen", "texto"],
                "additionalProperties": False,
            },
        ]
    }
    return {
        "type": "object",
        "properties": {
            "version": {"type": "integer"},
            "personas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clave": texto,
                        "mencion": texto,
                        "persona_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                        "persona_dudosa": {"type": "boolean"},
                        "candidatos": {"type": "array", "items": {"type": "integer"}},
                        "pendientes": {"type": "array", "items": texto},
                        "preguntas": {"type": "array", "items": texto},
                        "quedada": quedada,
                        "datos": {"type": "array", "items": texto},
                    },
                    "required": [
                        "clave", "mencion", "persona_id", "persona_dudosa",
                        "candidatos", "pendientes", "preguntas", "quedada", "datos",
                    ],
                    "additionalProperties": False,
                },
            },
            "sin_asignar": {"type": "array", "items": texto},
            "avisos": {"type": "array", "items": texto},
        },
        "required": ["version", "personas", "sin_asignar", "avisos"],
        "additionalProperties": False,
    }


def _texto_modelo(valor):
    import unicodedata
    return unicodedata.normalize("NFC", str(valor or "")) \
        .replace("ń", "ñ").replace("Ń", "Ñ").strip()


def _lista_textos(valor):
    if not isinstance(valor, list):
        return []
    salida = []
    for texto in valor:
        limpio = _texto_modelo(texto)
        if limpio and limpio not in salida:
            salida.append(limpio)
    return salida


def _madre_de_yo(contexto):
    ids_yo = {p["id"] for p in contexto["personas"] if p["es_yo"]}
    candidatas = {
        r["hacia"] for r in contexto["relaciones"]
        if r["desde"] in ids_yo and "madre" in (r["papel"] or "").lower()
    }
    return next(iter(candidatas)) if len(candidatas) == 1 else None


def _nombre_clave(texto):
    import unicodedata
    limpio = unicodedata.normalize("NFD", str(texto or "").lower())
    limpio = "".join(c for c in limpio if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", limpio).split())


def _fecha_dicha(fecha):
    texto = f"{fecha.day} de {MESES[fecha.month - 1]}"
    return texto if fecha.year == date.today().year else f"{texto} de {fecha.year}"


def corregir_dia_del_calendario(texto, grabado):
    """Un «viernes 5» imposible se ajusta al viernes cercano real."""
    try:
        base = date.fromisoformat(str(grabado)[:10])
    except ValueError:
        return texto
    dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    meses = {nombre: indice + 1 for indice, nombre in enumerate(MESES)}
    patron = re.compile(
        rf"\b({'|'.join(dias)})\s+(\d{{1,2}})\s+de\s+({'|'.join(MESES)})\b",
        re.IGNORECASE,
    )

    def corregir(coincidencia):
        nombre_dia = coincidencia.group(1).lower()
        numero = int(coincidencia.group(2))
        nombre_mes = coincidencia.group(3).lower()
        try:
            dicha = date(base.year, meses[nombre_mes], numero)
        except ValueError:
            return coincidencia.group(0)
        esperado = dias.index(nombre_dia)
        if dicha.weekday() == esperado:
            return coincidencia.group(0)
        opciones = [
            date.fromordinal(base.toordinal() + salto)
            for salto in range(-7, 29)
        ]
        opciones = [d for d in opciones if d.month == dicha.month and d.weekday() == esperado]
        if not opciones:
            return coincidencia.group(0)
        correcta = min(opciones, key=lambda d: abs(d.day - numero))
        return f"{coincidencia.group(1)} {correcta.day} de {nombre_mes}"

    return patron.sub(corregir, texto)


def resolver_fechas_relativas(texto, grabado):
    """Resuelve referencias inequívocas; las ambiguas siguen visibles."""
    try:
        base = date.fromisoformat(str(grabado)[:10])
    except ValueError:
        return texto
    resultado = texto
    dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    for indice, nombre in enumerate(dias):
        salto = (indice - base.weekday()) % 7
        destino = date.fromordinal(base.toordinal() + salto)
        resultado = re.sub(
            rf"\beste\s+{nombre}\b", f"el {nombre} {_fecha_dicha(destino)}",
            resultado, flags=re.IGNORECASE,
        )
    manana = date.fromordinal(base.toordinal() + 1)
    resultado = re.sub(
        r"(?<!la )\bmañana\b", f"el {_fecha_dicha(manana)}", resultado,
        flags=re.IGNORECASE,
    )
    dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    ayer = date.fromordinal(base.toordinal() - 1)
    resultado = re.sub(
        r"\bayer\b", f"el {dias[ayer.weekday()]} {_fecha_dicha(ayer)}",
        resultado, flags=re.IGNORECASE,
    )
    resultado = re.sub(
        r"\bhoy\b", f"el {dias[base.weekday()]} {_fecha_dicha(base)}",
        resultado, flags=re.IGNORECASE,
    )
    def completar_dia(coincidencia):
        numero = int(coincidencia.group(1))
        opciones = [
            date.fromordinal(base.toordinal() + salto)
            for salto in range(0, 32)
            if date.fromordinal(base.toordinal() + salto).day == numero
        ]
        if not opciones:
            return coincidencia.group(0)
        destino = opciones[0]
        return f"el {dias[destino.weekday()]} {_fecha_dicha(destino)}"

    resultado = re.sub(
        r"\bel\s+(\d{1,2})\b(?!\s+de)", completar_dia, resultado,
        flags=re.IGNORECASE,
    )
    return corregir_dia_del_calendario(resultado, grabado)


def quitar_nombre_repetido(texto, persona):
    resultado = texto.strip()
    nombres = sorted(
        {n.strip() for n in (persona.get("nombre"), persona.get("apodo")) if n and n.strip()},
        key=len, reverse=True,
    )
    for nombre in nombres:
        nuevo = re.sub(
            rf"^{re.escape(nombre)}\s*[,;:]?\s+", "", resultado,
            count=1, flags=re.IGNORECASE,
        )
        if nuevo != resultado:
            resultado = nuevo[:1].upper() + nuevo[1:]
            break
    return resultado


def dato_es_temporal(texto):
    """Último cortafuegos: un plan o compra puntual nunca es un Dato estable."""
    compra = re.search(r"\bcompr\w*\b", texto, flags=re.IGNORECASE)
    compra_importante = re.search(
        r"\b(coche|casa|piso|vivienda)\b", texto, flags=re.IGNORECASE
    )
    if compra:
        return not compra_importante
    patron = (
        r"\b(viajará|viaja(?:rá)?\s+a|se\s+va\s+a|se\s+irá|saldrá|llegará|"
        r"regresará|volverá|dejará|ha\s+vuelto|volvió|regresó|"
        r"está\s+de\s+vacaciones|"
        r"se\s+mudará|tiene\s+una\s+cita|tiene\s+un\s+examen)\b"
    )
    return bool(re.search(patron, texto, flags=re.IGNORECASE))


def pregunta_es_trivial(texto):
    if re.search(r"^¿?si\s+necesita\s+ayuda\b", texto, re.IGNORECASE):
        return True
    compra = re.search(r"\b(compr\w*|tienda|vestido\w*|ropa)\b", texto, re.IGNORECASE)
    importante = re.search(r"\b(casa|piso|vivienda|coche|trabajo)\b", texto, re.IGNORECASE)
    return bool(compra and not importante)


def naturalizar_pregunta(pregunta):
    """Completa «Preguntar por» con un asunto natural, no con otra pregunta."""
    pregunta = pregunta.strip().lstrip("¿").rstrip("?").strip()
    pregunta = re.sub(
        r"\s+(?:del|el)(?:\s+(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo))?"
        r"\s+\d{1,2}.*$", "", pregunta,
        flags=re.IGNORECASE,
    ).rstrip(" ,.;:")
    coincidencia = re.match(
        r"^cómo\s+le\s+va\s+con\s+((?:el|la|los|las)\s+.+?)(?:\s+que\s+.+)?$",
        pregunta, flags=re.IGNORECASE,
    )
    if coincidencia:
        pregunta = coincidencia.group(1)
    else:
        coincidencia = re.match(
            r"^cómo\s+le\s+(?:va|fue|ha\s+ido)\s+(?:en|con)\s+(su\s+.+)$",
            pregunta, flags=re.IGNORECASE,
        )
        if coincidencia:
            pregunta = coincidencia.group(1)
    coincidencia = re.match(
        r"^qué\s+tal\s+(?:le\s+)?(?:fue|ha\s+ido|va)\s+"
        r"((?:el|la|los|las)\s+.+)$",
        pregunta, flags=re.IGNORECASE,
    )
    if coincidencia:
        pregunta = coincidencia.group(1)
    coincidencia = re.match(
        r"^qué\s+planes\s+(?:tiene|tienes)\s+durante\s+(?:sus|tus|las)\s+(.+)$",
        pregunta, flags=re.IGNORECASE,
    )
    if coincidencia:
        pregunta = f"Las {coincidencia.group(1)}"
    coincidencia = re.match(
        r"^cómo\s+le\s+va\s+en\s+((?:el|la|los|las)\s+.+)$",
        pregunta, flags=re.IGNORECASE,
    )
    if coincidencia:
        pregunta = coincidencia.group(1)
    coincidencia = re.match(
        r"^qué\s+hizo\s+en\s+((?:el|la|los|las)\s+.+)$",
        pregunta, flags=re.IGNORECASE,
    )
    if coincidencia:
        pregunta = coincidencia.group(1)
    pregunta = re.sub(
        r"^cuándo\s+vuelve\s+a\s+trabajar$", "Las vacaciones",
        pregunta, count=1, flags=re.IGNORECASE,
    )
    pregunta = re.sub(
        r"^qué\s+planes\s+(?:tiene|tienes)\s+en\s+(?:sus\s+|las\s+)?vacaciones$",
        "Las vacaciones", pregunta, count=1, flags=re.IGNORECASE,
    )
    pregunta = re.sub(
        r"^qué\s+tal\s+(?:el\s+)?viaje\b", "El viaje",
        pregunta, count=1, flags=re.IGNORECASE,
    )
    pregunta = re.sub(
        r"^cuándo\s+(?:terminan|acaban)\s+sus\s+", "Las ",
        pregunta, count=1, flags=re.IGNORECASE,
    )
    pregunta = pregunta[:1].upper() + pregunta[1:] if pregunta else pregunta
    return pregunta


def naturalizar_relato(texto):
    """Mantiene concordancia de pasado en el discurso indirecto."""
    texto = re.sub(
        r"\b((?:me\s+)?(?:comentó|contó|dijo)|también\s+mencionó)\s+que\s+se\s+ha\s+comprado\b",
        lambda m: f"{m.group(1)} que se había comprado",
        texto, flags=re.IGNORECASE,
    )
    texto = re.sub(r"^se\s+habló\s+de\b", "Hablamos de", texto, flags=re.IGNORECASE)
    texto = re.sub(
        r"\bdurante\s+la\s+conversación,?\s+se\s+mencionó\s+que\b",
        "También hablamos de que", texto, flags=re.IGNORECASE,
    )
    texto = re.sub(
        r"\bfinalmente,?\s+se\s+tomó\s+algo\b",
        "Al final estuvimos tomando algo", texto, flags=re.IGNORECASE,
    )
    return texto


def naturalizar_resumen(texto):
    """La ficha compacta recuerda la conversación sin convertirse en agenda."""
    dias = "lunes|martes|miércoles|jueves|viernes|sábado|domingo"
    meses = "|".join(MESES)
    texto = re.sub(
        rf"\s+(?:del|el)(?:\s+(?:{dias}))?\s+\d{{1,2}}\s+de\s+(?:{meses})",
        "", texto, flags=re.IGNORECASE,
    )
    texto = re.sub(
        r"^conversación\s+sobre\s+el\b", "Hablamos del", texto,
        count=1, flags=re.IGNORECASE,
    )
    texto = re.sub(
        r"^conversación\s+sobre\b", "Hablamos de", texto,
        count=1, flags=re.IGNORECASE,
    )
    texto = re.sub(
        r"\by\s+actualizaciones\s+personales\b",
        "y de algunas novedades personales", texto, flags=re.IGNORECASE,
    )
    return texto


def normalizar_canal(canal):
    """Un lugar concreto pertenece al relato; el canal es cómo coincidieron."""
    if re.search(
        r"\b(piscina|plaza|casa|bar|restaurante|calle|parque|oficina)\b",
        canal, flags=re.IGNORECASE,
    ):
        return "En persona"
    return canal


def participantes_explicitos(transcripcion, contexto):
    """Extrae una enumeración inequívoca del tipo «quedamos A, B y yo»."""
    coincidencia = re.search(
        r"\bquedamos\s+(.+?)(?=\s+en\s+|\s+y\s+(?:estuv|habl|tom)|[.;])",
        transcripcion or "", flags=re.IGNORECASE,
    )
    if not coincidencia:
        return None
    tramo = _nombre_clave(coincidencia.group(1))
    encontrados = set()
    for persona in contexto["personas"]:
        if persona.get("es_yo"):
            continue
        for nombre in (persona.get("nombre"), persona.get("apodo")):
            clave = _nombre_clave(nombre)
            if clave and re.search(rf"\b{re.escape(clave)}\b", tramo):
                encontrados.add(persona["id"])
                break
    return encontrados or None


def persona_mencionada_univoca(mencion, contexto):
    """Un nombre o apodo exacto pesa más que cualquier id imaginado por Qwen."""
    partes = {
        _nombre_clave(parte) for parte in re.split(r"[/,]", mencion or "")
        if _nombre_clave(parte)
    }
    ids = set()
    for persona in contexto["personas"]:
        for nombre in (persona.get("nombre"), persona.get("apodo")):
            if _nombre_clave(nombre) in partes:
                ids.add(persona["id"])
    return next(iter(ids)) if len(ids) == 1 else None


def completar_fecha_suelta(resumen, texto_completo, grabado):
    try:
        base = date.fromisoformat(str(grabado)[:10])
    except ValueError:
        return resumen
    meses = "|".join(MESES)
    dias_semana = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    for dia, mes in re.findall(
        rf"\b(\d{{1,2}})\s+de\s+({meses})\b", texto_completo,
        flags=re.IGNORECASE,
    ):
        fecha = date(base.year, MESES.index(mes.lower()) + 1, int(dia))
        dicho = f"el {dias_semana[fecha.weekday()]} {fecha.day} de {mes.lower()}"
        resumen = re.sub(
            rf"\bel\s+{int(dia)}\b(?!\s+de)", dicho, resumen,
            flags=re.IGNORECASE,
        )
    return resumen


def pulir_contenido_personas(personas, por_id, grabado):
    for bloque in personas:
        persona = por_id.get(bloque.get("persona_id"))
        if bloque.get("quedada"):
            for campo in ("resumen", "texto"):
                texto = bloque["quedada"].get(campo, "")
                if campo == "texto":
                    texto = resolver_fechas_relativas(texto, grabado)
                if persona:
                    texto = quitar_nombre_repetido(texto, persona)
                if campo == "texto":
                    texto = naturalizar_relato(texto)
                else:
                    texto = naturalizar_resumen(texto)
                texto = texto[:1].upper() + texto[1:] if texto else texto
                if campo == "texto" and texto and texto[-1] not in ".!?":
                    texto += "."
                bloque["quedada"][campo] = texto
            bloque["quedada"]["resumen"] = completar_fecha_suelta(
                bloque["quedada"]["resumen"], bloque["quedada"]["texto"], grabado
            )
        for campo in ("pendientes", "preguntas", "datos"):
            limpios = []
            for texto in bloque.get(campo, []):
                texto = resolver_fechas_relativas(texto, grabado)
                if persona:
                    texto = quitar_nombre_repetido(texto, persona)
                if campo == "datos" and dato_es_temporal(texto):
                    continue
                if campo == "preguntas":
                    if pregunta_es_trivial(texto):
                        continue
                    texto = naturalizar_pregunta(texto)
                if texto and texto not in limpios:
                    limpios.append(texto)
            bloque[campo] = limpios


def ajustar_identidades_por_grupo(personas, contexto):
    """Corrige homónimos por conexiones; los empates quedan para revisión."""
    nombres = {}
    for persona in contexto["personas"]:
        for nombre in (persona.get("nombre"), persona.get("apodo")):
            clave = _nombre_clave(nombre)
            if clave:
                nombres.setdefault(clave, set()).add(persona["id"])
    conexiones = set()
    for relacion in contexto["relaciones"]:
        conexiones.add(frozenset((relacion["desde"], relacion["hacia"])))

    for bloque in personas:
        trozos = [_nombre_clave(t) for t in re.split(r"[/,]", bloque.get("mencion", ""))]
        por_nombre = set()
        for trozo in trozos:
            por_nombre.update(nombres.get(trozo, set()))
        candidatos = set(bloque.get("candidatos", [])) | por_nombre
        if len(candidatos) <= 1:
            continue
        otros = {
            otro.get("persona_id") for otro in personas
            if otro is not bloque and otro.get("persona_id")
        }
        puntuaciones = {
            candidato: sum(
                frozenset((candidato, otro)) in conexiones for otro in otros
            )
            for candidato in candidatos
        }
        orden = sorted(puntuaciones, key=lambda pid: puntuaciones[pid], reverse=True)
        mejor = orden[0]
        segundo = puntuaciones[orden[1]]
        if puntuaciones[mejor] > segundo and puntuaciones[mejor] > 0:
            bloque["persona_id"] = mejor
            bloque["persona_dudosa"] = False
        else:
            # Qwen puede proponer una candidata, pero sin una ventaja contextual
            # visible no se guarda hasta que la persona usuaria lo confirme.
            bloque["persona_dudosa"] = True
        bloque["candidatos"] = sorted(
            candidatos, key=lambda pid: (-puntuaciones[pid], pid)
        )


def normalizar_borrador(bruto, contexto, grabado, anterior=None, transcripcion=""):
    """Acepta sólo ids reales y conserva lo que ya se confirmó en una ficha."""
    anterior = anterior if isinstance(anterior, dict) else {}
    por_id = {p["id"]: p for p in contexto["personas"]}
    confirmadas = [
        p for p in anterior.get("personas", [])
        if isinstance(p, dict) and p.get("confirmado")
    ]
    ids_confirmados = {p.get("persona_id") for p in confirmadas}
    madre = _madre_de_yo(contexto)
    participantes = participantes_explicitos(transcripcion, contexto)
    personas = []
    claves = set()
    for indice, entrada in enumerate((bruto or {}).get("personas", [])):
        if not isinstance(entrada, dict):
            continue
        mencion = _texto_modelo(entrada.get("mencion"))
        persona_id = entrada.get("persona_id")
        candidatos = [
            pid for pid in entrada.get("candidatos", [])
            if isinstance(pid, int) and pid in por_id
        ]
        # Esta relación explícita es más fuerte que una diferencia ortográfica:
        # "mi madre", Carmela y Karmela no pueden convertirse en dos personas.
        if madre and "mi madre" in mencion.lower():
            persona_id, candidatos = madre, [madre]
            dudosa = False
        else:
            mencion_univoca = persona_mencionada_univoca(mencion, contexto)
            if mencion_univoca is not None:
                persona_id, candidatos, dudosa = mencion_univoca, [mencion_univoca], False
            else:
                persona_id = persona_id if persona_id in por_id else None
                dudosa = bool(entrada.get("persona_dudosa")) or persona_id is None
        candidatos = [pid for pid in candidatos if not por_id[pid].get("es_yo")]
        # La libreta registra a las otras personas. Quien habla aporta el punto
        # de vista, pero nunca recibe un bloque propio ni una ficha de diario.
        if persona_id is not None and por_id[persona_id].get("es_yo"):
            continue
        if persona_id in ids_confirmados:
            continue
        if persona_id is not None and persona_id not in candidatos:
            candidatos.insert(0, persona_id)
        clave = re.sub(r"[^a-zA-Z0-9_-]", "-", str(entrada.get("clave") or ""))
        clave = clave.strip("-") or f"persona-{indice + 1}"
        while clave in claves:
            clave += "-otra"
        claves.add(clave)
        quedada_bruta = entrada.get("quedada")
        quedada = None
        if isinstance(quedada_bruta, dict):
            # Una nota grabada después puede comenzar «ayer quedamos». Sólo se
            # acepta una fecha propuesta pasada y cercana; una fecha futura
            # mencionada dentro sigue siendo contenido, no el día del encuentro.
            fecha = str(grabado)[:10]
            try:
                base = date.fromisoformat(fecha)
                propuesta = date.fromisoformat(_texto_modelo(quedada_bruta.get("fecha")))
                if propuesta <= base and (base - propuesta).days <= 31:
                    fecha = propuesta.isoformat()
            except ValueError:
                pass
            resumen = _texto_modelo(quedada_bruta.get("resumen"))
            if len(resumen) > 160:
                resumen = resumen[:157].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
            quedada = {
                "fecha": fecha,
                "canal": normalizar_canal(_texto_modelo(quedada_bruta.get("canal"))),
                "resumen": resumen,
                "texto": _texto_modelo(quedada_bruta.get("texto")),
            }
            if participantes is not None and persona_id not in participantes:
                quedada = None
        nueva = {
            "clave": clave, "mencion": mencion, "persona_id": persona_id,
            "persona_dudosa": dudosa, "candidatos": list(dict.fromkeys(candidatos)),
            "pendientes": _lista_textos(entrada.get("pendientes")),
            "preguntas": _lista_textos(entrada.get("preguntas")),
            "quedada": quedada, "datos": _lista_textos(entrada.get("datos")),
            "confirmado": False,
        }
        if not any(nueva[campo] for campo in ("pendientes", "preguntas", "datos")) \
                and nueva["quedada"] is None:
            continue
        # Qwen puede nombrar a la misma persona de dos maneras. Se funden en un
        # solo bloque siempre que la identidad resuelta sea la misma.
        existente = next((p for p in personas if persona_id and p["persona_id"] == persona_id), None)
        if existente:
            for campo in ("pendientes", "preguntas", "datos"):
                existente[campo] = list(dict.fromkeys(existente[campo] + nueva[campo]))
            if existente["quedada"] is None:
                existente["quedada"] = quedada
            existente["persona_dudosa"] = existente["persona_dudosa"] or dudosa
            existente["candidatos"] = list(dict.fromkeys(existente["candidatos"] + candidatos))
            existente["mencion"] = " / ".join(filter(None, dict.fromkeys([existente["mencion"], mencion])))
        else:
            personas.append(nueva)
    ajustar_identidades_por_grupo(personas, contexto)
    pulir_contenido_personas(personas, por_id, grabado)
    quedadas = [p["quedada"] for p in personas if p.get("quedada")]
    if quedadas:
        comun = max(quedadas, key=lambda q: len(q.get("texto", "")))
        for bloque in personas:
            if bloque.get("quedada"):
                bloque["quedada"] = dict(comun)
    asignado = " ".join(
        texto for p in personas for texto in (
            p.get("pendientes", []) + p.get("preguntas", []) + p.get("datos", []) +
            ([p["quedada"]["resumen"], p["quedada"]["texto"]] if p.get("quedada") else [])
        )
    ).lower()
    sin_asignar = [
        texto for texto in _lista_textos((bruto or {}).get("sin_asignar"))
        if texto.lower() not in asignado
    ]
    return {
        "version": CONTRATO_BORRADOR,
        "personas": confirmadas + personas,
        "sin_asignar": sin_asignar,
        "avisos": _lista_textos((bruto or {}).get("avisos")),
        "quedadas_guardadas": anterior.get("quedadas_guardadas", {}),
    }


def _solicitar_json_qwen_una_vez(mensajes, formato, pensar):
    max_tokens = (
        MAX_TOKENS_QWEN_PENSANDO if pensar else MAX_TOKENS_QWEN_DIRECTO
    )
    peticion = {
        "model": MODELO_QWEN,
        "stream": False,
        "think": pensar,
        "format": formato or contrato_qwen(),
        "options": {"temperature": 0, "num_predict": max_tokens},
        "messages": mensajes,
    }
    req = urllib.request.Request(
        OLLAMA_CHAT,
        data=json.dumps(peticion, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=ESPERA_QWEN_SEGUNDOS) as respuesta:
        cuerpo = json.loads(respuesta.read().decode("utf-8"))
    contenido = cuerpo.get("message", {}).get("content", "")
    if not isinstance(contenido, str) or not contenido.strip():
        raise ValueError("Qwen no devolvió contenido JSON")
    return json.loads(contenido)


def solicitar_json_qwen(mensajes, formato=None, pensar=True):
    """Pide JSON acotado y abandona el razonamiento si se queda desbocado."""
    try:
        return _solicitar_json_qwen_una_vez(mensajes, formato, pensar)
    except Exception:
        if not pensar:
            raise
        try:
            return _solicitar_json_qwen_una_vez(mensajes, formato, False)
        except Exception as segundo_error:
            raise RuntimeError(
                "Qwen no devolvió un borrador válido tras el segundo intento"
            ) from segundo_error


def pedir_borrador_qwen(transcripcion, grabado, contexto, anterior=None):
    confirmadas = [
        {"persona_id": p.get("persona_id"), "mencion": p.get("mencion")}
        for p in (anterior or {}).get("personas", []) if p.get("confirmado")
    ]
    instrucciones = """Devuelve únicamente el JSON pedido. La persona que habla es siempre la marcada es_yo.
Tu trabajo no es resumir sin más: decide qué será útil recordar o preguntar en la próxima conversación y clasifícalo correctamente.
Convierte la voz en bloques editables por persona existente; nunca inventes ni crees personas.

REGLAS DE CLASIFICACIÓN:
- pendientes: acciones concretas que debe hacer la persona es_yo por o para la otra persona. No incluyas acciones que hará la otra persona ni inventes compromisos.
- preguntas: asuntos futuros o en evolución de la vida de la otra persona sobre los que tendría sentido interesarse después, aunque quien habla no diga literalmente «tengo que preguntar». El rótulo de la interfaz ya dice «Preguntar por», así que escribe sólo un asunto nominal breve, nunca una pregunta completa ni una frase de agenda. La fecha exacta pertenece al texto completo de la quedada; sólo inclúyela aquí si resulta imprescindible para distinguir dos asuntos iguales. No conviertas recados rutinarios, compras o visitas a tiendas en preguntas salvo petición explícita.
- datos: hechos estables que seguirán siendo útiles dentro de meses. No metas planes temporales, viajes próximos, compras puntuales, detalles que sólo pertenecen a esta conversación ni el nombre de la propia persona.
- quedada: registro adaptado del encuentro actual. Su fecha es fecha_grabacion salvo que la voz diga inequívocamente que el encuentro ocurrió antes; resuelve entonces esa fecha con el calendario. Una fecha futura mencionada como plan nunca es la fecha de la quedada. Sólo llevan esta quedada las personas que participaron en el encuentro, no quienes únicamente se nombran al hablar de un plan futuro. El canal describe cómo hablaron: usa «Llamada», «Mensaje», «Videollamada» o «En persona». Un lugar como una casa, una piscina o una plaza pertenece al relato y nunca es el canal. Si no se sabe, deja canal vacío.

Cada bloque admite cero o más pendientes, preguntas y datos, y como máximo una quedada. Si una misma conversación incluye a varias personas, repite en sus bloques exactamente la misma quedada para que se guarde como un único encuentro compartido.
La quedada necesita fecha ISO, canal, resumen claro de una sola línea (máximo 160 caracteres) y texto completo adaptado; no copies literalmente la transcripción. El resumen está dentro de la ficha de esa persona: no empieces repitiendo su nombre. Debe sonar a recuerdo natural, comenzar como una frase de conversación y emplear referencias temporales relativas. En el resumen están prohibidos fechas, días de la semana, horas y cronologías: esos detalles sólo pertenecen al texto completo. El texto completo sí conserva la precisión y usa discurso indirecto natural. Redacta siempre desde el punto de vista de quien habla, no como una ficha policial ni como un teletipo. Respeta el tiempo de cada hecho y no unas dos acciones distintas en una sola.

FECHAS:
Resuelve expresiones relativas con calendario_cercano y el tiempo verbal. El texto completo debe decir «viernes 7 de agosto», no sólo «el viernes», y «martes 11 de agosto», no sólo «el 11». El resumen puede decir «esa misma semana» porque se muestra junto a la fecha de la conversación. Las preguntas priorizan cómo hablarías con esa persona y normalmente omiten la fecha. Si de verdad no se puede resolver, no inventes: conserva la expresión y explica la duda en avisos.
Una expresión como «luego por la tarde» sin otro día explícito continúa el día de la conversación, no un viaje futuro mencionado antes.

Resuelve identidades usando nombre, apodo, pronunciación aproximada, relaciones, círculo y coherencia del grupo mencionado. Un grupo conectado pesa más que otra persona homónima sin relación con él.
Las expresiones como «mi madre» se interpretan desde es_yo. Variantes como Carmela/Karmela y «mi madre» deben acabar en un solo bloque si son la misma persona.
Si el contexto no basta, elige el id existente más probable, marca persona_dudosa=true e incluye candidatos razonables. No uses porcentajes.
No copies nombres propios, lugares, hechos ni fechas de estas instrucciones: todo el contenido debe proceder de transcripcion y libreta.
No vuelvas a producir información de ya_confirmados. No incluyas nunca a es_yo como destinataria: esta aplicación no es un diario de quien habla.
Usa ortografía española correcta. Lo imposible de atribuir va en sin_asignar. Nunca repitas allí algo que ya esté dentro de un bloque."""
    try:
        fecha_base = date.fromisoformat(str(grabado)[:10])
    except ValueError:
        fecha_base = date.today()
    dias_semana = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    calendario = [
        {
            "iso": (fecha_base.fromordinal(fecha_base.toordinal() + salto)).isoformat(),
            "dia": dias_semana[fecha_base.fromordinal(fecha_base.toordinal() + salto).weekday()],
        }
        for salto in range(-7, 22)
    ]
    contenido = {
        "fecha_grabacion": str(grabado)[:10],
        "calendario_cercano": calendario,
        "libreta": contexto,
        "ya_confirmados": confirmadas,
        "transcripcion": transcripcion,
    }
    bruto = solicitar_json_qwen([
        {"role": "system", "content": instrucciones},
        {"role": "user", "content": json.dumps(contenido, ensure_ascii=False)},
    ])
    revision = """Audita y corrige la propuesta usando la transcripción y el calendario. Devuelve el contrato completo, no una explicación.
Comprueba una por una estas condiciones:
1. Todo acontecimiento futuro significativo de la otra persona genera un asunto nominal natural en preguntas, aunque no se pidiera explícitamente. Empezar un trabajo, una mudanza, un viaje o un cambio vital merece seguimiento. Como la interfaz ya muestra «Preguntar por», no redactes otra pregunta ni uses signos de interrogación. Una compra ya terminada va a Datos si es estable y relevante, pero no genera además una pregunta salvo que se mencione un problema. Omite fechas de agenda salvo que sean necesarias para distinguir asuntos. No incluyas compras rutinarias, tiendas o recados salvo petición explícita.
2. pendientes sólo contiene acciones que debe hacer quien habla.
3. datos sólo contiene hechos estables que seguirán siendo útiles dentro de seis meses. Elimina viajes, horarios, planes, compras y sucesos puntuales: ya quedan en la quedada.
4. Resuelve la fecha real del encuentro: usa fecha_grabacion salvo que la transcripción diga claramente que ocurrió antes. Una fecha futura de un plan no puede convertirse en fecha de quedada. El canal es el medio («En persona», «Llamada», «Mensaje» o «Videollamada»), nunca el lugar concreto. Sólo asigna la quedada a quienes participaron en ese encuentro; una persona meramente mencionada no estuvo allí. Ningún resumen ni texto empieza repitiendo el nombre. El resumen es una frase humana de conversación, no una cronología telegráfica, y NO puede contener cifras, fechas, horas, meses ni días de la semana.
5. El texto completo usa discurso indirecto natural desde quien habla y contiene las fechas exactas que sí pertenezcan al relato. No dejes referencias como «ayer», «hoy» ni un día del mes sin mes cuando el calendario permita resolverlas. Haz una lista mental de cada hecho explícito de la transcripción —personas, plan, transporte, fecha, compras, trabajo, horarios, regresos, vacaciones y lugar— y comprueba que todos siguen en el texto completo. Audita por separado el tiempo verbal de cada afirmación: lo ya ocurrido sigue en pasado y los planes siguen siendo planes. No fusiones acciones distintas. No pierdas información verdadera ni inventes otra; conserva también las dudas expresadas.
6. Una misma persona no se duplica y sin_asignar no repite contenido ya clasificado. Elimina cualquier bloque cuya persona sea es_yo.
7. No reutilices ningún ejemplo ni conocimiento de otras conversaciones: nombres, lugares, fechas y hechos deben aparecer literalmente o deducirse de esta transcripción."""
    revisado = solicitar_json_qwen([
        {"role": "system", "content": revision},
        {"role": "user", "content": json.dumps({
            "transcripcion": transcripcion,
            "fecha_grabacion": str(grabado)[:10],
            "calendario_cercano": calendario,
            "propuesta": bruto,
        }, ensure_ascii=False)},
    ])
    quedadas_revisadas = [
        persona["quedada"] for persona in revisado.get("personas", [])
        if isinstance(persona, dict) and isinstance(persona.get("quedada"), dict)
    ]
    if quedadas_revisadas:
        quedadas_iniciales = [
            persona["quedada"] for persona in bruto.get("personas", [])
            if isinstance(persona, dict) and isinstance(persona.get("quedada"), dict)
        ]
        texto_schema = {"type": "string", "minLength": 1}
        contrato_redaccion = {
            "type": "object",
            "properties": {"resumen": texto_schema, "texto": texto_schema},
            "required": ["resumen", "texto"],
            "additionalProperties": False,
        }
        contrato_hechos = {
            "type": "object",
            "properties": {
                "hechos": {"type": "array", "items": texto_schema},
            },
            "required": ["hechos"],
            "additionalProperties": False,
        }
        inventario = solicitar_json_qwen([
            {
                "role": "system",
                "content": """Extrae todos los hechos explícitos de la transcripción, uno por elemento y sin resumirlos entre sí. No clasifiques ni redactes la quedada. Conserva por separado participantes del encuentro, personas sólo mencionadas, planes, acompañantes, transporte, fechas, horas, compras, trabajo, viajes pasados, vacaciones y lugares. Resuelve ayer, hoy y fechas cercanas con el calendario. No inventes nada.""",
            },
            {
                "role": "user",
                "content": json.dumps({
                    "transcripcion": transcripcion,
                    "fecha_grabacion": str(grabado)[:10],
                    "calendario_cercano": calendario,
                }, ensure_ascii=False),
            },
        ], formato=contrato_hechos, pensar=False)
        redaccion = solicitar_json_qwen([
            {
                "role": "system",
                "content": """Redacta únicamente el resumen y el texto completo de la quedada.
El resumen es una sola frase natural de conversación, sin nombres repetidos, cifras, fechas, horas ni días de la semana.
El texto completo está contado desde quien habla, con lenguaje natural y no como acta o transcripción literal. No lo resumas: adapta todo lo dicho. Antes de redactarlo, haz un inventario interno de todos los hechos explícitos de la transcripción y de la extracción inicial y comprueba que ninguno desaparece: quién participó, quién sólo fue mencionado, planes, acompañantes, transporte, fechas, horarios, cambios personales, viajes ya ocurridos y lugares. La propuesta revisada puede haber perdido detalles; recupéralos de la transcripción y de la extracción inicial. Resuelve fechas relativas con el calendario. Conserva dudas y no inventes hechos. Los ejemplos o conversaciones anteriores no son una fuente.""",
            },
            {
                "role": "user",
                "content": json.dumps({
                    "transcripcion": transcripcion,
                    "fecha_grabacion": str(grabado)[:10],
                    "calendario_cercano": calendario,
                    "inventario_de_hechos": inventario["hechos"],
                    "extraccion_inicial": max(
                        quedadas_iniciales, key=lambda q: len(q.get("texto", ""))
                    ) if quedadas_iniciales else None,
                    "redaccion_propuesta": max(
                        quedadas_revisadas, key=lambda q: len(q.get("texto", ""))
                    ),
                }, ensure_ascii=False),
            },
        ], formato=contrato_redaccion, pensar=False)
        for persona in revisado.get("personas", []):
            if isinstance(persona, dict) and isinstance(persona.get("quedada"), dict):
                persona["quedada"]["resumen"] = redaccion["resumen"]
                persona["quedada"]["texto"] = redaccion["texto"]
    return normalizar_borrador(
        revisado, contexto, grabado, anterior, transcripcion=transcripcion
    )


def nombres_para_whisper(contexto):
    nombres = []
    for persona in contexto["personas"]:
        for nombre in (persona.get("nombre"), persona.get("apodo")):
            nombre = (nombre or "").strip()
            if nombre and nombre not in nombres:
                nombres.append(nombre)
    return ", ".join(nombres)


def transcribir_audio(ruta, contexto):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        try:
            _whisper = WhisperModel(MODELO_WHISPER, device="cuda", compute_type="float16")
        except Exception:
            _whisper = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
    nombres = nombres_para_whisper(contexto)
    segmentos, _ = _whisper.transcribe(
        str(ruta), language="es", vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False, hotwords=nombres, initial_prompt=nombres,
    )
    return " ".join(s.text.strip() for s in segmentos if s.text.strip()).strip()


def _tomar_audio(estado, trabajando):
    con = conexion()
    with con:
        fila = con.execute(
            "SELECT * FROM audio WHERE estado = ? ORDER BY grabado, id LIMIT 1",
            (estado,),
        ).fetchone()
        if fila:
            con.execute(
                "UPDATE audio SET estado = ?, error = NULL, actualizado = ? WHERE id = ?",
                (trabajando, ahora_iso(), fila["id"]),
            )
    con.close()
    return dict(fila) if fila else None


def procesar_modelos():
    while True:
        _aviso_modelos.wait(2)
        _aviso_modelos.clear()
        while True:
            audio = _tomar_audio("pendiente", "transcribiendo")
            if audio:
                try:
                    con = conexion()
                    contexto = contexto_para_qwen(con)
                    con.close()
                    ruta = CARPETA_AUDIOS / Path(audio["archivo"]).name
                    texto = transcribir_audio(ruta, contexto)
                    if not texto:
                        raise ValueError("Whisper no encontró voz")
                    con = conexion()
                    with con:
                        con.execute(
                            "UPDATE audio SET transcripcion = ?, transcripcion_editada = 0, "
                            "estado = 'analisis_pendiente', actualizado = ? "
                            "WHERE id = ? AND estado = 'transcribiendo'",
                            (texto, ahora_iso(), audio["id"]),
                        )
                    con.close()
                except Exception as exc:
                    con = conexion()
                    with con:
                        con.execute(
                            "UPDATE audio SET estado = 'error_transcripcion', error = ?, actualizado = ? "
                            "WHERE id = ? AND estado = 'transcribiendo'",
                            (str(exc)[:500], ahora_iso(), audio["id"]),
                        )
                    con.close()
                    print(f"Audio {audio['id']}: no se pudo transcribir: {exc}")
                continue

            audio = _tomar_audio("analisis_pendiente", "analizando")
            if audio:
                try:
                    con = conexion()
                    contexto = contexto_para_qwen(con)
                    anterior = json.loads(audio["borrador"]) if audio.get("borrador") else None
                    con.close()
                    borrador = pedir_borrador_qwen(
                        audio["transcripcion"], audio["grabado"], contexto, anterior
                    )
                    con = conexion()
                    with con:
                        con.execute(
                            "UPDATE audio SET borrador = ?, estado = 'listo', error = NULL, "
                            "contrato_version = ?, actualizado = ? "
                            "WHERE id = ? AND estado = 'analizando'",
                            (json.dumps(borrador, ensure_ascii=False), CONTRATO_BORRADOR,
                             ahora_iso(), audio["id"]),
                        )
                    con.close()
                except Exception as exc:
                    con = conexion()
                    with con:
                        con.execute(
                            "UPDATE audio SET estado = 'error_analisis', error = ?, actualizado = ? "
                            "WHERE id = ? AND estado = 'analizando'",
                            (str(exc)[:500], ahora_iso(), audio["id"]),
                        )
                    con.close()
                    print(f"Audio {audio['id']}: Qwen no pudo preparar el borrador: {exc}")
                continue
            break


def iniciar_modelos():
    global _hilo_modelos
    if os.environ.get("RELACIONES_SIN_MODELOS") == "1":
        return
    if _hilo_modelos is None or not _hilo_modelos.is_alive():
        _hilo_modelos = threading.Thread(
            target=procesar_modelos, name="modelos-locales", daemon=True
        )
        _hilo_modelos.start()
    _aviso_modelos.set()


@app.on_event("startup")
def arrancar_modelos_locales():
    iniciar_modelos()

def _json(datos, status=200):
    return Response(
        json.dumps(datos), media_type="application/json", status_code=status
    )


@app.post("/audio")
async def subir_audio(archivo: UploadFile = File(...), grabado: str = Form("")):
    """Recibe un audio del móvil y lo guarda. Responde JSON, no 303: la subida
    la hace un fetch desde MediaRecorder, no un formulario. Es la segunda
    excepción a «POST + redirección», junto con la subida en dos de la foto."""
    datos = await archivo.read(MAX_AUDIO_BYTES + 1)
    if not datos:
        return _json({"ok": False, "motivo": "vacio"}, 400)
    if len(datos) > MAX_AUDIO_BYTES:
        return _json({"ok": False, "motivo": "grande"}, 413)

    tipo = (archivo.content_type or "").split(";")[0].strip().lower()
    ext = EXT_POR_MIME.get(tipo) or Path(archivo.filename or "").suffix.lower()
    if ext not in EXT_POR_MIME.values():
        ext = ".webm"

    # La fecha de grabación la manda el móvil; si no llega o no se entiende, se
    # usa la de llegada, que con la cola offline puede ser bastante posterior.
    try:
        grabado_iso = datetime.fromisoformat(
            grabado.strip()[:19]
        ).isoformat(timespec="seconds")
    except ValueError:
        grabado_iso = ahora_iso()

    CARPETA_AUDIOS.mkdir(exist_ok=True)
    sello = grabado_iso.replace(":", "").replace("-", "").replace("T", "-")
    nombre = f"{sello}-{secrets.token_hex(3)}{ext}"
    destino = CARPETA_AUDIOS / nombre
    temporal = CARPETA_AUDIOS / f".{nombre}.subiendo"
    con = conexion()
    try:
        temporal.write_bytes(datos)
        con.execute("BEGIN")
        cur = con.execute(
            "INSERT INTO audio (archivo, grabado, estado) "
            "VALUES (?, ?, 'pendiente')",
            (nombre, grabado_iso),
        )
        temporal.replace(destino)
        con.commit()
        audio_id = cur.lastrowid
    except (OSError, sqlite3.Error):
        con.rollback()
        for ruta in (temporal, destino):
            try:
                ruta.unlink(missing_ok=True)
            except OSError:
                pass
        con.close()
        return _json({"ok": False, "motivo": "guardar"}, 500)
    con.close()
    iniciar_modelos()
    return _json({"ok": True, "id": audio_id})


def _cargar_borrador_audio(con, audio_id):
    fila = con.execute("SELECT * FROM audio WHERE id = ?", (audio_id,)).fetchone()
    if fila is None:
        return None, None
    try:
        borrador = json.loads(fila["borrador"]) if fila["borrador"] else {
            "version": CONTRATO_BORRADOR, "personas": [],
            "sin_asignar": [], "avisos": [], "quedadas_guardadas": {},
        }
    except json.JSONDecodeError:
        borrador = {"version": CONTRATO_BORRADOR, "personas": []}
    return fila, borrador


def _buscar_bloque(borrador, clave):
    return next((
        bloque for bloque in borrador.get("personas", [])
        if bloque.get("clave") == clave and not bloque.get("confirmado")
    ), None)


def _estado_revision_audio(borrador):
    pendientes = any(
        not bloque.get("confirmado")
        for bloque in borrador.get("personas", [])
    )
    return "listo" if pendientes else "revisado"


@app.post("/audio/{audio_id}/volver-a-analizar")
def volver_a_analizar_audio(audio_id: int, volver: str = Form("/nota")):
    con = conexion()
    with con:
        con.execute(
            "UPDATE audio SET estado = 'pendiente', transcripcion = NULL, "
            "transcripcion_editada = 0, error = NULL, actualizado = ? WHERE id = ?",
            (ahora_iso(), audio_id),
        )
    con.close()
    iniciar_modelos()
    return vuelve(volver)


@app.post("/audio/{audio_id}/enviar-a-qwen")
def enviar_texto_a_qwen(
    audio_id: int, transcripcion: str = Form(""), volver: str = Form("/nota"),
):
    texto = transcripcion.strip()
    if texto:
        con = conexion()
        with con:
            con.execute(
                "UPDATE audio SET transcripcion = ?, transcripcion_editada = 1, "
                "estado = 'analisis_pendiente', error = NULL, actualizado = ? WHERE id = ?",
                (texto, ahora_iso(), audio_id),
            )
        con.close()
        iniciar_modelos()
    return vuelve(volver)


@app.post("/audio/{audio_id}/persona/{clave}/resolver")
def resolver_persona_audio(
    audio_id: int, clave: str, persona_id: int = Form(...),
    volver: str = Form("/nota"),
):
    con = conexion()
    fila, borrador = _cargar_borrador_audio(con, audio_id)
    bloque = _buscar_bloque(borrador, clave) if borrador else None
    existe = con.execute("SELECT 1 FROM persona WHERE id = ?", (persona_id,)).fetchone()
    if fila and bloque and existe:
        bloque["persona_id"] = persona_id
        bloque["persona_dudosa"] = False
        bloque["candidatos"] = list(dict.fromkeys([persona_id] + bloque.get("candidatos", [])))
        bloque.pop("aviso", None)
        with con:
            con.execute(
                "UPDATE audio SET borrador = ?, estado = 'listo', actualizado = ? WHERE id = ?",
                (json.dumps(borrador, ensure_ascii=False), ahora_iso(), audio_id),
            )
    con.close()
    return vuelve(volver)


@app.post("/audio/{audio_id}/persona/{clave}/eliminar")
def eliminar_bloque_audio(
    audio_id: int, clave: str, volver: str = Form("/nota"),
):
    """Retira una propuesta sin guardar nada ni modificar la ficha personal."""
    con = conexion()
    fila, borrador = _cargar_borrador_audio(con, audio_id)
    bloque = _buscar_bloque(borrador, clave) if borrador else None
    if fila and bloque:
        borrador["personas"] = [
            candidato for candidato in borrador.get("personas", [])
            if candidato is not bloque
        ]
        with con:
            con.execute(
                "UPDATE audio SET borrador = ?, estado = ?, actualizado = ? "
                "WHERE id = ?",
                (json.dumps(borrador, ensure_ascii=False),
                 _estado_revision_audio(borrador), ahora_iso(), audio_id),
            )
    con.close()
    return vuelve(volver)


def _editar_bloque_formulario(
    bloque, pendientes, preguntas, datos, quedada_fecha, quedada_canal,
    quedada_resumen, quedada_texto,
):
    bloque["pendientes"] = [t.strip() for t in pendientes if t.strip()]
    bloque["preguntas"] = [t.strip() for t in preguntas if t.strip()]
    bloque["datos"] = [t.strip() for t in datos if t.strip()]
    fecha = quedada_fecha.strip()
    canal = quedada_canal.strip()
    resumen = quedada_resumen.strip()
    texto = quedada_texto.strip()
    if fecha or canal or resumen or texto:
        try:
            fecha = date.fromisoformat(fecha).isoformat()
        except ValueError:
            fecha = ""
        bloque["quedada"] = {
            "fecha": fecha, "canal": canal, "resumen": resumen, "texto": texto,
        }
    else:
        bloque["quedada"] = None


def _bloque_guardable(bloque):
    if not bloque.get("persona_id") or bloque.get("persona_dudosa"):
        return False, "Confirma primero de quién se trata."
    quedada = bloque.get("quedada")
    if quedada and not all(quedada.get(campo) for campo in ("fecha", "resumen", "texto")):
        return False, "La quedada necesita día, resumen y texto completo."
    hay = any(bloque.get(campo) for campo in ("pendientes", "preguntas", "datos")) or quedada
    if not hay:
        return False, "Este bloque no contiene nada que guardar."
    return True, ""


def _guardar_bloque_audio(con, audio_id, borrador, bloque):
    persona_id = bloque["persona_id"]
    for campo, tipo in (("pendientes", "pendiente"), ("preguntas", "preguntar")):
        for texto in bloque.get(campo, []):
            cur = con.execute(
                "INSERT INTO hilo (persona_id, texto, abierto_desde, tipo) VALUES (?, ?, ?, ?)",
                (persona_id, texto, hoy_iso(), tipo),
            )
            con.execute(
                "INSERT OR IGNORE INTO audio_registro VALUES (?, 'hilo', ?, ?)",
                (audio_id, cur.lastrowid, persona_id),
            )
    for texto in bloque.get("datos", []):
        cur = con.execute(
            "INSERT INTO hecho (persona_id, texto, creado) VALUES (?, ?, ?)",
            (persona_id, texto, ahora_iso()),
        )
        con.execute(
            "INSERT OR IGNORE INTO audio_registro VALUES (?, 'hecho', ?, ?)",
            (audio_id, cur.lastrowid, persona_id),
        )
    quedada = bloque.get("quedada")
    if quedada:
        firma = json.dumps(
            [quedada["fecha"], quedada.get("canal", ""),
             quedada["resumen"], quedada["texto"]],
            ensure_ascii=False,
        )
        guardadas = borrador.setdefault("quedadas_guardadas", {})
        nota_id = guardadas.get(firma)
        if nota_id and not con.execute("SELECT 1 FROM nota WHERE id = ?", (nota_id,)).fetchone():
            nota_id = None
        if not nota_id:
            cur = con.execute(
                "INSERT INTO nota (fecha, canal, texto, resumen, creada) VALUES (?, ?, ?, ?, ?)",
                (quedada["fecha"], quedada.get("canal", ""),
                 quedada["texto"], quedada["resumen"], ahora_iso()),
            )
            nota_id = cur.lastrowid
            guardadas[firma] = nota_id
        con.execute(
            "INSERT OR IGNORE INTO nota_persona (nota_id, persona_id) VALUES (?, ?)",
            (nota_id, persona_id),
        )
        con.execute(
            "INSERT OR IGNORE INTO audio_registro VALUES (?, 'nota', ?, ?)",
            (audio_id, nota_id, persona_id),
        )
    bloque["confirmado"] = True
    bloque.pop("aviso", None)


@app.post("/audio/{audio_id}/persona/{clave}/confirmar")
def confirmar_persona_audio(
    audio_id: int, clave: str,
    pendientes: list[str] = Form(default=[]),
    preguntas: list[str] = Form(default=[]),
    datos: list[str] = Form(default=[]),
    quedada_fecha: str = Form(""),
    quedada_canal: str = Form(""),
    quedada_resumen: str = Form(""),
    quedada_texto: str = Form(""),
    volver: str = Form("/nota"),
):
    con = conexion()
    fila, borrador = _cargar_borrador_audio(con, audio_id)
    bloque = _buscar_bloque(borrador, clave) if borrador else None
    if fila and bloque:
        _editar_bloque_formulario(
            bloque, pendientes, preguntas, datos,
            quedada_fecha, quedada_canal, quedada_resumen, quedada_texto,
        )
        guardable, aviso = _bloque_guardable(bloque)
        with con:
            if guardable:
                _guardar_bloque_audio(con, audio_id, borrador, bloque)
            else:
                bloque["aviso"] = aviso
            con.execute(
                "UPDATE audio SET borrador = ?, estado = ?, actualizado = ? WHERE id = ?",
                (json.dumps(borrador, ensure_ascii=False),
                 _estado_revision_audio(borrador), ahora_iso(), audio_id),
            )
    con.close()
    return vuelve(volver)


@app.get("/audios")
def pantalla_audios(
    request: Request, volver: str = "/nota", audios_pagina: int = 1,
):
    """La lista de audios subidos, para confirmar que han llegado. Vive dentro
    de Notas: es el archivo de las grabaciones de voz."""
    con = conexion()
    datos = archivo_audios(con, audios_pagina, "/audios")
    datos["volver"] = volver
    con.close()
    return plantillas.TemplateResponse(request, "audios.html", datos)


@app.get("/audio/{audio_id}")
def oir_audio(audio_id: int):
    """Sirve el archivo para poder volver a escuchar el original."""
    con = conexion()
    fila = con.execute(
        "SELECT archivo FROM audio WHERE id = ?", (audio_id,)
    ).fetchone()
    con.close()
    if fila is None:
        return Response(status_code=404)
    ruta = CARPETA_AUDIOS / Path(fila["archivo"]).name
    if not ruta.exists():
        return Response(status_code=404)
    return FileResponse(ruta)


@app.post("/audio/{audio_id}/borrar")
def borrar_audio(audio_id: int, volver: str = Form("/audios")):
    """Borrado manual compensado: fila y archivo se retiran como una unidad."""
    con = conexion()
    fila = con.execute(
        "SELECT archivo FROM audio WHERE id = ?", (audio_id,)
    ).fetchone()
    if fila is None:
        con.close()
        return vuelve(volver, "/audios")

    origen = CARPETA_AUDIOS / Path(fila["archivo"]).name
    apartado = None
    try:
        if origen.exists():
            CARPETA_AUDIOS_BORRADOS.mkdir(exist_ok=True)
            apartado = CARPETA_AUDIOS_BORRADOS / (
                f"{secrets.token_hex(4)}-{origen.name}"
            )
            origen.replace(apartado)
        con.execute("BEGIN")
        con.execute("DELETE FROM audio WHERE id = ?", (audio_id,))
        con.commit()
    except (OSError, sqlite3.Error):
        con.rollback()
        if apartado is not None and apartado.exists() and not origen.exists():
            try:
                apartado.replace(origen)
            except OSError:
                pass
        con.close()
        return vuelve(volver, "/audios")
    con.close()
    if apartado is not None:
        try:
            apartado.unlink(missing_ok=True)
        except OSError:
            pass
    return vuelve(volver, "/audios")


# --------------------------------------------------------------------------
# 5. el JSON de la red. Sólo personas: los temas ya no existen, el circulo
#    hace ese trabajo. Los ids de las aristas van prefijados: p3.
# --------------------------------------------------------------------------

COSAS_EN_LA_RED = 3       # cuántas pendientes y cuántas por preguntar
DATOS_EN_LA_RED = 3       # una vista breve de lo que no caduca
QUEDADAS_EN_LA_RED = 2    # un par de líneas de lo último
LARGO_QUEDADA = 150       # el texto se corta, que la ficha flotante es pequeña


@app.get("/api/grafo")
def api_grafo():
    con = conexion()

    personas = [dict(f) for f in con.execute(
        "SELECT p.id, "
        f"       {NOMBRE_VISIBLE_SQL} AS nombre,"
        "       p.nombre AS nombre_completo, p.apodo,"
        "       p.color, p.circulo_id AS circulo_id,"
        "       CASE WHEN p.foto IS NOT NULL AND p.foto <> '' THEN 1 ELSE 0 END"
        "         AS foto,"
        "       c.nombre AS circulo,"
        "       (SELECT COUNT(*) FROM nota_persona np WHERE np.persona_id = p.id)"
        "         AS notas,"
        "       (SELECT MAX(n.fecha) FROM nota n"
        "          JOIN nota_persona np ON np.nota_id = n.id"
        "         WHERE np.persona_id = p.id) AS ultima_nota"
        "  FROM persona p LEFT JOIN circulo c ON c.id = p.circulo_id"
        " ORDER BY nombre COLLATE NOCASE"
    )]
    por_id = {p["id"]: p for p in personas}
    central = next(
        (
            p for p in personas
            if (p["circulo"] or "").strip().casefold() == "yo"
        ),
        None,
    )
    central_id = central["id"] if central else None
    for p in personas:
        p["central"] = p["id"] == central_id
        p["hablamos"] = cuanto(p["ultima_nota"])
        p["pendiente"] = []
        p["preguntar"] = []
        p["datos"] = []
        p["quedadas"] = []
        p["relaciones"] = []

    for f in con.execute(
        "SELECT persona_id, texto, tipo FROM hilo WHERE cerrado_el IS NULL"
        " ORDER BY abierto_desde DESC, id DESC"
    ):
        p = por_id.get(f["persona_id"])
        if p is None:
            continue
        cola = p["pendiente"] if f["tipo"] == "pendiente" else p["preguntar"]
        if len(cola) < COSAS_EN_LA_RED:
            cola.append(f["texto"])

    for f in con.execute(
        "SELECT persona_id, texto FROM hecho ORDER BY id DESC"
    ):
        p = por_id.get(f["persona_id"])
        if p is not None and len(p["datos"]) < DATOS_EN_LA_RED:
            p["datos"].append(f["texto"])

    for f in con.execute(
        "SELECT np.persona_id, n.fecha, n.canal, n.texto, n.resumen FROM nota n"
        "  JOIN nota_persona np ON np.nota_id = n.id"
        " ORDER BY n.fecha DESC, n.id DESC"
    ):
        p = por_id.get(f["persona_id"])
        if p is None or len(p["quedadas"]) >= QUEDADAS_EN_LA_RED:
            continue
        texto = (f["resumen"] or f["texto"]).strip().replace("\n", " ")
        if len(texto) > LARGO_QUEDADA:
            texto = texto[:LARGO_QUEDADA].rstrip() + "…"
        p["quedadas"].append(
            {"cuando": fecha_corta(f["fecha"]), "canal": f["canal"] or "",
             "texto": texto}
        )

    for f in con.execute("SELECT * FROM relacion"):
        a, b = por_id.get(f["persona_a"]), por_id.get(f["persona_b"])
        if a and b:
            a["relaciones"].append(
                {"id": b["id"], "nombre": b["nombre"], "etiqueta": f["etiqueta"]}
            )
            b["relaciones"].append(
                {"id": a["id"], "nombre": a["nombre"],
                 "etiqueta": f["etiqueta_inversa"] or f["etiqueta"]}
            )

    # Aristas: quien está en el círculo «Yo» ocupa el centro. Toda persona con
    # círculo se enlaza directamente con ella; quien no tiene círculo sólo
    # aparece a través de otras personas. Las relaciones y quedadas compartidas
    # siguen tejiendo el resto de la red.
    parejas = {}
    for f in con.execute("SELECT persona_a, persona_b FROM relacion"):
        pareja = (min(f[0], f[1]), max(f[0], f[1]))
        parejas[pareja] = "relacion"
    for f in con.execute(
        "SELECT a.persona_id AS a, b.persona_id AS b FROM nota_persona a"
        "  JOIN nota_persona b ON a.nota_id = b.nota_id AND a.persona_id < b.persona_id"
        " GROUP BY a.persona_id, b.persona_id"
    ):
        pareja = (f["a"], f["b"])
        parejas.setdefault(pareja, "quedada")

    if central_id is not None:
        for p in personas:
            if p["id"] == central_id:
                continue
            pareja = (min(central_id, p["id"]), max(central_id, p["id"]))
            if p["circulo_id"] is None:
                parejas.pop(pareja, None)
            else:
                parejas[pareja] = "directa"

    datos = {
        "generado": ahora_iso(),
        "central_id": central_id,
        "circulos": [dict(f) for f in con.execute(
            "SELECT id, nombre, orden FROM circulo ORDER BY orden, id"
        )],
        "personas": personas,
        "aristas": [
            {"a": f"p{a}", "b": f"p{b}", "tipo": tipo}
            for (a, b), tipo in sorted(parejas.items())
        ],
    }
    con.close()
    return datos


# --------------------------------------------------------------------------
# copia de seguridad
# --------------------------------------------------------------------------

@app.get("/exportar")
def exportar():
    """La base de datos entera en JSON. La llave de red no se exporta."""
    con = conexion()
    volcado = {"exportado": ahora_iso()}
    for tabla in TABLAS_EXPORTABLES:
        volcado[tabla] = [dict(f) for f in con.execute(f"SELECT * FROM {tabla}")]
    con.close()
    nombre = f"relaciones-{hoy_iso()}.json"
    return Response(
        json.dumps(volcado, ensure_ascii=False, indent=1),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
