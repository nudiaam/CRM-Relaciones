# `estatico/app.js` y `estatico/grafo.js`

Sin frameworks. Los dos son una función anónima que se ejecuta sola.

## `app.js` · ~1.150 líneas

Se carga **en el `<head>`** para aplicar el modo antes del primer pintado. Todo
lo demás espera a `DOMContentLoaded`.

| # | Qué hace | Línea |
| --- | --- | --- |
| — | `enfocar()`: no enfoca si el puntero es grueso | 22 |
| 1 | Modo día/noche antes de pintar | 35 |
| 1 bis | Límite de círculos visibles en la portada | 109 |
| 1 ter | Administración de círculos plegada y paginada | 130 |
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
  la posición del propio control para que el reajuste de altura no desplace lo
  que la persona acaba de pulsar; la edición nativa `<details>` de cada relación
  hace lo mismo tras su apertura.

## `grafo.js` · ~1.100 líneas

| Sección | Línea | Ancla |
| --- | --- | --- |
| Cargar `/api/grafo` | 65 | `── cargar` |
| Elegir colocación | 227 | `function colocar` |
| Agrupar por círculo | 381 | `function colocarPorCirculos` |
| Medidas del lienzo | 393 | `function medir` |
| Tinta, radios, escala y física | 405 | `function tinta` |
| Dibujo | 507 | `function pintar` |
| Interacción: buscar, seleccionar, cámara | 665 | `function xy` |
| Mandos de *Explorar la red* | 827 | `function prepararMandos` |
| Leyenda de círculos | 949 | `function montarCirculos` |
| Ratón y dedos | 1003 | `var toques = new Map` |
| Teclado | 1018 | `addEventListener('keydown'` |
| Ficha flotante | 1038 | `── la ficha flotante` |

### Gestos

Todo pasa por eventos `pointer*`, con los dedos activos en un `Map`:

- **Un dedo** gira · **dos dedos** desplazan siguiendo el punto medio y su
  separación hace zoom.
- **Ratón**: izquierdo gira, derecho o central desplazan, rueda hace zoom.
- `preventDefault()` en `pointerdown` **sólo con ratón**. Con el dedo lo
  cancelaba el traspaso de foco y Android reabría el teclado en cada toque.
- El lienzo lleva `touch-action: none`, que es lo que frena el desplazamiento.
- Un toque o clic entra por niveles: cuadrado → círculo centrado; punto → persona.
  Los nodos no cambian de disposición: la cámara interpola su posición y zoom.
  Pulsar el fondo o `Escape` retrocede persona → círculo → vista general.

### La ficha flotante

`protegerDelToque()` (línea 798) le pone `pointer-events: none` durante 350 ms
al abrirse. Sin eso, el `click` que el navegador dispara tras el toque caía
sobre *Abrir su ficha* y te sacaba de la red. **Es un apaño**: lo correcto sería
que ese `click` heredado no llegara a generarse.

### Composición y enfoque de la red

Hay una sola composición determinista. `estructura` contiene la jerarquía
Nuria → círculo activo → persona; no existe cuadrado *Yo*. `aristas` contiene
únicamente relaciones explícitas y sólo se dibuja si toca a la persona activa.
`prepararAnclasSinCirculo()` acerca a la gente sin círculo a sus relaciones con
personas visibles sin cambiar su clasificación. Quien no tiene ancla sólo entra
cuando *Sin círculo* está activo. `satelites` tiende una línea secundaria sólo a
los **puntos aislados de verdad**: una persona sin círculo cuya única atadura es
su relación **y** que está sola (su componente sin círculo tiene un único
miembro). Un grupo de gente sin círculo ya se lee como nube junta y no recibe la
maraña. La línea es discontinua (`setLineDash([2, 3])`) y más floja que
`estructura`; al señalar a esa persona pasa a la línea sólida de `aristas`.

Cada grupo (gente de un círculo, corro de Nuria, satélites) se reparte sobre una
**esfera** alrededor de su centro (`direccionEsfera` + `colocarEnEsfera`), no
sobre un plano: un disco se ve de canto desde algún ángulo y vuelve a parecer
plano, mientras que una esfera tiene volumen en los tres ejes y se lee de frente,
de lado y desde arriba. La profundidad de los propios cuadrados la fija el factor
Z de `ejesDeCirculos`.

La línea del cuadrado a Nuria (raíz → círculo) queda apenas visible cuando hay
una persona señalada (`tocaCirculo`), para no robar protagonismo a la persona ni
a sus relaciones; sólo la línea de la propia persona a su cuadrado se realza.

**Excepción única de Nuria**: cuando la persona activa es `central`, NO se
dibujan sus aristas (relaciones personales); su conexión visible es la de los
cuadrados de círculo, siempre. El resto de personas sí enseña sus relaciones.

`animarFisica()` mueve la red sin tocar las posiciones base (todo son desvíos
interpolados que vuelven a cero al soltar): al **señalar** con el ratón la gente
cercana se aparta del puntero —vivo también con una persona ya seleccionada,
vía `bajoPuntero`, para que entrar en una ficha no congele el vaivén— y al
**seleccionar** una persona o un círculo su gente vinculada se recoloca en un
anillo (`anilloActivo` + `radioAnillo`) alrededor del foco: los allegados de la
persona, o toda la gente del círculo alrededor de su cuadrado. Nuria no forma
anillo. Al soltar la selección, todo regresa.

`resaltada(n, a)` decide a quién realza señalar/seleccionar: persona + sus
relaciones, salvo Nuria (`central`), que no realza a ninguna persona y enciende
en cambio todos los cuadrados de círculo.

La **ficha resumida** se pliega como *Explorar la red*: `#grafo-ficha-plegar` es
el rótulo-botón con su signo +/−, alterna `#ficha[data-plegado]` y conserva el
estado entre selecciones; la × (`#grafo-cerrar`) sigue cerrándola del todo.

`animarFisica()` interpola el realce de la persona señalada y aparta suavemente
los puntos próximos para despejar el clic, sin muelles. Señalar un cuadrado fija
el contraste de todas sus personas sin cambiar el encuadre. Pulsar un cuadrado o
una persona actualiza objetivos de cámara; `actualizarCamara()` los alcanza poco
a poco, por lo que acercar, alejar y retroceder no recolocan la red ni dan saltos.

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
