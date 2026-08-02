# Relaciones — notas para futuras sesiones

App personal de escritorio para cultivar relaciones. Una sola persona la usa.
Corre en local, **nunca habla con internet**.

## Stack (no se discute)

- Python 3 en Windows. FastAPI + uvicorn, todo el backend en `app.py`.
- `main.py` arranca uvicorn en un hilo demonio (`0.0.0.0`, puerto 9765 fijo) y
  abre una ventana pywebview contra `http://127.0.0.1:9765`. El puerto no se
  busca ni se negocia: si está ocupado, la app avisa y no arranca, porque
  Tailscale apunta ahí. **No usar puertos por debajo del 9765**: el
  usuario trabaja con otros servicios ahí (8188 entre ellos).
- Nunca matar procesos filtrando por nombre o por línea de comandos (`main.py`
  coincide con servicios ajenos). Si hay que cerrar algo de esta app, localizarlo
  por el puerto concreto que escucha.
- **La dirección buena desde el móvil es `https://vespa.tail43936f.ts.net`,
  sin puerto.** Es la que tiene el icono instalado en la pantalla de inicio.
  `tailscale serve` escucha en el 443 y hace de proxy hacia
  `http://127.0.0.1:9765`. El nombre se compone del equipo en Tailscale
  (`vespa`, que salió del nombre de Windows, `Vespa`) más el dominio del tailnet
  (`tail43936f.ts.net`).
- La IP fija dentro de Tailscale es `100.69.126.95` y `http://…:9765` también
  responde, pero **no sirve para la app instalada**: sin HTTPS el navegador no
  la considera contexto seguro, así que no hay service worker ni instalación.
- **Ojo con la llave**: como el proxy de Tailscale conecta desde `127.0.0.1`,
  la app ve esas peticiones como locales y **entran sin llave**. La llave sólo
  protege el acceso directo por la IP de la wifi. Es aceptable porque el
  `serve` es «tailnet only» —sólo tus propios dispositivos—, pero conviene
  saberlo antes de activar Funnel, que lo abriría a internet.
- SQLite con el módulo `sqlite3` de la estándar, archivo `datos.db` en esta
  carpeta. Sin ORM. El esquema se crea al arrancar si no existe, y las bases de
  versiones anteriores se ponen al día en `poner_al_dia()`, que es idempotente.
- HTML/CSS/JS planos. Sin frameworks, sin build, sin npm, sin CDN, sin fuentes
  remotas: la única tipografía cargada es un `@font-face` local.
- Todo formulario es `POST` + redirección 303. Se puede usar JavaScript para
  mejorar la interacción; no es una limitación del proyecto. Las acciones que
  escriben datos conservan un formulario HTML normal. La única ruta que devuelve
  JSON es `GET /api/grafo`.

## Cómo se llaman las cosas

**Ninguna palabra técnica en pantalla.** En la base de datos hay tablas con
nombres viejos que en pantalla se dicen de otra manera:

| En la base | En pantalla |
| --- | --- |
| `circulo` | **círculo**: de dónde conozco a alguien |
| `hilo` con `tipo='pendiente'` | **Queda pendiente**: lo que tengo que hacer yo |
| `hilo` con `tipo='preguntar'` | **Preguntar por**: cosas de su vida |
| `hecho` | **Datos** |
| `nota` | **Quedadas** |
| `relacion` | **Relaciones** |
| cerrar un hilo | **Ya está** |
| escribir una nota | **Apuntar algo** |
| exportar | **Guardar una copia de todo** |
| última nota | **Hablamos hace** (y el valor no repite el «hace»: *tres días*) |

Los estados vacíos son frases cortas, no rótulos con un campo debajo: *«No le
debes nada ahora mismo»*, *«Nada en marcha ahora mismo»*, *«Aún no has apuntado
nada suyo»*, *«Todavía no habéis coincidido, o no lo has apuntado»*, *«No sabemos
aún a quién conoce»*.

Dos palabras **prohibidas**, porque nombraron conceptos que se eliminaron:

- **entorno**: fue un nombre efímero para el círculo. No debe reaparecer ni en
  el código ni en los comentarios.
- **tema** («de qué habláis»): duplicaba el trabajo del círculo. Se borraron las
  tablas `tema` y `nota_tema`, y sus datos quedaron en
  `temas-borrados-2026-07-25.json`.

## Modelo de datos

```
circulo(id, nombre, orden)
persona(id, nombre, apodo, circulo_id, color, cumple, notas_rapidas, foto, creada)
hecho(id, persona_id, texto, creado)
hilo(id, persona_id, texto, abierto_desde, cerrado_el, tipo)
nota(id, fecha, canal, texto, creada)
nota_persona(nota_id, persona_id)
relacion(persona_a, persona_b, etiqueta, etiqueta_inversa)
ajuste(clave, valor)                          -- sólo guarda la llave de red
```

Lo que no es evidente:

- **apodo** es «cómo le llamas». Si tiene contenido, es el nombre principal en
  listas, búsquedas, selecciones y red. El nombre completo sólo reaparece como
  subtítulo en la ficha completa y en la ficha rápida de Personas.
- Una **nota** puede mencionar a varias personas, por eso no cuelga de una
  persona: hay tabla intermedia. Es lo que teje la red sin trabajo extra.
- **hecho** es lo que no caduca: odia el cilantro, su hermana se llama Ana.
- **hilo** es lo que sí caduca, y su `tipo` lo parte en dos cosas distintas:
  `pendiente` es lo que yo tengo que hacer por esa persona; `preguntar` es algo
  de su vida por lo que interesarme la próxima vez. Antes esto era un booleano
  `mio`; la puesta al día lo convirtió (`mio=1` → `pendiente`).
- **circulo** es de dónde conozco a alguien (amigos, familia, trabajo, barrio,
  hípica, universidad). Uno solo por persona y **la única forma de clasificar
  gente que existe**. No lleva frecuencia asociada y el sistema no deduce nada
  de él. De fábrica, en una base nueva: Amigos, Familia, Trabajo y Barrio. Se
  pueden crear, renombrar, reordenar y borrar; al borrar uno, su gente se queda
  sin círculo pero **no se borra** (`ON DELETE SET NULL`).
- **canal** es un campo de texto libre de la quedada, no de la persona. La app
  sugiere los ya usados; se puede escribir cualquier otro.
- **relacion**: `etiqueta` describe qué es B respecto de A; `etiqueta_inversa`
  qué es A respecto de B ("madre de" / "hijo de"). Si la inversa está vacía se
  usa la misma en las dos fichas. Una sola fila por pareja.
- **foto** es opcional. Se recorta a 256×256, se convierte a PNG de 1 bit con
  tramado y se guarda como texto base64 dentro de `datos.db`; por eso ya queda
  incluida automáticamente en *Guardar una copia de todo*.
- Fechas **siempre ISO en la base de datos, siempre en lenguaje natural en
  pantalla**. Los cumpleaños sin año se guardan como `--MM-DD`. Los números van
  en palabras («tres días», «dos semanas»), no en cifras.

## Las cinco pantallas

1. `/` **La portada es la red**, siempre y a pantalla completa. Incluye búsqueda
   propia, cuadrados para señalar círculos, controles de cámara, pausa de
   movimiento y una ficha lateral. La red sigue siendo tridimensional y es el
   primer contacto con la app.
2. `/personas` es un archivador de tres partes: los círculos funcionan como
   carpetas, la columna central enseña hasta seis personas por página y la
   derecha ofrece una ficha rápida. Las flechas cambian de página sin apilar
   toda la lista. En móvil se recorre carpeta, persona y ficha por pasos. El
   alta permite indicar nombre, apodo, círculo y varias relaciones iniciales.
   La administración de círculos no vive aquí.
3. `/persona/{id}` ordena la ficha así: identidad con foto opcional y resumen,
   cosas en marcha, quedadas, datos y relaciones. No lleva índice interno. La
   edición personal queda al final y las **quedadas se paginan de diez en diez**.
   Cada quedada lleva a su pantalla de edición y cada relación se edita en la
   propia ficha, mostrando con nombres qué significa en ambos sentidos.
4. `/nota` es un recorrido lineal: qué ocurrió, cuándo y por dónde, con quién.
   Sigue accesible con la tecla `N` y `Ctrl + Enter`. `/nota/{id}` reutiliza el
   recorrido para cambiar una quedada, incluidas fecha, canal y personas.
5. `/ajustes` contiene modo día/noche, administración de círculos y copia de todo.

La navegación principal muestra siempre: *Red*, *Personas*, *Apuntar* y *Ajustes*.

## El estilo: interfaz pixelada 1-bit

El lenguaje visual toma referencias de interfaces gráficas tempranas, software
editorial y juegos de un bit. La estructura debe sentirse precisa, modular y
deliberada, nunca decorada por nostalgia sin función.

- Sólo papel `#f4efe1` y tinta `#14120f`; noche invierte ambos. El color guardado
  de una persona sigue siendo un dato editable, pero no rompe la interfaz 1-bit.
  **Única excepción**: `--alarma`, un rojo rebajado que aparece sólo al señalar
  con el ratón un botón que borra. En reposo esos botones siguen grises.
- Departure Mono se incluye localmente en `estatico/tipos/` bajo SIL OFL. Se usa
  a 11px para navegación, controles y rótulos. El texto largo usa serif a 16px.
- Títulos personales a 33px. Cuerpo a 16px. Interfaz a 11px.
- Filetes nítidos de 1px, esquinas rectas, selecciones por inversión de tinta y
  tramas binarias sin grises.
- Las secciones se separan con aire, filete y un pequeño cuadrado de tinta.
  Las bandas negras se reservan para acciones o estados seleccionados; no se
  repiten como cabecera de todos los paneles. **Única excepción**: en la ficha
  completa (`/persona/{id}`) cada bloque sí lleva su cabecera rellena, porque
  sin ella no se distinguía dónde acaba una sección y empieza su contenido.
  Fuera de esa pantalla la regla sigue entera.
- **Toda superficie rellena usa `var(--inverso-fondo)` y `var(--inverso-texto)`,
  nunca tinta y papel crudos.** En día dan lo mismo; en noche, la tinta cruda es
  crema y produce una caja brillante que no pega con nada. Las marcas pequeñas
  —el cuadrado, un filete, el punto de hoy— sí usan `var(--tinta)`, que ahí
  significa el color del trazo. La norma completa está junto a las variables en
  `estilo.css` y la comprueba `python mapa/comprobar.py`.
- **Todo `:hover` vive dentro de un `@media (hover: hover)`.** En una pantalla
  táctil el hover se queda pegado tras el toque y deja los desplegables en
  blanco. `:focus-visible` va fuera, que hace falta con teclado.
- *Queda pendiente* conserva su filete exterior, pero no lleva retícula ni otra
  trama decorativa detrás del encabezado o del contenido.
- Los controles tienen al menos 40px de alto y el foco de teclado usa un
  contorno visible de 2px.
- Se admiten retículas de una y dos columnas según la tarea, con texto largo
  limitado a 640px. En móvil todo vuelve a una columna.
- Las columnas de Personas, Apuntar y Ajustes se centran en la ventana, pero el
  texto permanece alineado a la izquierda.
- No crear desplazamiento interno si el contenido puede crecer con la página.
  Cuando una región acotada lo necesita, su barra es fina, monocroma, integrada
  y la región sigue siendo alcanzable con teclado.
- No usar sombras suaves, degradados tonales, esquinas redondeadas, opacidad para
  jerarquía ni animaciones ornamentales.

Detalles intencionados:

- `app.js` se carga en el `<head>` para aplicar el modo antes del primer pintado.
- Los formularios de añadir pueden vivir en `<details class="anadir">`; al
  abrirlos, JavaScript enfoca el primer campo.
- Las acciones pequeñas («Ya está», «Quitar», «Subir») permanecen visibles.
- El nombre habitual lleva su círculo debajo en listas y selecciones. Cuando
  hay apodo, la ficha muestra el nombre completo debajo como subtítulo.

## La red (`estatico/grafo.js`)

**Nítida y a resolución completa.** Se probó a dibujarla pixelada en un lienzo a
un tercio y con las transparencias en escalones: destrozaba las líneas finas y
se comía la profundidad. No repetirlo: el aspecto de píxel lo pone la tipografía
de los nombres, la red no necesita fingirlo.

- Un solo lienzo, escalado por `devicePixelRatio`, sin `imageSmoothingEnabled`
  ni `image-rendering: pixelated`.
- **Los puntos son pequeños y llenos.** El radio base lo manda cuántas veces has
  apuntado algo de esa persona (`2 + √notas·0.9`, tope 5) y la profundidad lo
  corrige acotada (`escala()` entre 0.6 y 1.6), así que en pantalla van de 1.2 a
  8px. La profundidad también aclara el punto de forma continua, nunca a saltos.
- **Las líneas, de 1px y al 7% de tinta**: casi al borde de no verse. Una red se
  lee bien cuando está medio vacía.
- **No hay anillos concéntricos.** Los círculos se muestran como cuadrados en
  *Explorar la red*. Al pasar o enfocar se iluminan temporalmente sus personas;
  al pulsar, la selección queda fijada. Nadie cambia de lugar.
- **Los nombres no se enseñan todos**: sólo los del 40% más cercano a la cámara
  (`CERCANIA_NOMBRES`), y al señalar a alguien sólo el suyo y los de sus
  conexiones. Siempre usan el nombre habitual si existe. Van en Departure a
  11px.
- **Al señalar, el contraste es bestia a propósito**: esa persona y sus
  conexiones a plena tinta, todo lo demás al 5%.
- La persona cuyo círculo se llama **Yo** es el origen estable de la red y se
  mantiene en `(0, 0, 0)`. Las personas con círculo ocupan el volumen directo,
  entre radios 220 y 430, y se enlazan con ella. Quienes no tienen círculo son
  indirectas: ocupan el volumen exterior, entre 500 y 700, y nunca reciben un
  enlace directo al centro.
- La colocación y las fuerzas usan X, Y y Z con la misma amplitud. No se aplasta
  el eje vertical ni se construye una cáscara plana.
- La cámara está lejos (`camZ` 1500, y 1900 en pantalla estrecha) para que los
  puntos cercanos no se proyecten enormes.
- El giro automático es de 0.00087 radianes por fotograma: una vuelta cada dos
  minutos. Calmado, pero vivo.
- La caja *Explorar la red* integra resultados de nombres y los cuadrados de
  círculo, además de acercar, alejar, centrar y pausar el giro. No usa
  desplegables nativos. El botón izquierdo arrastrado gira; el derecho o el
  central desplazan dentro de un límite; la rueda controla el zoom. Las flechas
  desplazan, Mayúsculas más flechas giran y *Centrar* restablece la cámara.
- La ficha flotante lleva foto si existe, nombre, círculo, hablamos hace, queda
  pendiente, preguntar por, vistas previas compactas de quedadas y relaciones,
  y botones para apuntar o abrir la ficha. En escritorio no crea una barra de
  desplazamiento exterior.
- En la ficha completa, el selector para enlazar otra persona abre sus resultados
  como una lista flotante bajo el buscador; la lista no cambia la altura de la
  caja de relación.

## Lo que NO se debe construir

Si parece que algo de esto mejoraría la app: no se hace, se dice.

- Ninguna puntuación, porcentaje, racha, "salud de la relación" ni métrica
  numérica al lado del nombre de nadie.
- Ningún recordatorio, notificación, aviso ni frecuencia de contacto.
- Ningún dashboard, gráfica ni estadística.
- Ninguna importación de contactos del móvil.
- Ningún usuario, login, contraseña ni permiso. La llave de red **no** es un
  sistema de usuarios: no hay tabla de usuarios, ni registro, ni contraseñas.
- Ninguna llamada a internet, API, CDN ni telemetría.
- Ningún campo de "cómo nos conocimos", deudas de dinero, ni notas marcadas como
  positivas o negativas.
- Ningún diario personal: esto registra a otras personas, no al usuario.
- Nada de "persona en pausa" (pedido y descartado explícitamente).
- Ninguna otra forma de clasificar gente aparte del círculo.

## El mapa del código

Antes de buscar nada a mano, mira `mapa/`. Dice a qué archivo, sección y línea
ir, con anclas de texto que no envejecen: `backend.md`, `pantallas.md`,
`estilos.md`, `interaccion.md` y `decisiones.md`.

`python mapa/comprobar.py` comprueba que el mapa siga siendo cierto, que los
`id` que usa `app.py` para redirigir existan, la norma de los dos modos, que
todos los botones que borran lleven `accion-eliminar` y que ningún `:hover` se
escape del `@media`. **Si se toca código, se actualiza el mapa en el mismo
cambio**, igual que el registro de aquí abajo.

## Cómo trabajar aquí

Un cambio cada vez. No reescribir archivos enteros para tocar una función.
Antes de añadir cualquier cosa que no esté en el encargo, preguntar. Avisar
siempre de los datos que se van a perder antes de tocar la base.

Una acción dentro de la misma pantalla **nunca puede mandar la página arriba**.
Los formularios y enlaces que recargan la ruta conservan la posición; cuando el
destino es una parte concreta, se usa un ancla explícita. Esta regla se aplica a
toda la app, no sólo a Personas.

Después de cualquier cambio, añadir una entrada fechada al registro de este
archivo. `CLAUDE.md` es la memoria de cambios del proyecto.

`python ejemplo.py` mete 20 personas de mentira en seis círculos para ver la red
con algo dentro, y `python ejemplo.py --quitar` las saca. Si ya están, no hace
nada: primero hay que quitarlas.

## Registro de cambios

### 2026-07-27 — Controles de ratón de la red

- Arrastrar con el botón izquierdo gira la red. Arrastrar con el derecho o el
  central desplaza la vista y la rueda controla el zoom.
- El menú contextual y el desplazamiento automático del botón central se
  cancelan únicamente dentro del lienzo para no interferir con esos controles.
- Un toque sigue desplazando y tocar sin arrastrar sigue seleccionando.

### 2026-07-27 — Edición de quedadas y relaciones

- Cada quedada tiene una acción *Editar* que abre el formulario completo con su
  contenido y sus personas ya marcadas.
- Cada relación tiene su propio bloque *Editar*. Los dos campos dicen
  explícitamente «qué es A para B» y «qué es B para A», usando los nombres
  reales para que la dirección nunca quede implícita.
- El selector de personas para una relación se abre al buscar y se cierra al
  elegir. El nombre seleccionado pasa también a los dos rótulos del formulario.
- `Relaciones.exe` excluye NumPy, que Pillow sólo ofrecía como integración
  opcional y la app no usa. El paquete baja de 39,7 MB a 28,9 MB; se comprobó
  aparte que el recorte y la conversión 1-bit de las fotos siguen funcionando.
- Las pruebas de guardado se hicieron sobre una copia temporal de `datos.db`;
  no se modificaron los datos reales.

### 2026-07-27 — Centro ocupado y desplazamiento de la red

- Se quitó la retícula decorativa de *Queda pendiente*; el recuadro conserva su
  jerarquía mediante el filete y el espacio.
- La red dejó de distribuir a todas las personas sobre una cáscara: ahora ocupa
  el centro y reduce su radio exterior para evitar acumular nodos en los lados.
- El arrastre normal desplaza la vista dentro de límites proporcionados a la
  ventana. Mayúsculas más arrastre conserva la rotación, las flechas ofrecen
  ambas operaciones y *Centrar* restablece la cámara completa.

### 2026-07-27 — Red sin anillos, jerarquía amable y fotos

- Se eliminaron los anillos concéntricos de la portada. Los círculos pasaron a
  una leyenda de cuadrados con previsualización al pasar o enfocar y selección
  fija al pulsar, sin recolocar personas.
- La búsqueda de la red y el selector de relaciones se sustituyeron por
  componentes integrados con resultados propios.
- Personas, Apuntar y Ajustes centran su columna. La jerarquía global ahora usa
  espacio, filetes y encabezados claros en vez de repetir bandas negras.
- La ficha dejó de tener índice; los controles de añadir están a la derecha y
  fuera del contenido de sus secciones.
- Apuntar usa una «×» propia y su listado deja crecer la página en vez de crear
  una barra interior. Las barras necesarias son finas, monocromas y accesibles.
- Se añadió `persona.foto` mediante una migración idempotente. Las imágenes se
  recortan, tramitan a 1 bit, se guardan dentro de `datos.db`, aparecen en la
  ficha y la red, y viajan en la copia completa. No se eliminó ningún dato.

### 2026-07-27 — Arranque con doble clic

- Se preparó una versión autónoma `Relaciones.exe` que abre la ventana sin
  PowerShell ni una instalación local de Python.
- En la versión ejecutable, los recursos se leen del paquete y `datos.db` se
  mantiene junto al `.exe`; mover ambos archivos conserva toda la información.
- Los fallos de arranque del ejecutable se muestran en una ventana y dejan el
  detalle en `relaciones-error.txt`. No hubo cambios ni pérdida de datos.

### 2026-07-27 — Reorganización UX e interfaz 1-bit

- Se sustituyó la navegación dispersa por cuatro destinos persistentes: Red,
  Personas, Apuntar y Ajustes.
- Personas se separó en cuatro vistas: todas, queda pendiente, preguntar por y
  hace tiempo. La búsqueda avanzada se mantiene en la vista general.
- La administración de círculos pasó de Personas a Ajustes.
- La ficha personal se reordenó: resumen, cosas en marcha, quedadas, datos,
  relaciones y edición personal.
- Apuntar algo pasó a un recorrido lineal de tres partes e incorporó filtro y
  contador de personas mediante JavaScript.
- La red añadió búsqueda, filtro por círculo, zoom, centrado, pausa, controles de
  teclado, estado visible y una ficha lateral reorganizada.
- Se creó un sistema visual pixelado 1-bit adaptable a móvil, con controles
  amplios, foco visible, barras de panel invertidas y tramas binarias.
- Se incorporó Departure Mono como archivo local bajo SIL OFL y se versionaron
  los recursos estáticos para evitar estilos antiguos en caché.
- Se eliminó la restricción documental contra JavaScript. No hubo cambios en el
  modelo de datos ni pérdida de información.
### 2026-07-28 — Posición estable al guardar

- Los formularios que recargan y vuelven exactamente a la misma pantalla
  conservan ahora la posición vertical. Añadir o cambiar círculos, y las demás
  acciones equivalentes, ya no mandan la vista al principio de la página.
- La posición no se restaura si la acción abre otra pantalla o lleva a un ancla
  concreta, de modo que la navegación intencionada mantiene su destino.
- Las casillas invisibles para elegir personas quedan físicamente dentro de su
  tarjeta; enfocarlas ya no puede hacer que ciertos motores desplacen la página.

### 2026-07-28 — El círculo `Yo` como centro y relaciones compactas

- La persona incluida en el círculo `Yo` pasa a ser el centro fijo de la red.
  Las personas con círculo se conectan directamente con ella y las que no
  tienen círculo quedan como contactos indirectos, sin enlace al centro.
- La distribución deja de comprimir el eje Y: los nodos y las fuerzas ocupan de
  verdad los ejes X, Y y Z.
- El buscador para añadir relaciones usa una lista flotante que se cierra al
  elegir, al pulsar Escape o al hacer clic fuera, sin alargar el formulario.
- No se cambió el esquema ni se eliminó ningún dato. La propuesta de carpetas
  para Personas queda pendiente de aprobación y no se implementó.

### 2026-07-28 — Archivador de personas y nombres habituales

- Antes del cambio se guardó una copia completa y restaurable en
  `copias/Relaciones-antes-archivador-2026-07-28.zip`, con código, ejecutable y
  `datos.db`.
- «Cómo le llamas» pasa a ser el nombre visible en listas, búsquedas,
  selecciones y red. En la ficha completa y en la ficha rápida, el nombre
  completo queda debajo como subtítulo.
- El alta de una persona permite escribir desde el principio tanto su nombre
  completo como la manera habitual de llamarla.
- *Todas* en Personas se convirtió en un archivador: los círculos son carpetas,
  la columna central contiene las personas y la derecha ofrece una ficha rápida
  con acceso a Apuntar y a la ficha completa.
- Queda pendiente, Preguntar por, Hace tiempo, buscar en lo apuntado, ordenar,
  añadir y editar conservan su funcionamiento. En móvil, elegir una persona abre
  sólo su ficha rápida y ofrece volver a la lista.
- No se cambió el esquema ni se transformó o eliminó información existente.

### 2026-07-28 — Archivador paginado y alta completa

- Se retiraron las pestañas y la búsqueda avanzada que precedían al archivador:
  ese espacio contiene ahora un único bloque de *Añadir persona*, con nombre,
  manera habitual de llamarla, círculo y tantas relaciones iniciales como hagan
  falta.
- El alta conserva formularios HTML normales y permite quitar una fila de
  relación antes de guardar. Al terminar abre la ficha recién creada, donde ya
  aparecen su círculo y sus relaciones en ambos sentidos.
- Cada carpeta enseña como máximo seis personas. Dos flechas permiten cambiar
  de página sin crear una columna interminable, manteniendo carpeta, búsqueda y
  ficha rápida.
- La ficha completa lleva *Volver al archivador*. En móvil, la ficha rápida
  conserva además su regreso propio a la lista.
- Cabecera, alta y archivador comparten exactamente el mismo ancho y se adaptan
  a una columna sin desbordamiento horizontal en pantallas estrechas.
- La posición vertical se conserva para cualquier formulario o enlace que
  recargue la misma ruta; las carpetas, páginas y fichas rápidas usan el ancla
  del archivador. La prohibición de saltar arriba queda registrada como regla
  general para futuros cambios.
- Las altas y ediciones se probaron sobre una copia temporal de `datos.db`. No
  se cambió el esquema ni se modificaron los datos reales.
- Se reconstruyó `Relaciones.exe` (28,9 MB), se comprobó su arranque autónomo y
  sus rutas principales, y se volvió a abrir la app actualizada en el puerto
  9765 con las 11 personas de la base real.

### 2026-07-28 — Fichas de un vistazo, selectores y tarjetas en la red

- Las carpetas enseñan cinco personas por página. La lista ocupa toda la altura
  útil de la tarjeta y su paginación permanece fija al pie incluso cuando sólo
  hay una página.
- La ficha rápida del archivador se rediseñó como una tarjeta modular: foto e
  identidad comparten altura y quedan separados de hablamos hace, cosas en
  marcha, última quedada, datos, relaciones y acciones. No crea desplazamiento
  interno.
- Las relaciones iniciales de una persona usan un buscador integrado en vez del
  desplegable nativo. Las filas añadidas heredan el buscador y generan sus
  referencias accesibles sin duplicar identificadores.
- Apuntar sustituyó las sugerencias nativas del canal por una lista propia que
  sigue admitiendo texto libre. La selección de personas muestra nueve por
  página en escritorio y seis en móvil, con las flechas siempre debajo; el pie
  dejó de tapar la última fila.
- En la red, cada nombre visible forma una tarjeta con foto a la izquierda —o
  un cuadrado de tinta— y nombre a la derecha. Al seleccionar, la tarjeta crece
  y se invierte, y el resto de la red baja de contraste sin cambiar de lugar.
- La ficha de la portada se convirtió en una tarjeta de identificación compacta
  con cosas en marcha, **Datos**, última quedada y relaciones. En escritorio
  cabe sin barra exterior; en móvil usa la barra integrada sólo si hace falta.
- Se comprobaron búsquedas, clonación de relaciones, páginas, selección y
  adaptación móvil sobre una copia temporal de `datos.db`. No se cambió el
  esquema ni se modificaron los datos reales.
- Se reconstruyó y verificó `Relaciones.exe` (29,4 MB) con los nuevos recursos;
  responde correctamente, conserva las 12 personas de la base actual y sigue
  excluyendo NumPy.

### 2026-07-28 — Ritmo visual, archivador inmóvil y relaciones en ambos sentidos

- Los nombres de la red vuelven a ser texto suelto junto a puntos pequeños: se
  retiraron de la red las fotos, los fondos rectangulares y el crecimiento de
  esas tarjetas. La ficha flotante conserva su foto opcional y sus datos.
- Se añadió un gris secundario, también adaptado al modo noche, sólo para
  metadatos: círculo, recuentos, fechas, nombre completo y papel de una
  relación. Los títulos, el cuerpo, los controles y los filetes siguen usando
  papel y tinta.
- Se compactó la distancia entre el nombre de una carpeta y su recuento. Las
  relaciones de las fichas rápida, completa y de la portada comparten ahora la
  misma familia tipográfica; su papel queda en cursiva y en el gris secundario.
- La ficha rápida perdió el filete vertical innecesario entre la inicial o foto
  y el nombre. También se unificaron los márgenes de cabecera, módulos y
  acciones de la ficha de la portada.
- Carpetas, personas, flechas y búsqueda del archivador se actualizan sin
  recargar la página, sin conservar el `#archivo` en el historial dinámico y
  restaurando la posición exacta. Se comprobó con clics reales que la ventana
  permanece inmóvil al cambiar de carpeta, persona y página.
- La paginación de *Con quién* conserva su filete superior también en la última
  página.
- Se corrigió un único dato existente: una relación de pareja tenía la misma
  etiqueta en los dos sentidos y pasó a decir lo que corresponde en cada ficha.
  Se comprobó el sentido en las fichas rápidas, completas y en la portada; no
  se cambió el esquema ni otro dato.
- Se revisaron alineación y desbordamiento en escritorio y móvil. Se
  reconstruyó `Relaciones.exe` (29,4 MB) y se comprobó de forma autónoma en el
  puerto 9765: salud, recursos, 12 personas y la relación inversa correcta.

### 2026-07-28 — Identidad limpia y jerarquía en las fichas compactas

- Se retiraron los rótulos visibles *Ficha rápida* del archivador y *Persona
  seleccionada* de la portada: la foto, el nombre y el círculo ya identifican
  con claridad el bloque.
- En la ficha completa, `PERSONA / 0000` se movió encima de la identidad. Foto,
  nombre y círculo quedan debajo en una misma línea visual y centrados entre sí,
  también en móvil.
- Las fichas compactas distinguen mejor sus capas: rótulos a 10px con espaciado
  amplio y un cuadrado de tinta, recuentos en gris y contenido serif a 15–17px
  con más separación vertical.
- Las relaciones del archivador, la portada y la ficha completa usan de nuevo
  Departure Mono tanto para el nombre como para el papel. El papel baja a 10px
  y conserva el gris secundario, sin cursiva.
- Se comprobaron la carga de todas las plantillas, las versiones de los
  recursos, la ausencia de los dos rótulos y la estructura de identidad en una
  copia aislada. `Relaciones.exe` (29,4 MB) se reconstruyó y respondió
  correctamente en el puerto 9765 con estos recursos.

### 2026-07-28 — Borrados seguros y modo noche descansado

- Los títulos de los módulos compactos suben a 11px y mantienen tinta plena;
  los recuentos y otros metadatos siguen siendo los únicos textos en gris.
  *Última quedada* deja así de confundirse con información secundaria.
- Cada elemento de *En marcha* ofrece ahora **Ya está** y **Eliminar**. El
  borrado pide confirmación y vuelve a `#atencion`, sin mandar la ficha arriba.
- El control **Editar** de una relación tiene fondo propio y permanece visible
  cuando se señala la fila. Su editor incluye **Eliminar relación**, con una
  confirmación que explica que desaparece de las dos fichas y vuelve a
  `#relaciones`.
- El modo noche abandona la inversión negra y crema pura: usa carbón cálido,
  crema apagada, una capa intermedia para tarjetas, selecciones gris oscuro y
  filetes suavizados. Texto, información secundaria, selección y límites
  conservan contrastes de 10,8:1, 6,1:1, 9,3:1 y 3:1 respectivamente.
- Se renderizaron todas las plantillas y se probaron ambos borrados sobre una
  copia de `datos.db`; las redirecciones conservaron sus anclas y la base real
  quedó intacta. El ejecutable autónomo se reconstruyó y respondió con las
  pantallas, acciones y estilos nuevos.

### 2026-07-28 — Corrección del rótulo «Última quedada»

- Se corrigió la colisión que hacía que una cabecera con un solo elemento
  coincidiera también con la regla gris de los recuentos. Ahora esa regla sólo
  actúa cuando existe un segundo elemento real y *Última quedada* conserva
  tinta plena, igual que *Datos* y *Relaciones*.
- Se cambió la versión del CSS para impedir que la ventana reutilice el estilo
  anterior desde la caché.
- En la portada nocturna, buscador, lista de círculos y controles de cámara
  comparten ahora la misma capa de carbón. Se retiraron los rectángulos más
  negros que cortaban visualmente el panel; ayuda, estado y ficha flotante usan
  el mismo sistema, y los estados señalados suben sólo un paso de luminosidad.
- La revisión se extendió a toda la aplicación: barra, paneles, formularios,
  listas, fichas, selector de personas, pie de Apuntar y Ajustes comparten una
  única capa nocturna. Las cabeceras informativas ya no forman bandas grises;
  sólo las acciones y selecciones cambian de fondo.
- Los controles nativos respetan también el modo elegido; iconos del calendario,
  flechas y menús dejan de conservar piezas negras propias del modo claro.
- **Eliminar** pasa a ser una acción secundaria gris, incluida **Eliminar
  relación**. Se distingue de **Ya está** y de las acciones principales sin
  añadir un color de alarma ajeno a la estética 1-bit.
- Se recorrieron en un navegador real Red, Personas, ficha completa, Apuntar y
  Ajustes, además de Personas en móvil. En noche, la auditoría de todos los
  elementos visibles sólo encontró la capa común `#2b2c27` y la selección
  `#3a3b35`; no quedó desplazamiento horizontal en 390px. En día se comprobó
  que *Última quedada* devuelve tinta `#14120f` a 11px.
- `Relaciones.exe` se reconstruyó (28,9 MB), se probó de forma autónoma y
  sustituyó a la versión abierta. La app se reinició en el puerto 9765 con sus
  12 personas y seis círculos intactos.

### 2026-07-28 — Acciones alineadas al editar relaciones

- **Eliminar relación** y **Guardar cambios** comparten ahora una sola fila:
  eliminar queda a la izquierda con el gris secundario del resto de borrados y
  guardar a la derecha como acción principal. Ambos tienen también la misma
  altura visual de 40 px.
- Los formularios siguen siendo independientes. El botón derecho envía el
  formulario de edición mediante su identificador y el izquierdo conserva la
  confirmación antes de borrar en las dos fichas.
- Se comprobó en navegador a ancho de escritorio y a 390 px: los dos botones
  empiezan en la misma coordenada vertical, no desbordan y **Guardar cambios**
  termina en el borde derecho. `Relaciones.exe` se reconstruyó, se verificó
  aparte y sustituyó a la versión abierta; la app volvió a arrancar en el
  puerto 9765 con sus 12 personas, seis círculos y `datos.db` sin cambios.

### 2026-07-28 — Fondo continuo en las fichas durante la noche

- La regla nocturna general estaba acumulando el gris de capa en los apartados,
  las tarjetas de *En marcha* y sus filas. En las fichas individuales esos
  contenedores recuperan ahora el mismo carbón del fondo general.
- El gris auxiliar se reserva para controles y superficies interactivas. Las
  secciones vuelven a separarse mediante espacio y filetes, sin rectángulos
  tonales detrás de *En marcha*, *Quedadas*, *Datos* o *Relaciones*.
- La ficha completa se revisó en navegador tanto en escritorio como a 390 px:
  sus cuatro apartados y las dos tarjetas usan exactamente el mismo fondo que
  la página, mientras campos y controles conservan la capa diferenciada; no hay
  desbordamiento horizontal. `Relaciones.exe` se reconstruyó, se probó aparte
  y se volvió a abrir en el puerto 9765 con 12 personas, seis círculos y
  `datos.db` sin cambios.

### 2026-07-28 — Noche sin capa intermedia

- Desapareció el gris de capa del modo noche: paneles, apartados, campos,
  botones, listas de círculos, tarjetas y los recuadros de la red comparten
  ahora exactamente el mismo fondo que la página, igual que ocurre de día. Las
  cajas se distinguen sólo por su filete y por el aire, sin rectángulos más
  claros alrededor.
- La variable `--capa` se quedó con un único valor, el del papel, así que la
  regla que ya devolvía el fondo a la ficha individual se volvió innecesaria y
  se retiró.
- Siguen invirtiéndose únicamente las acciones y lo señalado: el cuadrado de
  tinta, el destino actual de la navegación, los botones sólidos y los
  desplegables abiertos.
- Se comprobó en un navegador real, sobre una instancia de prueba en el puerto
  9770 levantada desde el código y cerrada después por su puerto: en Red,
  Personas, ficha, Apuntar y Ajustes ningún elemento nocturno conserva un fondo
  propio salvo esas acciones. No se tocó la base de datos ni el esquema.

### 2026-07-30 — Puerto fijo para llegar desde el móvil

- El puerto deja de buscarse: es siempre el 9765. `PUERTO_BASE` e
  `INTENTOS_PUERTO` se sustituyeron por una sola constante `PUERTO`, y
  `puerto_libre()` pasó a llamarse `comprobar_puerto()`, que ya no recorre un
  rango sino que comprueba ese puerto y nada más.
- Si el 9765 está ocupado, la app dice cuál es y que no usa ningún otro, y no
  arranca. Antes saltaba al siguiente libre y la dirección guardada en el móvil
  dejaba de servir sin avisar. En el ejecutable el aviso sale en ventana, porque
  `mostrar_error` recoge también `SystemExit`.
- Desapareció el aviso «el puerto estaba ocupado, uso el N», que ya no puede
  ocurrir.
- El motivo es Tailscale: la dirección del móvil apunta a un puerto concreto y
  no puede cambiar de un arranque a otro.
- Se revisó de paso que uvicorn ya escuchaba en `0.0.0.0` desde antes, y que la
  llave de red ya se generaba una sola vez y se guardaba en `ajuste`. Ninguna de
  las dos cosas necesitaba cambio; la llave sigue siendo la misma en todos los
  arranques.
- No se tocó la base de datos ni el esquema.

### 2026-07-30 — El móvil: teclado, gestos y fotos

- **El teclado ya no aparece solo.** Se retiró el `autofocus` del texto de
  Apuntar y el `.focus()` que lo reforzaba, y el foco al abrir un
  `details.anadir` o al clonar una fila de relación pasa por `enfocar()`, que
  no hace nada cuando el puntero es grueso. Con ratón todo sigue igual. El
  `autofocus` de la pantalla de la llave se conserva a propósito: esa pantalla
  existe sólo para escribir ahí.
- **El buscador de la red dejó de secuestrar el foco.** La causa era un
  `e.preventDefault()` incondicional en el `pointerdown` del lienzo: cancelar
  ese evento cancela también el traspaso de foco del navegador, así que el
  campo de búsqueda no lo perdía nunca y Android reabría el teclado en cada
  toque. Ahora sólo se cancela con ratón, donde evita seleccionar texto al
  arrastrar; el toque suelta el foco explícitamente. El arrastre no se
  desmadra porque el lienzo ya llevaba `touch-action: none`.
- **Gestos táctiles.** Un dedo gira, dos desplazan siguiendo el punto medio y
  su separación hace zoom. Antes un dedo desplazaba y dos hacían zoom y
  desplazaban a la vez, porque el pellizco iba por `touchstart`/`touchmove` y
  el arrastre por los eventos de puntero. Todo pasa ahora por `pointer*`, con
  los dedos activos en un mapa. El ratón no cambia.
- **La ficha de la red se ancla debajo de la barra** en pantalla estrecha, en
  vez de subir desde el pie, y puede tapar *Explorar la red*.
- **Los filetes de esa ficha llegan a los dos bordes.** Se cortaban 16px antes
  del derecho porque una regla posterior le ponía `width: calc(100vw - 16px)`
  mientras otra ya la fijaba con `left: 0; right: 0`.
- **Explorar la red se pliega.** Su barra de título es ahora un botón con
  `aria-expanded`; arranca abierto en escritorio y cerrado por debajo de 640px.
  El estado por defecto lo decide el CSS, así que no hay parpadeo al cargar.
- **Las fotos pasan a escala de grises.** Se retiró el paso a 1 bit con tramado
  Floyd–Steinberg: a 256px el umbral destrozaba las caras y estas fotos son
  para reconocer a alguien de un vistazo. Se sigue recortando en cuadrado a
  256×256 y guardando dentro de `datos.db`.
- **Se aplica la orientación EXIF** con `ImageOps.exif_transpose`. Los retratos
  del móvil entraban tumbados.
- **Un fallo al guardar una foto se dice en pantalla.** Antes el `except` se lo
  tragaba y la ficha volvía como si todo hubiera ido bien. Ahora la redirección
  lleva `?foto=` y la ficha abre el bloque con el motivo: pesa más de 8 MB, no
  se puede leer la imagen, o falta Pillow.
- Se subió la versión de `estilo.css`, `app.js` y `grafo.js` a `20260730a` para
  que el móvil no reutilice los archivos de la caché.
- No se tocó la base de datos ni el esquema. Ninguna foto existente se
  reconvierte: las que ya estaban siguen guardadas en 1 bit hasta que se
  vuelvan a subir.

### 2026-07-31 — Controles propios, la ficha rehecha y el mapa del código

**Se acabaron los controles nativos.**

- El **círculo** deja de ser un `<select>` en el alta y en la ficha: ahora es
  una lista de radios visible, con su cuadrado de tinta y filas de 40px. Sin
  JavaScript, sin desplegable y sin teclado posible.
- La **fecha** de una quedada deja de ser `<input type="date">`: seis atajos
  (*hoy*, *ayer* y cuatro días más), la fecha elegida en palabras y un
  calendario propio plegado detrás de *Otro día*. Todo son botones, así que
  desplegarlo no abre el teclado. El nativo se conserva en un `<noscript>`, y
  el campo que viaja lo crea el JavaScript para que nunca se envíen dos.
- Repaso completo: el único control del sistema que queda es el diálogo de
  archivos al subir una foto, que no se puede sustituir.

**La ficha completa se rehízo como continuación de la comprimida de la red.**

- Mismo marco, misma cabecera con foto e identidad, misma etiqueta con filete y
  contador. Lo que **no** se hereda es la retícula: aquí se lee todo entero, en
  una columna en móvil, y no se trunca nunca.
- Desapareció el triple encuadre de *En marcha*: ya no hay título, ni cajas
  `tarjeta-accion`, ni rótulos dentro de rótulos. Quedan dos bloques hermanos.
- **En reposo no hay un solo botón dentro del contenido.** Cada bloque entra en
  edición por su cuenta y sólo entonces enseña añadir, cerrar, quitar o editar.
  Abrir uno no abre los demás. La navegación —páginas, enlaces a otra persona,
  *Sigue*— no es edición y se ve siempre.
- Cada bloque se pliega, con su etiqueta y su contador visibles plegado.
- Las acciones se apoyan en la **línea base** de su frase, no a media altura.
- `PERSONA / 0009` se conserva a petición expresa. *Apuntar algo* baja a botón
  normal: lo más grande de la pantalla vuelve a ser el nombre.
- La edición de la persona y la foto son ahora el modo edición de la cabecera.
  *Quitar a X* sigue abajo del todo, fuera de ella.
- La **zona peligrosa** se rediseñó: la trama binaria deja de ser fondo —
  recortaba el texto con parches de anchos distintos— y pasa a ser dos bandas
  de altura fija arriba y abajo, como un precinto, dentro de una caja con
  filete y con el contenido en papel limpio.

**Los dos modos, con norma escrita.**

- La causa de los desajustes era pintar superficies rellenas con `var(--tinta)`
  cruda: en noche eso es crema y salía una caja brillante. La norma está ahora
  en el propio `estilo.css` y la comprueba `mapa/comprobar.py`.
- **Todos los `:hover` se envolvieron en `@media (hover: hover)`**, 39 reglas:
  22 hubo que partirlas porque mezclaban selectores con y sin hover. Se hizo
  con PostCSS instalado **fuera del proyecto**, que aquí no entra npm, y se
  verificó que los 817 selectores sin hover siguen existiendo en el mismo
  orden, que ningún `@media` original perdió reglas y que no quedó ningún
  `(hover: hover)` anidado dentro de otro igual.
- El rojo de borrar se separó en `--alarma` y `--alarma-texto`: el contraste
  sube de 5,1 a 6,8 de día y de 5,6 a 9,1 de noche. Lo llevan ahora **todos**
  los botones que borran, no sólo algunos.
- *Explorar la red* recupera su relleno de tinta y pierde el cuadrado de la
  izquierda. Necesitó una regla propia para noche porque es un `<button>` y le
  llegaba el fondo de los botones del panel.

**Enlazar con varias.** Ruta nueva `POST /persona/{id}/relaciones`: se marcan
varias personas, se escribe un solo par de etiquetas y quedan todas enlazadas
con esa persona —no entre ellas—, con atajos que marcan un círculo entero. La
lógica de enlazar se extrajo a `enlazar()`, compartida con la ruta de una sola,
así que se conserva el caso de la relación que ya existe al revés.

**La red agrupa por círculo.** Cada círculo recibe una dirección propia en la
esfera repartida con una espiral de Fibonacci, y una fuerza floja mantiene ahí a
su gente. Quien no tiene círculo no se agrupa. El valor se eligió midiendo con
las 27 personas reales: la proporción de distancia dentro/fuera del círculo baja
de 0,42 a 0,30 y el largo medio de una línea de 250 a 227, sin apelmazar los
puntos. **No se tocó qué se conecta con quién**: los radios al centro siguen
igual, a la espera de decidir cómo se marca «conectado a mí».

**Arreglos de móvil.** La × del buscador se estira de arriba abajo del campo y
su filete llega a las esquinas. El *Editar* de cada relación se ancla a su fila
y ya no se va al centro del formulario al abrirse. La ficha de la red nace sin
aceptar pulsaciones durante 350 ms, para comerse el clic fantasma que abría la
ficha completa sin querer; es un apaño, lo correcto sería que ese clic no
llegara a generarse.

**El mapa del código.** Carpeta `mapa/` con cinco documentos y un comprobador en
Python de la estándar. Existe para no releer 5.000 líneas cada vez.

**Limpieza.** Se eliminaron `.pestanas` y `.ficha-indice`, restos de las
pestañas y el índice retirados hace tiempo: 0 usos, 18 reglas y 133 líneas
fuera. Sigue habiendo CSS muerto de la ficha vieja (`.apartado`,
`.tarjeta-accion`, `.cosas`, `.dice`, `.aparte`, `.ficha-resumen`) pendiente de
una pasada aparte.

**Dos excepciones de estilo**, pedidas expresamente y anotadas arriba en su
regla: la cabecera rellena por bloque, sólo en la ficha completa, y el rojo,
sólo al señalar un borrado.

- Las altas y ediciones se probaron **sobre una copia temporal de `datos.db`**;
  la base real quedó intacta. No se cambió el esquema. La única consulta que se
  tocó añade `circulo_id` a la lista de otras personas de la ficha.
- Los recursos estáticos van por `?v=20260731h`.

### 2026-07-31 — Ajustes en caja, y la inicial en la ficha de la Red

- **Las cabeceras de Ajustes vuelven a ser una caja rellena**, con el mismo
  tratamiento que `.bloque-cabecera` de la ficha expandida: `--inverso-fondo`
  y `--inverso-texto`, o sea tinta pura de día y carbón de noche sin copiar los
  colores de un modo al otro. Antes era caja **sólo de día**: la lista antigua
  de `html[data-modo="noche"]` la devolvía a fondo de página.
- Había además una segunda definición de `.panel-cabecera`, en la capa del
  2026-07-28, que la había convertido en texto plano con un cuadradito. Era esa
  la que mandaba. Se reescribió en su sitio y el cuadrado desapareció: dentro
  de una banda rellena sobra. `.panel-cabecera` ya sólo la usa Ajustes.
- **Ajustes se comprimió**: 24px entre paneles en vez de 48, cabecera de página
  sin alto mínimo, 16px de relleno por fila y 12/16 en el texto de ayuda. Los
  círculos bajan de 64 a 55px de alto y **ahí se paran**: por debajo dejan de
  ser cómodos con el dedo.
- **En la ficha de la Red, quien no tiene foto muestra su inicial** en serif a
  33px sobre papel, como ya hacía la ficha rápida de Personas. Antes salía un
  cuadrado de tinta macizo que no decía nada de quién era. Personas no se tocó:
  ya lo hacía bien.
- **Se probó llevar también a caja las cabeceras de las dos fichas compactas y
  se descartó**, a la vista de una captura: cinco bandas en tan poco alto
  pesaban demasiado. Y el intento estaba además incompleto, porque
  `header > span:first-child` se pinta con `var(--tinta)` en una regla
  posterior y el rótulo quedaba tinta sobre tinta, ilegible. Queda anotado en
  el CSS y en `mapa/estilos.md` por si se retoma.
- No se tocó la base, el esquema ni qué información se muestra. Los recursos
  van por `?v=20260731i`.

### 2026-07-31 — Enlazar con varias, también al dar de alta

- *Enlazar con varias* se había quedado **sólo en la ficha** de alguien que ya
  existe, que es la mitad del problema: el trabajo pesado está al **dar de
  alta**, cuando llega un compañero nuevo y hay que enlazarlo con los otros
  seis de uno en uno.
- El paso 02 del alta tiene ahora el mismo componente: casillas con toda la
  gente, atajos que marcan un círculo entero y **un solo par de etiquetas**
  para todas. Convive con las filas sueltas de siempre.
- Si alguien sale en las dos, **manda la fila suelta**: el grupo se aplica
  después y salta a quien ya está enlazado. Así una etiqueta escrita a mano no
  se pisa con la del grupo.
- Sin etiqueta de grupo no se enlaza nada, aunque haya casillas marcadas.
- Con esto no hace falta ninguna acción de «todos contra todos»: **si vas
  dando de alta a la gente marcando al grupo cada vez, el resultado es el
  mismo**, cada nuevo se enlaza con todos los anteriores, y sin generar
  relaciones que tú no hayas elegido.
- `crear_persona` recibe `varias[]`, `etiqueta_varias` e `inversa_varias`. El
  bloque 9 quater de `app.js` pasó a recorrer **todas** las instancias del
  componente, que ahora hay dos.
- Probado **sobre una copia de `datos.db`**: alta con una fila suelta más los
  siete de Trabajo → 8 relaciones, la etiqueta escrita a mano intacta, y sin
  etiqueta de grupo no enlaza nada. La base real quedó intacta.
- Los recursos van por `?v=20260731j`.

### 2026-07-31 — El bloque de enlazar, legible, y el aviso de borrar propio

- **Enlazar con varias** se veía mal: el texto de ayuda se montaba encima del
  desplegable, todo era una plancha de un solo tono y salían las 27 personas de
  golpe dentro de un cajón con barra propia.
  - El solape era `.alta-ayuda`, que lleva `margin-top: -8px` para pegarse al
    título de su bloque; dentro del `<details>` eso la subía sobre el `summary`.
    Ahora tiene clase propia.
  - El bloque se parte en **tres apartados con filete**, cada uno con su rótulo
    y su cuadrado de tinta: *qué papel*, *marcar un círculo entero*, *quiénes*.
  - La gente va **por páginas**: nueve en escritorio, seis en móvil, con flechas
    y contador. Se fue el desplazamiento interno.
  - En móvil, dos columnas en vez de tres.
  - Lo que se marca en una página **no se pierde al cambiar de página**: sólo se
    oculta. Comprobado: 7 marcadas, 4 fuera de la página visible, 7 en el envío.
  - De paso: la primera pintada usaba el tamaño de página del ancho que hubiera
    al cargar, así que un bloque plegado podía abrirse con seis por página en
    escritorio. Ahora también recalcula al desplegar.
- **El aviso antes de borrar deja de ser el `confirm()` del navegador.** Salía
  pegado arriba, sin estilo y anunciando la dirección del servidor. Ahora es un
  `<dialog>` propio en `base.html`: centrado, con filete de 1px, rótulo *Esto no
  se deshace*, el texto en serif y dos botones de 40px. El trasfondo usa una
  trama binaria en vez de bajar la opacidad, como manda el estilo del proyecto.
  El foco arranca en **Cancelar**.
  - **La decisión cuelga del clic de cada botón, no del evento `close`.** Se
    descubrió probando que en este navegador `close` **no se dispara nunca**,
    ni siquiera llamando a `close()` a mano; de haberlo dejado así, borrar no
    habría hecho nada y sin avisar. Si el navegador no tiene `<dialog>`, se cae
    al `confirm()` de siempre antes que quedarse sin aviso.
  - Comprobado: aceptar envía, cancelar y Escape no envían nada, y el diálogo
    queda centrado y dentro de la pantalla también a 375px.
- No se tocó la base ni el esquema. Los recursos van por `?v=20260731n`.

### 2026-07-31 — Instalable en el móvil, y el logo en la ventana

- La app se puede **añadir a la pantalla de inicio** y abrirse a pantalla
  completa, sin la barra del navegador. Hace falta HTTPS, que ya lo da Tailscale.
- **Iconos** generados desde `img/Logo-Negro_SF.png` a `estatico/icono/`:
  192 y 512 para la instalación, un 512 **recortable** con margen del 20%
  porque Android recorta el icono a la forma del sistema y sin ese aire se
  comía las puntas de la onda, 180 para iOS, 32 y 16 de favicon, y dos `.ico`
  para la ventana de escritorio (claro y oscuro). Todos cuadrados, monocromos y
  sin esquinas redondeadas.
- **`manifest.json`** en la raíz: `display: standalone`, fondo papel `#f4efe1`,
  tema tinta `#14120f`. **Sin `orientation`**, a propósito: la red se ve mejor
  pudiendo girar.
- **Service worker mínimo en `/sw.js`, que no cachea nada.** Existe sólo porque
  sin uno registrado el navegador no ofrece instalar. Su manejador de `fetch`
  está vacío y no llama a `respondWith`, así que todo sigue viniendo del
  servidor. **No añadir caché**: la app vive en tu red, no hay latencia que
  compensar, y lo único que se ganaría es que el móvil enseñe versiones viejas.
  Comprobado tras cargar: cero almacenes de caché.
- Se sirve **desde la raíz**, no desde `/estatico/`: un service worker sólo
  alcanza su carpeta y hacia abajo. `manifest.json` y `/sw.js` entran sin llave,
  porque el navegador los pide antes de tener la cookie.
- **Zonas seguras.** El viewport lleva `viewport-fit=cover`, que es lo que
  enciende `env(safe-area-inset-*)`. La barra, la red, sus mandos, el pie de
  Apuntar y la ficha de la red respetan el notch y la barra de gestos. En el
  navegador normal esas variables valen cero, así que la geometría no cambió:
  barra a 56px, red a 56, mandos a 80/24, igual que antes.
- **La ventana de escritorio lleva el mismo icono**, vía `webview.start(icon=…)`.
  La documentación de pywebview dice que eso es sólo de GTK/QT, pero está
  desactualizada: `platforms/winforms.py` lo aplica en Windows.
- Comprobado servido: `application/manifest+json` para el manifest y
  `text/javascript` con `Service-Worker-Allowed: /` para el service worker.
- No se tocó la base ni el esquema. Los recursos van por `?v=20260731p`.

### 2026-07-31 — El logo en la barra, y la franja blanca del móvil

- **El cuadrado de tinta de la barra pasa a ser el logo.** Van las dos
  versiones en el marcado, `marca-negro.png` y `marca-blanco.png`, con fondo
  transparente y recortadas al trazo; el CSS enseña la que toca según el modo.
  Sin JavaScript y sin filtros, que sobre un trazo tramado ensucian. Se retiró
  `.marca-pixel` y su regla nocturna.
- **El icono de la ventana de escritorio ahora es el blanco sobre
  transparente**, que su barra de título es oscura. Antes llevaba un cuadrado
  de papel detrás y se veía como un recuadro. Queda `relaciones-oscuro.ico`
  por si algún día la barra de título fuera clara.
- **La franja blanca al pie del móvil** era que `<html>` no tenía fondo: con la
  app instalada, la zona de la barra de gestos queda por debajo de `<body>` y
  enseñaba el blanco del navegador. El fondo va ahora también en `html`, así
  que sigue al modo.
- **Ajustes**: se fue el filete de `.pagina-cabecera`, que duplicaba la línea
  bajo la entradilla porque el borde del primer panel ya hace de raya; y se
  fueron los filetes que separaban los círculos, que ya se distinguen por su
  propia caja.
- No se tocó la base ni el esquema. Los recursos van por `?v=20260731q`.

### 2026-07-31 — Márgenes del móvil y las barras del sistema

- **La hoja se había quedado sin márgenes laterales en móvil**, y era culpa de
  la tanda anterior: la regla de zona segura ponía `padding-left/right` con
  `env(...)`, que en vertical vale cero, y al ir después pisaba el relleno de
  los `@media`. Ahora la zona segura **se suma** al relleno en vez de
  sustituirlo: 48px en escritorio, 24 y 20 según se estrecha.
- **`theme-color` pasa a seguir al modo de la app, no al del teléfono.** Había
  dos metaetiquetas por `prefers-color-scheme`, así que un móvil en claro con
  la app en noche teñía las barras del sistema al revés. Ahora hay una sola y
  `app.js` la actualiza al arrancar y al pulsar el botón de modo. En Android es
  lo único que tiñe la barra de gestos, que es de donde salía la franja clara
  al pie de la app instalada.
- El logo de la barra baja de 28 a 22px y se acerca al borde: la marca pasa de
  24 a 16px de relleno por la izquierda.
- Los recursos van por `?v=20260731r`.

### 2026-08-01 — Se pueden borrar quedadas

- **Faltaba poder eliminar una quedada.** No era que el botón estuviera
  escondido: no existía ni la ruta. Se podía crear y editar, pero no borrar.
- Ruta nueva `POST /nota/{id}/borrar`. Las filas de `nota_persona` se van solas
  por el `ON DELETE CASCADE` que ya tenía el esquema, así que **no hizo falta
  tocarlo**.
- El botón vive en el bloque *Quedadas* de la ficha, junto a *Editar*, y sólo
  aparece en modo edición como todo lo que escribe datos.
- **El aviso nombra a quien corresponda.** Una quedada puede mencionar a varias
  personas, así que al borrarla desaparece de todas sus fichas: la confirmación
  dice «…y desaparece también de la ficha de Fulano» cuando hay más gente, y se
  queda en la frase corta cuando la quedada es sólo tuya con esa persona.
- Probado **sobre una copia de `datos.db`**: quedada con dos personas → una nota
  menos, sus dos enlaces fuera, las personas intactas, y borrar una inexistente
  no rompe nada. La base real quedó igual.
- La línea superior de la barra en móvil sube a 2px, que a 1px se veía más
  delgada que el filete de abajo.
- Los recursos van por `?v=20260801a`.
