# `app.py` y `main.py`

`app.py` son ~1.550 líneas en siete secciones separadas por una banda de
guiones. `main.py` son 120 y arranca todo.

## Secciones de `app.py`

Busca el ancla con `grep`; el número es orientativo.

| Sección | Línea | Ancla |
| --- | --- | --- |
| Constantes y esquema SQL | 28 | `ESQUEMA = """` |
| Base de datos | 105 | `# base de datos` |
| Fechas y lenguaje natural | 194 | `# fechas: ISO dentro` |
| App, plantillas y la puerta | 328 | `app = FastAPI(` |
| La llave de red | 388 | `@app.get("/entrar")` |
| Consultas compartidas | 412 | `NOMBRE_VISIBLE_SQL` |
| Portada, ajustes e hilos | 466 | `@app.get("/")` |
| Personas y círculos | 525 | `PERSONAS_POR_PAGINA` |
| La ficha de una persona | 900 | `QUEDADAS_POR_PAGINA` |
| Quedadas | 1263 | `@app.get("/nota")` |
| Red y copia de todo | 1406 | `@app.get("/api/grafo")` |

## Dónde tocar según lo que quieras cambiar

| Si vas a… | Ve a | Ancla |
| --- | --- | --- |
| Cambiar el esquema o migrar la base | `poner_al_dia()` · 116 | `def poner_al_dia` |
| Añadir un círculo de fábrica | 39 | `CIRCULOS_DE_FABRICA` |
| Tocar cómo se dice una fecha en pantalla | 194–326 | `def cuanto`, `def hace`, `def fecha_natural` |
| Cambiar quién entra sin llave | `puerta()` · 352 | `async def puerta` |
| Tocar el nombre visible (apodo manda) | 416 | `NOMBRE_VISIBLE_SQL` |
| Cambiar el orden del archivador | 529 | `ORDENES = {` |
| Cambiar cuántas personas por página | 536 | `PERSONAS_POR_PAGINA` |
| Cambiar cuántas quedadas por página | 904 | `QUEDADAS_POR_PAGINA` |
| Tocar el tratamiento de fotos | 1039 | `async def cambiar_foto` |
| Crear o actualizar una relación | busca | `def enlazar(` |
| Enlazar con varias de golpe | busca | `def crear_relaciones` |
| Cambiar los avisos de foto fallida | 907 | `FALLOS_FOTO = {` |
| Tocar lo que come la red | 1406 | `def api_grafo` |
| Tocar la copia de todo | busca | `TABLAS_EXPORTABLES` |

## Rutas, todas

**GET**: `/` · `/personas` · `/persona/{id}` · `/persona/{id}/foto` · `/nota` ·
`/nota/{id}` · `/ajustes` · `/entrar` · `/salud` · `/api/grafo`

**POST**: `/entrar` · `/persona` · `/persona/{id}` · `/persona/{id}/foto` ·
`/persona/{id}/borrar` · `/persona/{id}/hecho` · `/persona/{id}/hilo` ·
`/persona/{id}/relacion` · `/persona/{id}/relaciones` · `/hecho/{id}` ·
`/hecho/{id}/borrar` ·
`/hilo/{id}/cerrar` · `/hilo/{id}/reabrir` · `/hilo/{id}/borrar` ·
`/relacion/editar` · `/relacion/borrar` · `/nota` · `/nota/{id}` ·
`/circulo` · `/circulo/{id}` · `/circulo/{id}/mover` · `/circulo/{id}/borrar`

Todas las POST terminan en redirección 303. La única que devuelve JSON es
`GET /api/grafo`.

## Anclas de redirección

Hay rutas que vuelven a un sitio concreto de la ficha. Si renombras un `id` en
`ficha.html`, hay que cambiarlas aquí:

- `/relacion/editar` y `/relacion/borrar` → `#relaciones`
- la paginación de quedadas → `#quedadas`
- cerrar, reabrir y borrar hilos → el `volver` que manda el formulario, que en
  la ficha es `#atencion`

## `main.py`

| Qué | Línea | Ancla |
| --- | --- | --- |
| El puerto, fijo | 22 | `PUERTO = 9765` |
| Comprobar que está libre | 27 | `def comprobar_puerto` |
| Arrancar uvicorn en `0.0.0.0` | 47 | `def servidor` |
| Esperar a que responda | 51 | `def espera_a_que_responda` |
| Ventana de errores del `.exe` | 69 | `def mostrar_error` |
| Abrir la ventana | 92 | `def main` |

El puerto **no se negocia**: si está ocupado, avisa y no arranca, porque
Tailscale apunta ahí.
