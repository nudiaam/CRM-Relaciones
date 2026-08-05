# `app.py` y `main.py`

`app.py` son ~2.400 líneas en siete secciones separadas por una banda de
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
| Notas y quedadas | 1378 | `@app.get("/nota")` |
| Modelos locales y voz | busca | `def contexto_para_qwen` |
| Red y copia de todo | busca | `@app.get("/api/grafo")` |

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
| Guardar la captura de una persona | 1396 | `def guardar_captura_persona` |
| Filtrar y paginar el archivo de audios | 1378 | `AUDIOS_POR_PAGINA` |
| Cambiar el contrato de Qwen | busca | `def contrato_qwen` |
| Resolver nombres por relaciones | busca | `def ajustar_identidades_por_grupo` |
| Procesar la cola de modelos | busca | `def procesar_modelos` |
| Tocar el tratamiento de fotos | 1039 | `async def cambiar_foto` |
| Crear o actualizar una relación | busca | `def enlazar(` |
| Enlazar con varias desde la ficha | busca | `def crear_relaciones` |
| Enlazar con varias al dar de alta | busca | `etiqueta_varias` |
| Cambiar los avisos de foto fallida | 907 | `FALLOS_FOTO = {` |
| Tocar lo que come la red | 1406 | `def api_grafo` |
| Tocar la copia de todo | busca | `TABLAS_EXPORTABLES` |

## Rutas, todas

**GET**: `/` · `/personas` · `/persona/{id}` · `/persona/{id}/foto` · `/nota` ·
`/nota/{id}` · `/nota/audio/{id}/proceso` · `/audios` · `/audio/{id}` · `/ajustes` · `/entrar` · `/salud` ·
`/api/grafo` · `/manifest.json` · `/sw.js`

`/manifest.json` y `/sw.js` van **en la raíz y sin llave**: el navegador los
pide antes de tener la cookie, y un service worker sólo alcanza su carpeta y
hacia abajo, así que desde `/estatico/` no cubriría la app. Los archivos viven
en `estatico/`, pero se sirven desde la raíz con su tipo MIME propio.

**POST**: `/entrar` · `/persona` · `/persona/{id}` · `/persona/{id}/foto` ·
`/persona/{id}/borrar` · `/persona/{id}/hecho` · `/persona/{id}/hilo` ·
`/persona/{id}/relacion` · `/persona/{id}/relaciones` · `/hecho/{id}` ·
`/hecho/{id}/borrar` ·
`/hilo/{id}/cerrar` · `/hilo/{id}/reabrir` · `/hilo/{id}/borrar` ·
`/relacion/editar` · `/relacion/borrar` · `/nota` · `/nota/persona/{id}` · `/nota/{id}` ·
`/nota/{id}/borrar` · `/audio` · `/audio/{id}/borrar` ·
`/audio/{id}/volver-a-analizar` · `/audio/{id}/enviar-a-qwen` ·
`/audio/{id}/persona/{clave}/resolver` · `/audio/{id}/persona/{clave}/eliminar` ·
`/audio/{id}/persona/{clave}/confirmar` ·
`/circulo` · `/circulo/{id}` · `/circulo/{id}/mover` · `/circulo/{id}/borrar`

Casi todas las POST terminan en redirección 303. Devuelven JSON `GET /api/grafo`
y `POST /audio`: esta última la llama un fetch desde el móvil, no un formulario.

## Notas y captura manual

- `nota.resumen` guarda la versión corta de una quedada. Personas y Red la
  usan en sus fichas compactas; `/persona/{id}` conserva `nota.texto` completo.
  Si una fila antigua no tiene resumen, las vistas compactas usan su texto.
- `POST /nota/persona/{id}` recibe un bloque independiente: listas repetibles
  `pendientes`, `preguntas` y `datos`, más una quedada opcional con
  `quedada_fecha`, `quedada_canal`, `quedada_resumen` y `quedada_texto`. Todo
  se guarda en una sola transacción y siempre vuelve con 303.
- El `audio_id` activo se persiste en `audio_registro` para enlazar cada hilo,
  dato o quedada confirmada con la grabación que lo originó.

## Captura por voz

Busca `# captura por voz` en `app.py` (entre las quedadas y la red).

- `audio` guarda una fila por grabación, su estado, transcripción, borrador JSON,
  error y versión del contrato. El archivo suelto
  vive en `CARPETA_AUDIOS` (`audios/`, junto a `datos.db`), nunca en la base.
  Los estados recorren espera, transcripción, análisis, revisión y revisado.
  Sigue fuera de `TABLAS_EXPORTABLES`.
- Un hilo demonio toma la cola de uno en uno: faster-whisper `large-v3` produce
  el texto y Ollama `qwen3:14b` devuelve `contrato_qwen()`. Ambos son locales.
- Qwen separa propuesta, auditoría, inventario factual y redacción final. Los
  dos últimos pasos usan esquemas mínimos para impedir que el texto adaptado
  pierda acompañantes, transporte, fechas, horas o lugares. El contrato v2
  incluye el canal de la quedada. Las preguntas guardan sólo el asunto que
  completa «Preguntar por»; el resumen usa lenguaje relativo y el texto completo
  conserva la precisión.
- `_solicitar_json_qwen_una_vez()` limita la salida tanto al razonar como al
  redactar y usa una espera máxima de tres minutos. `solicitar_json_qwen()` hace
  un segundo intento sin razonamiento si la primera respuesta queda vacía,
  incompleta o agota el plazo; nunca deja que una generación crezca sin límite.
- `normalizar_borrador()` rechaza ids que no existan, funde alias de una misma
  persona, conserva bloques confirmados, corrige fechas imposibles y evita que
  planes o compras rutinarias terminen en Datos. Un nombre o apodo exacto gana
  a cualquier id incoherente propuesto por el modelo; una enumeración explícita
  de asistentes limita quién recibe la quedada. `ajustar_identidades_por_grupo()`
  desempata los demás homónimos por conexiones con el resto del grupo; un empate
  queda dudoso y no se puede guardar.
- Cada bloque pendiente permite reasignar la persona mediante la ruta
  `resolver` o retirarlo mediante `eliminar`. Retirar no escribe en ninguna
  ficha; si era el último bloque pendiente, el audio pasa a `revisado`.
- `reconciliar_audios()` mantiene la relación uno-a-uno al arrancar: recupera
  como pendiente cualquier archivo sin fila, retira filas sin archivo y elimina
  metadatos duplicados antes de crear el índice único `audio_archivo_unico`.
  `audios_disponibles()` vuelve a comprobar el disco antes de enseñar nada.
  El archivo visible se pagina con `AUDIOS_POR_PAGINA = 5`.
- `POST /audio`: recibe el blob del móvil y lo guarda. `EXT_POR_MIME` decide la
  extensión según el contenedor que llegue (Opus en webm/ogg, o mp4/AAC en
  iPhone); el servidor no transcodifica. Primero escribe un temporal y después
  confirma archivo y fila como una unidad; ante un fallo compensa ambos lados.
- `GET /audios`: la lista independiente que se conserva por compatibilidad; el
  mismo archivo aparece al final de Notas. `GET /audio/{id}` sirve el
  archivo para volver a escucharlo. `POST /audio/{id}/borrar` aparta el archivo,
  borra la fila y restaura el original si falla la transacción.
- La cola offline vive en el móvil (IndexedDB, en `estatico/voz.js`): el
  servidor sólo recibe subidas.

## Anclas de redirección

Hay rutas que vuelven a un sitio concreto de la ficha. Si renombras un `id` en
`ficha.html`, hay que cambiarlas aquí:

- `/relacion/editar` y `/relacion/borrar` → `#relaciones`
- la paginación de quedadas → `#quedadas`
- cerrar, reabrir y borrar hilos → el `volver` que manda el formulario, que en
  la ficha es `#atencion`

## `main.py`

Al ejecutar `python main.py` desde el código, el propio arranque se relanza con
`venv/Scripts/python.exe` antes de importar la aplicación. Así Whisper no depende
de que la activación manual haya funcionado en `cmd` o PowerShell. El ejecutable
empaquetado no usa este relanzado.

`Relaciones.spec` construye un solo `Relaciones.exe` con las plantillas, los
recursos y las dependencias de Python. `construir.ps1` instala las dependencias
de construcción en `.paquete-deps/`, llama a PyInstaller y copia el resultado a
la raíz para que encuentre `datos.db` y `audios/`. Ollama y los modelos locales
no se incrustan en el ejecutable.

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
