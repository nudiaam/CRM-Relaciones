"""Relaciones — backend completo. Ver CLAUDE.md antes de tocar nada.

Sin ORM y sin API JSON: formularios POST y redirección 303. La única excepción
es GET /api/grafo, para que grafo.js tenga qué dibujar.

El esquema se crea al arrancar si no existe. Las bases hechas con versiones
anteriores se ponen al día en poner_al_dia(), que es idempotente.
"""

import json
import re
import secrets
import sqlite3
import sys
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
    id     INTEGER PRIMARY KEY,
    fecha  TEXT NOT NULL,
    canal  TEXT,
    texto  TEXT NOT NULL,
    creada TEXT NOT NULL
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
    id      INTEGER PRIMARY KEY,
    archivo TEXT NOT NULL,                       -- nombre del archivo en audios/
    grabado TEXT NOT NULL,                       -- fecha de grabación (la pone el móvil)
    estado  TEXT NOT NULL DEFAULT 'pendiente'    -- de momento siempre 'pendiente'
);
"""

TABLAS_EXPORTABLES = (
    "circulo", "persona", "hecho", "hilo", "nota", "nota_persona", "relacion",
)

# Los audios son archivos sueltos junto a la base, nunca dentro de ella. La
# carpeta viaja con el .exe igual que datos.db, y queda fuera de git y de la
# copia de todo porque contiene voz. De momento no se procesan: sólo se guardan.
CARPETA_AUDIOS = BASE_DATOS / "audios"
MAX_AUDIO_BYTES = 60 * 1024 * 1024  # una hora de voz en Opus cabe de sobra

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


def preparar():
    """Crea el esquema y las semillas si hace falta. Idempotente."""
    nueva = not RUTA_DB.exists()
    CARPETA_AUDIOS.mkdir(exist_ok=True)
    con = conexion()
    with con:
        con.executescript(ESQUEMA)
        con.execute("PRAGMA journal_mode = WAL")
        poner_al_dia(con)
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
            "SELECT n.* FROM nota n WHERE n.texto LIKE ? ESCAPE '\\' "
            "ORDER BY n.fecha DESC, n.id DESC LIMIT 50",
            (patron,),
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
            "SELECT n.fecha, n.canal, n.texto FROM nota n "
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

@app.get("/nota")
def pantalla_nota(request: Request, volver: str = "/", persona: str = ""):
    con = conexion()
    datos = {
        "fecha": hoy_iso(),
        "texto": "",
        "canal": "",
        "editando": False,
        "nota": None,
        "canales": canales(con),
        "personas": con.execute(
            SELECT_PERSONA + ORDENES["ultima"]
        ).fetchall(),
        "marcadas": [int(persona)] if persona.isdigit() else [],
        "volver": volver,
    }
    con.close()
    return plantillas.TemplateResponse(request, "nota.html", datos)


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
            "INSERT INTO nota (fecha, canal, texto, creada) VALUES (?, ?, ?, ?)",
            (fecha, canal.strip(), texto, ahora_iso()),
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
            "UPDATE nota SET fecha = ?, canal = ?, texto = ? WHERE id = ?",
            (fecha, canal.strip(), texto, nota_id),
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
# captura por voz (paso 1: sólo grabar, subir y guardar)
#
# El móvil graba con MediaRecorder y sube el audio por fetch. Aquí se guarda
# como archivo suelto en audios/ y se anota una fila que lo nombra. Nada de
# transcripción ni de IA todavía: el estado es siempre 'pendiente'. Ninguna
# se borra sola; el borrado es manual desde la lista.
# --------------------------------------------------------------------------

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
    (CARPETA_AUDIOS / nombre).write_bytes(datos)

    con = conexion()
    with con:
        cur = con.execute(
            "INSERT INTO audio (archivo, grabado, estado) "
            "VALUES (?, ?, 'pendiente')",
            (nombre, grabado_iso),
        )
        audio_id = cur.lastrowid
    con.close()
    return _json({"ok": True, "id": audio_id})


@app.get("/audios")
def pantalla_audios(request: Request, volver: str = "/nota"):
    """La lista de audios subidos, para confirmar que han llegado. Vive dentro
    de Apuntar: es apuntar por voz."""
    con = conexion()
    audios = con.execute(
        "SELECT * FROM audio ORDER BY grabado DESC, id DESC"
    ).fetchall()
    con.close()
    return plantillas.TemplateResponse(
        request, "audios.html", {"audios": audios, "volver": volver}
    )


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
    """Borrado manual: se va la fila y también el archivo del disco."""
    con = conexion()
    fila = con.execute(
        "SELECT archivo FROM audio WHERE id = ?", (audio_id,)
    ).fetchone()
    with con:
        con.execute("DELETE FROM audio WHERE id = ?", (audio_id,))
    con.close()
    if fila is not None:
        try:
            (CARPETA_AUDIOS / Path(fila["archivo"]).name).unlink(missing_ok=True)
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
        "SELECT np.persona_id, n.fecha, n.canal, n.texto FROM nota n"
        "  JOIN nota_persona np ON np.nota_id = n.id"
        " ORDER BY n.fecha DESC, n.id DESC"
    ):
        p = por_id.get(f["persona_id"])
        if p is None or len(p["quedadas"]) >= QUEDADAS_EN_LA_RED:
            continue
        texto = f["texto"].strip().replace("\n", " ")
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
