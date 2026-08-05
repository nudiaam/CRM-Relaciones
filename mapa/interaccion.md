# `estatico/app.js` y `estatico/grafo.js`

Sin frameworks. Los dos son una función anónima que se ejecuta sola.

## `app.js` · ~1.150 líneas

Se carga **en el `<head>`** para aplicar el modo antes del primer pintado. Todo
lo demás espera a `DOMContentLoaded`.

| # | Qué hace | Línea |
| --- | --- | --- |
| — | `enfocar()`: no enfoca si el puntero es grueso | 22 |
| 1 | Modo día/noche antes de pintar | 35 |
| 3 | Tecla `N` para abrir Notas desde cualquier sitio | 64 |
| 4 | `Ctrl + Enter` guarda la nota | 77 |
| 5 | Filtro, contador y páginas del editor antiguo de quedadas | 86 |
| 6 | **Aviso propio antes de borrar** (`<dialog>`, no `confirm()`) | 164 |
| 7 | Foco al abrir un `details.anadir` | 171 |
| 8 | Selectores integrados de persona y canal | 180 |
| 9 | Varias relaciones en el alta | 374 |
| 9 bis | **Control de fecha**: atajos y calendario | 429 |
| 9 ter | **Notas**: proceso local, revisión, audio activo y captura manual | 663 |
| 9 quater | **Ficha: plegado y edición por bloque** | 870 |
| 9 quinquies | **Enlazar con varias**: atajos por círculo | 914 |
| 10 | Archivador sin recargar | busca `// 10.` |
| 11 | Conservar la posición vertical al recargar | busca `// 11.` |

**El bloque 2 no existe**: era el foco automático del texto de la antigua captura, que se
quitó porque abría el teclado solo en el móvil.

En Notas, tanto los bloques manuales como los que rellena Qwen nacen abiertos.
El selector emite `persona-limpiada` cuando se borra o modifica una elección;
la captura retira entonces sólo el formulario de esa persona, sin tocar su ficha.

### El aviso antes de borrar

El `<dialog class="confirmar">` vive en `base.html`, uno por página. El texto
sale de `data-confirmar` del formulario, igual que antes.

**No cuelgues nada del evento `close` del diálogo.** Hay navegadores donde no
se dispara —comprobado en el que usa esta app—, y ahí borrar se quedaría en
nada sin decir por qué. La decisión va en el **clic** de cada botón. Si el
navegador no tiene `showModal`, se cae al `confirm()` de siempre.

### Reglas que hay que respetar

- **Nada de foco automático.** Al montar o al abrir algo no se llama a
  `.focus()` directo: se llama a `enfocar()`, que no hace nada en táctil.
- **Ninguna acción puede mandar la página arriba.** De eso vive el bloque 11.
  La posición se guarda por ruta: prevalece sobre las anclas de respaldo al
  volver de un formulario y sobrevive también al recorrido de editar una
  quedada fuera de la ficha y regresar después. Si hay una posición pendiente,
  el ancla se retira en el `<head>` antes de que el navegador pueda saltar a ella.
- Los controles marcados con `data-conservar-posicion`, como las flechas del
  archivo de audios, guardan también el punto exacto aunque su enlace lleve un
  ancla de respaldo.
- El borrado de audio intercepta el segundo envío, ya confirmado, y retira la
  fila mediante `fetch`: no recarga ni cambia la posición de la página.
- El proceso del audio se refresca por fragmentos HTML mientras trabajan los
  modelos. Las confirmaciones individuales y *Validar todo* hacen lo mismo.
- Los fragmentos vuelven a registrar `data-confirmar`: así *Descartar bloque*
  usa el mismo diálogo que el resto de eliminaciones antes de retirar la
  propuesta y refrescar el audio activo.
- Al recibir un fragmento nuevo, `cargarProceso()` sincroniza también el estado
  guardado en la opción del selector. Si ya está `revisado`, la grabación deja
  de aparecer entre las pendientes sin cerrar su ficha activa de golpe.
- *Volver a analizar* cambia el botón y los dos estados visibles antes de
  enviar la petición; durante Whisper queda desactivado y anuncia el proceso
  mediante `aria-live`, sin dejar el borrador aparentemente inmóvil. El primer
  refresco espera 900 ms para que la respuesta al clic llegue a percibirse.
- El ocultado de la edición por bloque **lo enciende el JavaScript**: sin él la
  ficha se ve entera. Es a propósito. Abrir, cerrar o plegar un bloque reafirma
  la posición visible para que el reajuste de altura no desplace la página; la
  edición nativa `<details>` de cada relación hace lo mismo tras su apertura.

## `grafo.js` · ~900 líneas

| Sección | Línea | Ancla |
| --- | --- | --- |
| Cargar `/api/grafo` | 69 | `── cargar` |
| Colocación de nodos (una vez) | 136 | `function colocar` |
| Ejes por círculo (Fibonacci) | 138 | `function ejesDeCirculos` |
| Medidas del lienzo | 220 | `function medir` |
| Tinta, radios y escala | 231 | `function tinta` |
| Dibujo | 281 | `function pintar` |
| Interacción: buscar, seleccionar, cámara | 367 | `function xy` |
| Mandos de *Explorar la red* | 422 | `function prepararMandos` |
| Leyenda de círculos | 549 | `function montarCirculos` |
| Ratón y dedos | 605 | `var toques = new Map` |
| Teclado | ~745 | `addEventListener('keydown'` |
| Ficha flotante | 773 | `── la ficha flotante` |

### Gestos

Todo pasa por eventos `pointer*`, con los dedos activos en un `Map`:

- **Un dedo** gira · **dos dedos** desplazan siguiendo el punto medio y su
  separación hace zoom.
- **Ratón**: izquierdo gira, derecho o central desplazan, rueda hace zoom.
- `preventDefault()` en `pointerdown` **sólo con ratón**. Con el dedo lo
  cancelaba el traspaso de foco y Android reabría el teclado en cada toque.
- El lienzo lleva `touch-action: none`, que es lo que frena el desplazamiento.

### La ficha flotante

`protegerDelToque()` (línea 798) le pone `pointer-events: none` durante 350 ms
al abrirse. Sin eso, el `click` que el navegador dispara tras el toque caía
sobre *Abrir su ficha* y te sacaba de la red. **Es un apaño**: lo correcto sería
que ese `click` heredado no llegara a generarse.

### Agrupación por círculo

Cada círculo con gente dentro recibe **una dirección propia** en la esfera,
repartidas con una espiral de Fibonacci. Sus personas nacen dentro de un cono
alrededor de esa dirección, y durante la simulación una fuerza floja
(`COHESION`) las mantiene ahí en vez de dejar que la repulsión las esparza.

Quien no tiene círculo **no se agrupa**: reparto libre en el volumen exterior.

`COHESION` se eligió midiendo. Con las 27 personas reales:

| Valor | Distancia dentro / fuera | Distancia mínima |
| --- | --- | --- |
| 0 (como estaba) | 0,42 | 142 |
| **0,03 (actual)** | **0,30** | **105** |
| 0,08 | 0,25 | 88 |

Subirlo agrupa más pero junta los puntos. Si lo cambias, vuelve a medir.

## `voz.js` (captura por voz)

Cargado en todas las pantallas desde `base.html`, aparte de `app.js`. La misma
grabadora flota normalmente, pero `notas.html` la integra arriba en `/nota`.

- Sólo actúa en móvil: `puedeGrabar()` exige puntero grueso, `MediaRecorder`,
  `getUserMedia` e IndexedDB. Si no, el botón flotante `[data-voz]` sigue
  `hidden` y en escritorio no aparece.
- Graba con `MediaRecorder`, elige contenedor Opus si se puede (`elegirMime`),
  cronómetro por `setInterval`.
- **Cola offline en IndexedDB** (`relaciones-voz` › `pendientes`): al parar,
  guarda el blob *antes* de intentar subir, así el audio no se pierde con el
  servidor apagado. `subirTodo()` reintenta al abrir la app, al evento `online`
  y con el botón *Reintentar*; borra de la cola sólo lo que el servidor confirma.
- No toca el service worker ni cachea nada.
- El reproductor de `/audios` (`prepararReproductor`) usa un solo `Audio`
  compartido, sin `<audio controls>` nativo. Publica `MediaMetadata` para que la
  tarjeta de Android diga *Nota de voz*, muestre fecha y hora y use el logotipo
  claro u oscuro según `html[data-modo]`.

### Lo que no se debe hacer en la red

- No dibujarla pixelada ni a resolución reducida. Se probó y destrozaba las
  líneas finas.
- No aplastar el eje Y: X, Y y Z tienen la misma amplitud.
- No usar desplegables nativos en los mandos.
