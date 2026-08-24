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
| abrir la captura | **Notas** o **Añadir nota** |
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
circulo(id, nombre, orden, en_portada)
persona(id, nombre, apodo, circulo_id, color, cumple, notas_rapidas, foto, creada)
hecho(id, persona_id, texto, creado)
hilo(id, persona_id, texto, abierto_desde, cerrado_el, tipo)
nota(id, fecha, canal, texto, resumen, creada)
nota_persona(nota_id, persona_id)
relacion(persona_a, persona_b, etiqueta, etiqueta_inversa)
ajuste(clave, valor)                          -- sólo guarda la llave de red
```

Lo que no es evidente:

- **apodo** es «cómo le llamas». Si tiene contenido, es el nombre principal en
  listas, búsquedas, selecciones y red. El nombre completo sólo reaparece como
  subtítulo en la ficha completa y en la ficha rápida de Personas.
- **notas_rapidas** es la descripción breve de la persona: una impresión general
  de hasta cien caracteres. Se ve en las fichas y en Notas, donde es de sólo
  lectura.
- Una **nota** puede mencionar a varias personas, por eso no cuelga de una
  persona: hay tabla intermedia. La coincidencia queda registrada en las
  fichas, pero no crea relaciones ni líneas entre todos sus asistentes.
  El `resumen` opcional se enseña en fichas compactas; la ficha completa usa
  siempre `texto`. Las quedadas antiguas usan el texto como alternativa corta.
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
  sin círculo pero **no se borra** (`ON DELETE SET NULL`). `en_portada` elige
  hasta siete círculos visibles; los desactivados tampoco se dibujan en la red.
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
4. `/nota` es **Notas** y sigue accesible con la tecla `N`: grabadora integrada
   arriba en móvil, audio activo opcional, captura manual por persona y archivo
   de audios al final. Cada persona tiene un formulario independiente con
   pendientes, preguntas y datos repetibles, más una quedada con día, resumen
   y texto completo. Los audios se transcriben con faster-whisper y Qwen prepara
   esos mismos bloques para revisarlos. `/nota/{id}` edita una quedada existente.
5. `/ajustes` contiene modo día/noche, administración de círculos —incluidos los
   accesos breves de la portada— y copia de todo.

La navegación principal muestra siempre: *Red*, *Personas*, *Notas* y *Ajustes*.

## El estilo: interfaz pixelada 1-bit

El lenguaje visual toma referencias de interfaces gráficas tempranas, software
editorial y juegos de un bit. La estructura debe sentirse precisa, modular y
deliberada, nunca decorada por nostalgia sin función.

- Sólo papel `#f4efe1` y tinta `#14120f`; noche invierte ambos. La columna
  histórica `persona.color` se conserva, pero ya no se muestra ni edita.
  **Excepciones acotadas**: `--alarma`, un rojo rebajado que aparece al señalar
  con el ratón un botón que borra y en la identidad que la voz dejó dudosa.
  En el segundo caso permanece hasta confirmar con ✓ o elegir otra persona.
- Departure Mono se incluye localmente en `estatico/tipos/` bajo SIL OFL. Se usa
  a 11px para navegación, controles y rótulos. El texto largo usa serif a 16px.
- Títulos personales a 33px. Cuerpo a 16px. Interfaz a 11px.
- Filetes nítidos de 1px, esquinas rectas, selecciones por inversión de tinta y
  tramas binarias sin grises.
- Las secciones se separan con aire, filete y un pequeño cuadrado de tinta.
  Las bandas negras se reservan para acciones o estados seleccionados; no se
  repiten como cabecera de todos los paneles. **Única excepción**: en la ficha
  completa (`/persona/{id}`) y en los bloques personales de Notas cada sección
  sí lleva su cabecera rellena. Comparten exactamente `.bloque-cabecera`.
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
- Las columnas de Personas, Notas y Ajustes se centran en la ventana, pero el
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
- **Las líneas son de 1px.** En reposo sólo se dibuja la jerarquía limpia entre
  la raíz, los cuadrados activos y sus personas. Las relaciones entre dos
  personas sólo aparecen al señalar o seleccionar una de ellas.
- **No hay anillos concéntricos.** Los círculos activos se muestran dentro de la
  red como cuadrados con nombre; *Sin círculo* usa un cuadrado discontinuo.
- **Los nombres no se enseñan todos**: sólo los del 40% más cercano a la cámara
  (`CERCANIA_NOMBRES`), y al señalar a alguien sólo el suyo y los de sus
  conexiones. Siempre usan el nombre habitual si existe. Van en Departure a
  11px.
- **Al señalar, el contraste es bestia a propósito**: esa persona y sus
  conexiones a plena tinta, todo lo demás al 5%.
- La persona de **Yo** es la raíz en `(0, 0, 0)`, sin cuadrado propio. Hay una
  sola composición: los cuadrados se reparten con aire y cada grupo abre una
  estrella regular y determinista a su alrededor.
- Sólo las filas de `relacion` crean líneas entre dos personas. Coincidir en una
  quedada no presupone que todos sus asistentes se conozcan.
- Al señalar con ratón, esa persona se acerca visualmente y las próximas se
  apartan; en táctil ocurre al seleccionarla. Señalar un cuadrado realza toda su
  gente. El movimiento respeta la reducción de animaciones del sistema.
- Pulsar una **persona** o un **círculo** centra la cámara en el foco y, además,
  recoloca a su alrededor a la gente vinculada en un anillo ordenado
  (`animarFisica`, `anilloActivo`): los allegados de la persona, o toda la gente
  del círculo alrededor de su cuadrado, para que se lean como radios y no como un
  abanico desordenado. No cambia las posiciones base: son desvíos interpolados
  que vuelven a cero al soltar. Acercar, alejar y retroceder usan la misma
  transición. Nuria es la excepción (ver más abajo): no recoloca a nadie ni
  enseña sus relaciones.
- Los grupos (gente de un círculo, corro de Nuria, satélites) se reparten sobre
  una **esfera** alrededor de su centro, no sobre un plano: una esfera tiene
  volumen en los tres ejes y se lee de frente, de lado y desde arriba, mientras
  que un disco se ve de canto desde algún ángulo y vuelve a parecer plano.
- **Nuria siempre cuelga de los cuadrados de círculo, no de las personas.** Es la
  única excepción: al seleccionarla se dibuja su conexión a los círculos y no sus
  relaciones personales.
- El giro automático es de 0.00087 radianes por fotograma: una vuelta cada dos
  minutos. Calmado, pero vivo.
- La caja *Explorar la red* integra resultados de nombres y hasta siete accesos
  de círculo elegidos en Ajustes, además de acercar, alejar, centrar y pausar el
  giro. No usa desplegables nativos. El botón izquierdo arrastrado gira; el derecho o el
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

### 2026-08-02 — Captura por voz, paso 1: grabar, subir y guardar

Primer paso deliberadamente mínimo de la captura por audio: **sólo** grabar en
el móvil, subir el audio y guardarlo. **Nada de transcripción ni de IA**; se
comprueba que el audio viaja del móvil al ordenador y se guarda entero antes de
construir nada encima.

- **Tabla nueva `audio(id, archivo, grabado, estado)`**, en `ESQUEMA`, creada al
  arrancar también en bases existentes (`CREATE TABLE IF NOT EXISTS`, sin
  migración en `poner_al_dia`). `estado` es siempre `pendiente` de momento.
  **Fuera de `TABLAS_EXPORTABLES`**: la copia de todo zipea la base, no los
  archivos, y una lista apuntando a nada no sirve. Se decidirá al tratar la
  copia con audios.
- **Carpeta `audios/` junto a `datos.db`** (`CARPETA_AUDIOS`, con `BASE_DATOS`
  para que quede al lado del `.exe`). Los audios son archivos sueltos ahí,
  nunca dentro de la base. **En el `.gitignore`** con la base: contienen voz.
- **Formato: Opus donde se pueda.** El móvil elige contenedor con
  `MediaRecorder.isTypeSupported` (webm/ogg Opus en Android; mp4/AAC en iPhone,
  que no sabe grabar webm). El servidor **no transcodifica**: guarda el blob tal
  cual y le pone la extensión según `EXT_POR_MIME`. Cero dependencias nuevas,
  nada sale a internet.
- **Botón de grabar flotante en toda la app** (`base.html`, `[data-voz]`), a un
  toque desde cualquier pantalla para grabar antes de que se olvide. Plegado es
  un botón; desplegado enseña grabar/parar, cronómetro y el estado. **Sólo
  móvil**: `voz.js` sólo lo revela con puntero grueso y micrófono; en la ventana
  de escritorio no aparece. Grabar no se hace desde escritorio a propósito.
- **Cola local con reintento (`voz.js`, IndexedDB).** Al parar, el audio se
  guarda en el móvil **antes** de intentar subir, así no se pierde con el
  ordenador apagado —el requisito central—. Reintenta al abrir la app, al
  evento `online` y con un botón *Reintentar*; contador de «sin subir». Sólo
  borra de la cola lo que el servidor confirma. **No toca el service worker** ni
  cachea nada.
- **`POST /audio`** recibe el blob (fetch, no formulario) y responde JSON:
  segunda excepción a «POST + 303», junto al `/api/grafo`. **`GET /audios`** es
  la lista, **dentro de Apuntar** (enlace en la cabecera de `/nota`): fecha en
  lenguaje natural, estado y **Eliminar manual** con confirmación. **Ninguno se
  borra solo.** **`GET /audio/{id}`** sirve el original para volver a
  escucharlo; el reproductor es propio, sin `<audio controls>` nativo.
- El mapa (`backend.md`, `pantallas.md`, `interaccion.md`, `estilos.md`,
  `decisiones.md`) se actualizó en el mismo cambio; `python mapa/comprobar.py`
  pasa. No se modificó ningún dato existente; el único cambio de esquema es la
  tabla nueva, avisado y aprobado de antemano.
- En la portada, `.grafo-estado` (barra de estado fija de 32px al pie) solapaba
  el botón flotante. Se sube el botón por encima **sólo en `body.portada`**
  (`bottom: calc(48px + zona segura)`); en el resto de pantallas, donde no hay
  nada fijo abajo a la derecha, se queda en su sitio.
- Pendiente de tu visto bueno al aspecto del botón antes de darlo por bueno.
- Los recursos van por `?v=20260802b`.

### 2026-08-02 — La ficha de la red, como ventana flotante

- La ficha comprimida de la portada (`.grafo-ficha`) deja de ir de borde a
  borde en móvil y pasa a ser una **ventana flotante** con el mismo lenguaje que
  *Explorar la red*: barra de título rellena (`.grafo-ficha-titulo`, reutiliza
  `.ventana-titulo`) que dice **«Ficha resumida»**, con la × dentro de la barra
  en vez de flotando sobre el contenido.
- En móvil flota con **márgenes de 16px a los lados y arriba** (respetando la
  zona segura), y su altura se acota para **no tapar la barra de estado** del
  pie. En escritorio ya era una caja flotante arriba a la derecha; ahora también
  estrena la barra de título. La barra es `sticky` al desplazar el contenido.
- Se retiró el `padding-right: 40px` que reservaba hueco para la × flotante, en
  las dos reglas (escritorio y móvil): ya no hace falta.
- Las dos reglas móviles de `.grafo-ficha` (una anulaba a la otra desde una
  tanda vieja) quedan coherentes con la misma geometría flotante.
- **Nota de proceso:** la ruta `/audios` es código nuevo de `app.py`; las
  plantillas y los estáticos se recargan en cada petición, pero las rutas nuevas
  sólo entran al **reiniciar el proceso**. Hasta reiniciar la ventana del 9765,
  el enlace a los audios daba 404. No es un fallo del código.
- Los recursos van por `?v=20260802c`.

### 2026-08-02 — Ficha de la red: sin scroll lateral y la × alineada

- **Se va la barra de scroll horizontal.** La causa: `.grafo-ficha` tiene
  `overflow-y: auto` y `overflow-x` quedaba en `visible`, que por la regla de
  CSS lo asciende a `auto`; entonces la barra vertical, al estrechar el
  contenido, provocaba un desbordamiento de 1px y sacaba barra horizontal. Se
  fija `overflow-x: hidden`.
- **La × se despega del borde.** Pasa a insertarse 8px como el rótulo de la
  izquierda de su barra de título (`margin: -8px 0` en vez de `-8px -8px`), así
  queda simétrica con «Ficha resumida» y alineada con la barra, no pegada.
- Se retiró el `padding-right: 48px` que reservaba hueco para la × cuando
  flotaba sobre el nombre; la identidad vuelve a 16px a ambos lados.
- Los recursos van por `?v=20260802d`.

### 2026-08-03 — Fase 0 de Notas: captura manual por persona

- La pestaña visible **Apuntar pasa a llamarse Notas**. Se conservan `/nota` y
  las tablas internas para no mover rutas ni datos; los accesos desde las
  fichas dicen *Añadir nota*. La tecla `N` sigue abriendo la pestaña.
- `/nota` estrena `notas.html`. El orden es: grabadora · audio activo opcional ·
  captura manual · archivo de audios. `/nota/{id}` conserva `nota.html` para
  editar una quedada existente.
- **La grabadora es la misma**, extraída a `_grabadora.html`: dentro de Notas
  queda arriba y en el flujo de la página; en el resto sigue flotante. No se
  cambió `voz.js`, la cola offline ni el formato de los audios.
- **Audio activo**: se puede elegir una grabación existente o trabajar sin
  audio. La elección actualiza el reproductor, propaga `audio_id` a los bloques
  abiertos y propone como día de la quedada el día de grabación. En esta fase
  no se transcribe, no se analiza, no cambia `audio.estado` y no se borra nada.
- **Captura por persona**: el selector integrado sólo admite gente que ya está
  en la base. Cada elección abre un formulario `.ficha` independiente con
  identidad y las cabeceras `.bloque-*` ya existentes. *Queda pendiente*,
  *Preguntar por* y *Datos* admiten varias filas; la quedada es una sola y lleva
  día, resumen corto y texto completo adaptado. Todo es opcional salvo que, si
  se usa la quedada, se piden sus dos textos.
- `POST /nota/persona/{id}` guarda sólo ese formulario, en una transacción:
  varios `hilo`, varios `hecho` y, si existe, una `nota` enlazada a esa persona.
  Sigue siendo un formulario HTML normal con 303. JavaScript lo envía como
  mejora para retirar sólo el bloque confirmado y conservar los demás.
- Los campos llevan `data-campo` y nombres estables para que el futuro contrato
  de Qwen reproduzca exactamente la estructura que ahora se rellena a mano.
  Qwen y Whisper **no se integraron** en esta fase.
- **Esquema**: `nota` añade `resumen TEXT`, mediante `poner_al_dia()` idempotente.
  Personas y Red enseñan `resumen` en sus fichas compactas; la ficha completa
  sigue enseñando sólo `texto`. Las filas antiguas, con resumen vacío, caen a
  su texto actual. No se perdió ni se transformó ningún dato real.
- El archivo se comparte en `_audios_lista.html` entre el final de Notas y la
  ruta antigua `/audios`, que se conserva. Los nombres físicos siguen siendo
  internos; en pantalla los audios se nombran por fecha y hora naturales.
- Comprobado con una base temporal: dos pendientes, dos preguntas, dos datos y
  una quedada se guardan en la ficha correcta; la vista compacta usa el resumen
  y la completa el texto largo. La base real sólo recibió la columna nueva.
- Revisado a **375 px en día y noche** contra `/persona/{id}`. Se corrigió el
  solapamiento móvil de *Quitar bloque*. El navegador quedó sin errores, el mapa
  pasa y los recursos suben a `?v=20260803a`.

### 2026-08-03 — Notas: archivo real, plegado y paginado

- La captura vacía ya no reserva altura para el aviso ni para los bloques: antes
  de elegir persona, el archivo sube y desaparece el hueco sin función.
- La apertura normal de `/nota` sigue sin persona seleccionada. La captura de
  Karmela que se enseñó para validar la ficha era un estado de prueba elegido a
  mano, no el estado inicial de la pantalla.
- Tanto el selector de audios pendientes como el archivo visible descartan las
  filas cuyo archivo ya no existe en `audios/`. Las filas huérfanas se conservan
  en la base: abrir la pantalla no borra ni repara datos silenciosamente.
- El archivo de audios queda plegado por defecto y se pagina de cinco en cinco,
  con las mismas flechas y filetes del archivador. Al cambiar de página o borrar
  manualmente, vuelve abierto a su ancla.
- Recursos actualizados a `?v=20260803b`.

### 2026-08-03 — Audios enlazados, borradores plegables y tarjeta multimedia

- **Invariante de audio:** cada fila de `audio` tiene exactamente un archivo en
  `audios/` y viceversa. `reconciliar_audios()` se ejecuta al arrancar, recupera
  archivos sueltos como pendientes, retira filas sin original, resuelve
  duplicados y crea un índice único por nombre físico.
- La subida escribe primero un temporal y confirma fila + archivo con
  compensación de errores. El borrado aparta el archivo antes de tocar SQLite y
  lo restaura si la transacción falla. `.audios-borrados/` queda fuera de git.
- La base real tenía seis filas para cuatro archivos: se retiraron las dos filas
  sin original. No se borró ni alteró ninguno de los cuatro audios existentes.
- Los apartados *Queda pendiente*, *Preguntar por*, *Quedada* y *Datos* de cada
  borrador empiezan plegados y reutilizan el control de plegado de la ficha.
- *Quitar bloque* pasa a **Descartar borrador**, con una aclaración visible de
  que sólo retira el formulario sin borrar la persona ni cambiar su ficha.
- El reproductor publica metadatos propios para la tarjeta multimedia de
  Android: *Nota de voz*, fecha/hora y logotipo. El modo claro usa el icono
  original y el oscuro `audio-oscuro-512.png`, derivado de forma determinista
  con carbón `#23241f` y crema `#ddd6c6`.
- Recursos actualizados a `?v=20260803c`.

### 2026-08-03 — Transcripción local, contrato Qwen y revisión por persona

- Los audios pendientes se procesan automáticamente, uno por uno, en un hilo
  demonio: `faster-whisper` usa `large-v3` en CUDA (con caída local a CPU) y
  Ollama usa `qwen3:14b`. Ninguno habla con internet. Si la app se cierra a
  mitad, `poner_al_dia()` recupera el estado para continuar al abrir.
- `audio` añade de forma idempotente transcripción, marca de edición, borrador
  JSON, error, fecha de actualización y versión del contrato. `audio_registro`
  enlaza cada hilo, dato o quedada confirmada con su grabación de origen. La
  migración es aditiva y no borra ni transforma datos existentes.
- El contrato versionado devuelve bloques por persona existente: pendientes,
  preguntas y datos repetibles; una quedada con día, resumen y texto adaptado;
  candidatos, identidad dudosa y contenido sin asignar. La aplicación valida
  todos los ids y funde dos menciones de una misma persona antes de enseñar nada.
- La persona que habla es siempre la del círculo *Yo*. «Mi madre» se resuelve
  por la relación explícita y un posprocesado evita separar Carmela, Karmela y
  «mi madre». Entre homónimos, las conexiones con el resto del grupo deciden
  sólo si existe una ventaja clara; en empate, la propuesta queda roja y no se
  guarda hasta pulsar ✓ o elegir otra persona.
- La fecha de la quedada del borrador es siempre la fecha de grabación: un
  viernes o un día 11 mencionados dentro son contenido, no el día de la llamada.
  El resumen se limita a 160 caracteres y `sin_asignar` no repite texto que ya
  pertenezca a un bloque.
- El audio activo carga `_audio_proceso.html`: estado, transcripción plegada,
  borrador editable y confirmación individual. *Volver a analizar* repite
  Whisper desde el original. *Editar* desbloquea el texto y se convierte en
  *Enviar a Qwen*, que no repite Whisper. *Validar todo* guarda sólo bloques
  completos y deja en pantalla los dudosos o incompletos. Al confirmar una
  persona, su bloque desaparece.
- Una quedada de grupo se guarda una sola vez y se enlaza con todas sus personas.
  Los bloques ya confirmados permanecen en el JSON como memoria para que un
  nuevo análisis del mismo audio no vuelva a proponerlos.
- El borrado manual de audios sigue usando el diálogo propio, pero el segundo
  envío se hace por `fetch`: retira la fila sin recargar ni mover la página.
- Prueba real con el único audio: Whisper transcribió «mi madre, Karmela» y Qwen
  produjo un solo bloque, persona 2 (Karmela), sin ambigüedad. No se confirmó el
  bloque, así que ninguna ficha cambió. La transcripción y el borrador quedaron
  guardados en la fila del audio para revisarlos desde la app.
- Pruebas de identidad: Marina + Nacho + Susi + Marta elige a Marti Marti
  (Barrio) por tres conexiones frente a ninguna de Marta (Trabajo); una Lucía
  aislada conserva las dos candidatas y queda pendiente de confirmación.
- Revisado en escritorio y a 375 px, día y noche: sin desbordamiento horizontal,
  sin errores de consola y con el mismo lenguaje de la ficha. Recursos en
  `?v=20260803d`.

### 2026-08-03 — Lenguaje natural, fechas y canal en el borrador de voz

- El contrato Qwen pasa a v2 y añade el canal editable de la quedada. La llamada
  del audio real se reconoce como *Llamada* y se guarda en `nota.canal` sólo al
  validar el bloque.
- La clasificación ya no depende de que la voz diga literalmente «preguntar»:
  un acontecimiento futuro significativo propone seguimiento. Como la cabecera
  ya dice *Preguntar por*, el contenido es el asunto natural —*El viaje a
  Huelva*—, sin otra pregunta ni una fecha de agenda.
- Qwen hace una primera propuesta y una segunda auditoría de clasificación,
  identidad, calendario, canal y fidelidad. El normalizador corrige combinaciones
  imposibles de día y fecha, resuelve referencias cercanas y bloquea planes,
  viajes y compras puntuales en Datos.
- El resumen compacto usa una frase humana y tiempo relativo; la versión
  extendida conserva fechas, horarios y discurso indirecto. En la prueba real:
  *Hablamos de que se iba de viaje a Huelva esa misma semana* y, en el texto
  completo, viernes 7 de agosto, salida a las 8:00, llegada a las 16:00 y vuelta
  el martes 11.
- El borrador corregido permanece sin confirmar. `audio_registro` sigue vacío
  para ese audio, por lo que la ficha de Karmela no ha recibido todavía ningún
  hilo, dato ni quedada. Recursos actualizados a `?v=20260803e`.

### 2026-08-03 — Arranque automático dentro del entorno de los modelos

- Un arranque desde el Python global podía levantar FastAPI con normalidad pero
  fallar después al importar `faster_whisper`. El audio quedaba intacto en estado
  de error y la consola repetía que faltaba el módulo.
- `main.py` se relanza ahora con `venv/Scripts/python.exe` antes de importar la
  aplicación siempre que se ejecute desde el código y exista ese entorno. Ya no
  depende del comando de activación propio de cada terminal. El ejecutable
  empaquetado mantiene su arranque actual.

### 2026-08-03 — Recuperación del audio 8 y borrador sin contaminación

- El audio 8 falló inicialmente porque el servidor escuchaba en 9765 desde el
  Python global, que no tenía `faster_whisper`. El `venv` estaba sano y contenía
  `faster-whisper 1.2.1` y `ctranslate2 4.8.1`; no se reinstaló ni se recreó.
  El relanzado automático usa ahora un proceso hijo del Python del entorno, en
  vez de `os.execv`, que en Windows perdía el contexto del `venv`.
- La transcripción se recuperó desde el mismo archivo, sin borrar ni duplicar
  el audio. El proceso que escucha en 9765 cuelga ahora de
  `venv/Scripts/python.exe` y el audio queda en estado `listo`, sin error.
- Se retiraron del prompt todos los nombres, lugares y fechas de los ejemplos:
  el caso de Huelva estaba contaminando audios posteriores. Un bloque de `es_yo`
  se descarta siempre y un nombre exacto como Diego prevalece sobre un id que el
  modelo haya asociado mal.
- Una enumeración explícita como «quedamos Susi, Diego, Coba y yo» limita los
  enlaces de la quedada a esas personas: Miguel puede permanecer en el relato
  del viaje futuro, pero no recibe una quedada a la que no asistió. Los lugares
  se quedan en el texto y el canal se normaliza a *En persona*.
- Qwen separa ahora propuesta, auditoría, inventario de hechos y redacción. La
  prueba real exige conservar tren, acompañantes, día 13, coche, nuevo trabajo,
  salida a las tres, viaje con la tía, vacaciones y plaza antes de aceptar el
  borrador. Las referencias se resolvieron como domingo 2, lunes 3 y jueves 13
  de agosto.
- El borrador final propone *El nuevo trabajo* para Susi, *El viaje con su tía*
  para Coba y *Las vacaciones* para Diego. Sigue sin confirmar:
  `audio_registro` permanece vacío y ninguna ficha ha cambiado.

### 2026-08-03 — Captura abierta y sincronizada con el buscador

- Los cuatro apartados de cada borrador manual y automático nacen desplegados;
  siguen pudiéndose plegar individualmente después. Ya no aparece una ficha
  nueva convertida en cuatro bandas cerradas sin campos visibles.
- `.bloque-plegar` deja de heredar el centrado general de los botones. Etiquetas,
  campos y texto de la captura quedan alineados a la izquierda, también en
  *Quedada*, que no lleva contador.
- Al escribir sobre una persona elegida o pulsar la × del buscador, el selector
  comunica qué elección se ha limpiado y desaparece su bloque correspondiente.
  Es una retirada local del borrador: no borra ni modifica la ficha real.
- Recursos actualizados a `?v=20260803f`.

### 2026-08-03 — Estado visible al volver a analizar

- *Volver a analizar* deja de parecer una acción sin respuesta: en el mismo
  clic cambia a *Volviendo a analizar…*, se desactiva y muestra junto al botón
  que Whisper está transcribiendo el audio de nuevo.
- El estado del audio activo también se actualiza de inmediato y el aviso usa
  `aria-live`. Los fragmentos posteriores mantienen *Procesando audio…* hasta
  que termina; el primero espera 900 ms para no borrar la respuesta visual en
  el mismo instante. Si la petición falla, el botón se recupera y aparece el error.
- Recursos actualizados a `?v=20260803g`.

### 2026-08-05 — Límite y recuperación del análisis de voz

- El audio 9 demostró un fallo distinto de la subida y la transcripción: Qwen
  siguió razonando durante diez minutos, superó decenas de miles de tokens y
  terminó por tiempo agotado. El archivo y sus 260 caracteres transcritos no se
  perdieron; la fila quedó en `error_analisis`.
- Cada llamada a Qwen limita ahora su salida: 4096 tokens cuando razona y 8192
  cuando redacta directamente, con una espera máxima de tres minutos.
- Si una llamada con razonamiento devuelve una respuesta vacía, incompleta o
  inválida, se repite una sola vez sin razonamiento largo. Si también falla, la
  cola conserva el audio y la transcripción y muestra el error como antes.
- Una prueba aislada verificó la sintaxis, los dos límites, el plazo y el cambio
  automático al segundo intento. Una llamada real a `qwen3:14b`, con contenido
  sintético y sin datos personales, confirmó que Ollama acepta el nuevo límite
  y devuelve el JSON esperado.

### 2026-08-05 — Ejecutable autocontenido de Windows

- `Relaciones.spec` genera un único ejecutable con Python 3.12, FastAPI,
  pywebview, faster-whisper, plantillas y recursos locales. Excluye Torch y
  TensorFlow, que la app no usa para transcribir, y deja fuera los modelos.
- `construir.ps1` localiza un Python válido, prepara dependencias aisladas en
  `.paquete-deps/`, construye en `dist/` y copia el resultado junto a `datos.db`.
  `requisitos-paquete.txt` fija las versiones necesarias para repetirlo.
- El primer `Relaciones.exe` ocupa 167,9 MB. Se probó desde
  `build/prueba-paquete`, con modelos desactivados y una base nueva aislada:
  arrancó sin depender del Python desinstalado, creó sus carpetas, respondió
  `200 / vale` y liberó correctamente el puerto 9765 al cerrar. La copia final
  sirvió además la portada, Notas, el manifiesto móvil y `estatico/app.js`, todos
  con estado 200; las dos bases vacías y copias de prueba se retiraron después.
- El ejecutable debe quedarse junto a la base y los audios. Ollama,
  `qwen3:14b` y el modelo `large-v3` siguen en sus almacenes locales para no
  convertir cada versión de la aplicación en un archivo de varios gigabytes.

### 2026-08-05 — Cambiar persona o descartar un bloque del audio

- Todos los bloques automáticos muestran ahora *Cambiar persona*, también
  cuando Qwen había asignado una persona sin dudas. La ruta `resolver` existente
  conserva el contenido y sólo cambia la ficha a la que se aplicaría.
- *Descartar bloque* retira la propuesta completa sin guardar pendientes,
  preguntas, datos ni quedadas. No borra la persona ni toca su ficha. Si era el
  último bloque por decidir, el audio queda en estado `revisado`.
- La eliminación pide confirmación mediante el diálogo propio. Como el proceso
  del audio llega en un fragmento HTML, `iniciarConfirmacion()` registra también
  esos formularios dinámicos antes de que el envío por `fetch` los intercepte.
- En móvil, los dos formularios de acción y sus botones ocupan todo el ancho.
  Recursos actualizados a `?v=20260805b`.
- Las rutas se probaron con una base aislada: cambiar de Ana a Bea conservó
  *Llamarla* y *El viaje*; eliminar uno de dos bloques mantuvo el audio `listo`
  y eliminar el último lo dejó `revisado`, sin filas nuevas en `hecho`, `hilo`,
  `nota` ni `audio_registro`.
- La prueba en navegador confirmó además que Cancelar conserva el bloque, que
  el diálogo nombra la ficha afectada y que la eliminación refresca el estado.
  A 390 px, ambos formularios quedan apilados y sus botones ocupan todo el
  ancho; no hubo errores de JavaScript. El servidor y la base ficticios se
  retiraron al terminar.
- El servidor ya dejaba correctamente los audios 9 y 10 en `revisado`, pero la
  opción del selector conservaba en el DOM el texto anterior *Listo para
  revisar*. `cargarProceso()` actualiza ahora ese texto y retira del selector la
  opción cuando el fragmento confirma que ya está revisado. La ficha activa se
  queda visible con *Revisado* para que la acción tenga respuesta inmediata.
- El verbo visible pasó de *Eliminar* a *Descartar*: el botón, el texto del
  diálogo y su acción final dicen *Descartar bloque* / *Descartar*, sin confundir
  la propuesta con datos ya guardados.

### 2026-08-05 — La ficha conserva la posición en todas sus acciones

- Guardar, añadir, completar o eliminar dentro de un bloque ya no salta a su
  ancla al volver: con JavaScript se restaura la posición exacta anterior y el
  ancla queda sólo como respaldo sin JavaScript.
- La posición se guarda por pantalla, no en una única entrada compartida. Así,
  salir de la ficha para editar una quedada y regresar tampoco pierde el punto
  de lectura aunque la pantalla intermedia guarde su propia posición.
- Los enlaces con un `volver` hacia la ficha conservan ahora su posición antes
  de salir. Si el regreso incluye un ancla, se retira en el `<head>` sólo cuando
  existe una posición exacta pendiente, antes de que el navegador salte a ella.
- La prueba en navegador detectó además el reajuste local al mostrar controles:
  pulsar *Editar* movía la ficha unos píxeles aunque no hubiera recarga. Editar,
  plegar y abrir la edición individual de una relación reafirman ahora la misma
  posición después del cambio de altura; `.ficha` desactiva además el anclaje
  automático del navegador, que era quien la recolocaba. La posición se reafirma
  durante dos pintados consecutivos para cubrir el ajuste de foco del control.
  Recursos actualizados a `?v=20260805g`.

### 2026-08-05 — README para quien descubre e instala Relaciones

- El README deja de abrir con la arquitectura y presenta primero qué problema
  resuelve Relaciones, con un ejemplo reconocible y un recorrido por sus cuatro
  pantallas.
- La instalación recomendada es ahora la carpeta portátil con `Relaciones.exe`:
  explica el aviso de Windows, dónde nacen `datos.db` y `audios/`, por qué no se
  debe mover el ejecutable solo y cómo crear un acceso directo.
- Ollama, Qwen, Whisper y Tailscale quedan como ampliaciones opcionales, con
  pasos separados, expectativas sobre las primeras descargas y una advertencia
  explícita de usar Tailscale Serve, nunca Funnel.
- Se añadieron instrucciones de primera apertura, copia completa, actualización,
  desinstalación y resolución de los fallos más habituales. Python, Git y la
  construcción del ejecutable pasan a un apéndice para personas técnicas.

### 2026-08-05 — Whisper cae a CPU si CUDA falla al transcribir

- El audio 11 se subió completo, pero permaneció pendiente hasta reiniciar. Al
  reintentarlo apareció el error real: `cublas64_12.dll` no estaba disponible.
- La caída a CPU sólo cubría la construcción de `WhisperModel`. faster-whisper
  devuelve un generador y CUDA puede fallar después, al recorrer los segmentos;
  ese error dejaba el audio en `error_transcripcion` sin probar el procesador.
- La transcripción se consume ahora dentro de `_transcribir_con_whisper()`. Si
  el modelo activo era CUDA y falla en cualquier momento, se reconstruye una
  sola vez en CPU con `int8` y se repite el mismo archivo. Si CPU también falla,
  se conserva el error normal para poder diagnosticarlo.

### 2026-08-05 — El archivo de audios conserva su posición

- Las flechas del archivo de audios llevan un marcador explícito para que el
  bloque común de navegación guarde la posición antes de cambiar de página.
  El ancla `#audios` queda como respaldo sin JavaScript, pero ya no provoca el
  salto cuando el navegador puede restaurar el punto exacto.
- El paginador queda cerrado también por debajo con un filete, agrupando la
  lista, las flechas y el número de página en una sola pieza visual. Si hay
  varias páginas, el listado conserva el alto de cinco filas: sin esa reserva,
  una última página corta reducía el alto del documento y el navegador no
  podía restaurar la posición aunque estuviera guardada. Recursos actualizados
  a `?v=20260805i`.

### 2026-08-07 — README reorganizado en tres partes por público

- El README se reordena en tres bloques numerados con su propio índice: *Qué es
  Relaciones* (para quien no conoce el producto), *Instalarla y usarla* (guía de
  instalación completa, con móvil y voz como opcionales) y *Cómo funciona por
  dentro* (para personas técnicas). Una tabla de rutas al principio manda a cada
  lector a su parte.
- *Qué es* estrena *Las cuatro pantallas* y *Qué NO hace, a propósito*, que
  resume en positivo las prohibiciones del proyecto (sin métricas, sin
  recordatorios, sin cuentas, sin internet, sin importar contactos).
- La antigua sección técnica, que sólo tenía clonar/instalar/arrancar, pasa a
  explicar la pila real (FastAPI + uvicorn + pywebview en `app.py`, SQLite sin
  ORM, front plano de un bit, puerto 9765 fijo), que nada sale a internet,
  `ejemplo.py` para datos de prueba, la construcción del `.exe` y el mapa del
  código.
- Sólo se tocó `README.md`. No se cambió código, plantillas, base ni esquema.

### 2026-08-11 — README de GitHub para personas no técnicas

- El README vuelve a presentar el propósito de Relaciones antes de la
  instalación y ofrece dos recorridos dentro del mismo documento: una guía de
  uso sin conocimientos de programación y un apéndice técnico breve. Así se
  evita duplicar requisitos, privacidad y copias en dos archivos distintos.
- La descarga distingue expresamente el ZIP de código de una carpeta portátil
  con `Relaciones.exe`. Si GitHub no ofrece todavía una Release para Windows,
  no se promete una aplicación instalable que el repositorio no contiene.
- La guía explica las cinco vistas, el primer uso, la ubicación de `datos.db` y
  `audios\`, las copias completas, las actualizaciones, los fallos habituales y
  las ampliaciones opcionales de voz y móvil. La privacidad separa el uso local
  de las descargas iniciales de dependencias y modelos.
- El apéndice conserva el arranque desde código, la arquitectura, los datos de
  prueba, el mapa y la construcción con PyInstaller. Se añadió el logotipo local
  con una variante para cada modo de color de GitHub; no hay insignias ni
  recursos remotos.
- Sólo se tocaron `README.md` y este registro. No se cambió código, plantillas,
  base de datos ni esquema. `mapa/comprobar.py` sigue pasando completo.

### 2026-08-11 — Corrección del README tras comprobar GitHub

- Se revisó la página pública y se sincronizó primero el commit más reciente
  para no pisar la edición hecha directamente en GitHub. La rama pública
  contiene el código, los recursos, `instalar.bat`, `Relaciones.bat` y los dos
  archivos de requisitos; no contiene `Relaciones.exe`, `datos.db` ni
  `audios/`, y no tiene Releases publicadas.
- Se retiró toda la sección *Lo que no hace, a propósito*, como se pidió.
- La guía deja de especular con una futura carpeta portátil o con Releases. El
  recorrido principal parte ahora de lo que sí está publicado: **Code →
  Download ZIP**, Python, dos órdenes de preparación y `Relaciones.bat` para
  los arranques posteriores.
- Se eliminaron también las instrucciones de copia, actualización y resolución
  de fallos que daban por hecho que el lector había recibido
  `Relaciones.exe`. El apéndice conserva la construcción del ejecutable sólo
  como operación técnica opcional.
- `instalar.bat` no se recomienda en la guía porque el archivo publicado pide
  `requirements.txt`, que no existe; el repositorio contiene `requisitos.txt` y
  `requisitos-paquete.txt`. El instalador no se modificó en este cambio.
- Sólo se tocaron `README.md` y este registro. No se cambió código, plantillas,
  base de datos ni esquema.

### 2026-08-18 — Una red única, limpia y continua

- La red deja una sola composición estable, sin selector de orden. Nuria es el
  origen sin cuadrado *Yo*; los cuadrados activos se reparten con aire por el
  volumen y las personas forman estrellas regulares alrededor del suyo. Las
  etiquetas que se solapan se omiten y la orientación inicial es determinista.
- Ajustes manda sobre el contenido visible: un círculo desactivado no crea
  cuadrado ni mete a su gente directa en el lienzo. *Sin círculo* respeta la
  misma selección; quienes no tienen círculo pero sí una relación explícita con
  una persona visible pueden seguir apareciendo como satélites, sin heredar su
  clasificación. Las quedadas nunca crean conexiones.
- Las relaciones entre personas sólo aparecen al señalar o seleccionar una.
  David enseña así únicamente su relación explícita con Iciar, sin líneas
  atribuidas a la gente que acudió a la misma quedada.
- Señalar un círculo realza su cuadrado, su gente y los satélites vinculados sin
  mover la cámara. Señalar una persona la acerca y separa suavemente los puntos
  próximos para despejar el clic; no hay muelles ni rebotes. El giro automático
  se detiene mientras el puntero está sobre un punto o un círculo.
- Pulsar un círculo o una persona no recoloca nada: cambia objetivos de cámara y
  posición que se alcanzan con interpolación fotograma a fotograma. Rueda,
  botones, enfoque y retroceso comparten esa transición, de modo que acercar y
  alejar dejan de dar saltos. Pulsar fuera retrocede persona → círculo → red.
- Ajustes separa los círculos activos de los desactivados. Las casillas son
  cuadrados de un bit, sin azul nativo; al guardar aparece a la izquierda una
  confirmación temporal. La administración completa sigue plegada y paginada de
  cinco en cinco, y *Ver todos* abre directamente esta subsección.
- `circulo.en_portada` es una migración aditiva e idempotente; *Sin círculo* se
  guarda en `ajuste.sin_circulo_en_portada`. No se modifica ni se pierde ninguna
  clasificación, relación, quedada o persona.
- Editar, plegar o abrir una relación en la ficha conserva el control pulsado en
  el mismo punto visible, incluso cuando el bloque cambia de altura.
- Revisado en navegador real: composición general, realce de círculo, enfoque de
  persona, cámara progresiva, exclusión de círculos desactivados y confirmación
  de guardado. Sintaxis Python/JavaScript, plantillas, mapa y recursos versionados
  se comprueban en el mismo cambio.

### 2026-08-18 — Los satélites dejan de flotar

- Las personas sin círculo que sólo entran en la red por una relación explícita
  (los «satélites» que coloca `colocarSatelites`) se dibujaban como puntos
  sueltos: quedaban cerca de su relación pero sin ninguna línea que los uniera.
- Ahora cuelgan de cada una de sus relaciones visibles con una **línea
  secundaria**: siempre **discontinua** (`setLineDash([2, 3])`) y más tenue que
  la estructura raíz → círculo → persona, para que ningún punto flote sin
  atribuirle un círculo que no tiene.
- La línea es sólo un ancla visual: no cambia qué se conecta con quién ni la
  clasificación del satélite. Al señalar o seleccionar a esa persona, su
  relación pasa a la línea sólida de `aristas` como siempre (la discontinua se
  omite en ese tramo para no dibujar doble). El resto de la red baja de
  contraste igual que antes.
- Nuevo array `satelites`, construido junto a `estructura` en `montar()` y
  dibujado en `pintar()` antes del paso de `aristas`. No se tocó la base, el
  esquema ni `/api/grafo`. El mapa (`interaccion.md`) se actualizó en el mismo
  cambio y `python mapa/comprobar.py` pasa. Los recursos van por `?v=20260818g`.

### 2026-08-18 — Red con volumen, líneas de aislados acotadas y lomo suave

Tres arreglos sobre la red, todos en `grafo.js` (sigue sin tocar backend ni base):

- **Profundidad de verdad (dejaba de parecer 3D al girar).** Cada grupo —la
  gente de un círculo, el corro de Nuria y cada satélite— se colocaba en un
  anillo plano sobre el plano de la pantalla (la Z variaba ±55 frente a ~300 de
  radio), así que al girar la cámara todo se veía como una losa fina. Ahora cada
  grupo vive en un **disco inclinado en el espacio**, con una orientación
  moderada y determinista por grupo (`baseDelDisco`, `enDisco`, constante
  `TILT`). De frente sigue siendo una estrella/elipse legible —la vista frontal
  que ya gustaba se conserva—; al girar, cada disco enseña su propia profundidad
  y el conjunto tiene volumen. Los cuadrados de círculo también ganan algo de
  fondo (factor Z de `ejesDeCirculos` de 0,3 a 0,55).
- **La línea secundaria, sólo en los puntos AISLADOS.** El día anterior se tendió
  a *todos* los satélites, y con datos reales eso tejía una maraña de discontinuas
  entre la gente sin círculo (p. ej. el corro de Barrio). Se acota a los puntos
  aislados de verdad: una persona sin círculo cuya única atadura es su relación y
  cuyo componente sin círculo tiene **un único miembro**. Una nube de gente sin
  círculo ya se lee junta y no recibe líneas encima.
- **El lomo círculo→Nuria, apenas visible al señalar.** Al seleccionar a alguien,
  la línea de su cuadrado a Nuria se dibujaba tan fuerte (0,44) como la de la
  propia persona, y quedaba fea y ruidosa. Se separa `tocaCirculo` y baja a 0,12:
  sitúa el círculo sin competir con la persona ni con sus relaciones, que siguen
  siendo el foco.

- Verificado en una copia aislada de `datos.db` (servida aparte, sin modelos):
  `grafo.js` carga sin errores de consola y dibuja las 43 personas, 7 círculos y
  116 relaciones reales. El aspecto fino de la inclinación queda a tu ojo: si es
  demasiada o poca, se ajusta la constante `TILT` y el factor Z. El mapa
  (`interaccion.md`) se actualizó en el mismo cambio y `python mapa/comprobar.py`
  pasa. Los recursos van por `?v=20260818h`.

### 2026-08-18 — Esferas, allegados en anillo, vaivén vivo y la excepción de Nuria

Cuatro cambios sobre la red (`grafo.js`), atendiendo tus apuntes:

- **Esferas, no discos.** Los discos inclinados de la tanda anterior seguían
  viéndose de canto desde algún ángulo y volviendo a parecer planos. Ahora cada
  grupo —gente de un círculo, corro de Nuria y cada satélite— se reparte sobre
  una **esfera** alrededor de su centro (`direccionEsfera` + `colocarEnEsfera`).
  Una esfera tiene volumen en los tres ejes, así que de frente, de lado y desde
  arriba siempre hay profundidad y se lee. Se retiraron `baseDelDisco`, `enDisco`,
  `TILT` y las utilidades `normaliza3`/`cruz` que sólo usaban.
- **Al seleccionar a alguien, sus allegados se recolocan en un anillo** a su
  alrededor (`animarFisica`, `radioAnillo`), en vez de quedar en el abanico
  desordenado que salía cuando las relaciones apuntaban a donde cada uno estuviera.
  Son desvíos interpolados: no cambian la posición base y vuelven a cero al
  soltar. **Esto cambia la regla anterior** de que pulsar una persona nunca
  recolocaba nada; se actualizó arriba en «La red».
- **El vaivén del ratón sigue vivo dentro de una ficha.** Antes, al entrar en una
  persona, se perdía el efecto de que la gente cercana se apartaba del puntero.
  Ahora `bajoPuntero` alimenta ese apartar aunque haya alguien seleccionado, sin
  cambiar su ficha ni su cámara.
- **Excepción única de Nuria: cuelga de los círculos, no de las personas.** Al
  seleccionar a Nuria (`central`) no se dibujan sus relaciones personales; su
  conexión visible son los cuadrados de círculo, siempre, con independencia de lo
  que tenga en su ficha.

- Verificado en copia aislada de `datos.db` (servida aparte, sin modelos):
  `grafo.js` carga y dibuja las 43 personas / 7 círculos / 116 relaciones sin
  errores de consola. El aspecto fino —tamaño de las esferas, radio del anillo,
  fuerza del vaivén— queda a tu ojo; se ajustan `radioAnillo`, las distancias de
  `colocarEnEsfera` y la fuerza de `animarFisica`. No se pudo capturar pantalla
  por automatización (el lienzo de una pestaña no visible se lee en negro). El
  mapa (`interaccion.md`) se actualizó en el mismo cambio y
  `python mapa/comprobar.py` pasa. Los recursos van por `?v=20260818i`.

### 2026-08-18 — Ficha plegable, Nuria sólo a círculos y el círculo también recoloca

- **La ficha resumida se pliega** como *Explorar la red*: su rótulo es ahora un
  botón (`#grafo-ficha-plegar`) con su signo +/− que oculta el contenido; la ×
  sigue cerrándola del todo. El estado plegado se conserva entre selecciones.
  CSS nuevo `.grafo-ficha-plegar` y `.grafo-ficha[data-plegado="si"]`.
- **Nuria: sólo los círculos en tinta, el resto de personas en gris.** Ya no se
  realzaban únicamente sus relaciones al seleccionarla. Nueva función
  `resaltada(n, a)`: la regla normal (persona + sus relaciones) salvo para Nuria
  (`central`), donde no se realza ninguna persona —sólo ella— y **todos los
  círculos se encienden**, porque su vínculo son los cuadrados, no la gente. Sus
  aristas personales ya no se dibujaban (tanda anterior); esto completa la
  excepción también en puntos y nombres.
- **Pulsar un círculo recoloca a su gente en un anillo** alrededor del cuadrado,
  igual que al entrar en una persona. La lógica del anillo se extrajo a
  `anilloActivo()`, que sirve tanto a la persona (sus allegados) como al círculo
  (su gente por `enCirculoVisual`). Sigue sin tocar posiciones base: desvíos
  interpolados que vuelven a cero al soltar. Se actualizó la regla de «La red».
- Verificado en copia aislada de `datos.db` (sin modelos): sin errores de
  consola tras seleccionar persona, círculo y Nuria; el toggle de la ficha
  alterna `data-plegado` si/no y el signo +/−. El aspecto fino queda a tu ojo.
  El mapa (`interaccion.md`) se actualizó; `python mapa/comprobar.py` pasa.
  Recursos: `grafo.js?v=20260818j`, `estilo.css?v=20260818j`.

### 2026-08-19 — Editar el texto de pendientes, preguntas y datos

- En la ficha, al entrar en edición cada línea de *Queda pendiente*, *Preguntar
  por* y *Datos* ya no ofrece sólo cerrar, eliminar o quitar: enseña un campo con
  su propia frase y *Guardar* para **corregir el texto en el sitio**. Antes había
  que borrar y volver a escribir.
- El texto de reposo lleva `data-solo-lectura` y se oculta únicamente cuando el
  bloque está en edición (`[data-edicion="si"]`); sin JavaScript se ven el texto
  y el campo, como el resto de la ficha.
- Ruta nueva `POST /hilo/{id}/editar` para pendientes y preguntas. Los datos
  reutilizan `POST /hecho/{id}`, que ya existía pero no estaba enlazado en
  ninguna pantalla; ahora recibe `volver` para el ancla de respaldo. En los dos,
  un texto vacío **no borra** —para eso están *Eliminar* y *Quitar*— y el texto
  se recorta. La posición de lectura se conserva como en el resto de acciones.
- `.linea` admite ahora salto de línea para que el campo y las acciones quepan en
  móvil. Nada cambia en reposo.
- Probado sobre una **copia temporal de `datos.db`** con el cliente de pruebas:
  editar un hilo y un hecho actualiza el texto recortado y redirige a `#atencion`
  y `#datos`; un texto vacío no borra ni cambia; la ficha renderiza con los
  campos. La base real quedó intacta. `python mapa/comprobar.py` pasa. El mapa
  (`backend.md`, `pantallas.md`) se actualizó en el mismo cambio.
- Recursos: `estilo.css?v=20260819a`.

### 2026-08-19 — La red encaja en el móvil (auto-ajuste) y la ficha, debajo

En pantalla estrecha la red se salía por los lados en dos sitios distintos y,
además, ni al alejar al máximo entraba entera. Cada cosa tenía su causa:

- **Al enfocar un círculo o una persona**, el corro se recoloca en un anillo
  dibujado en **píxeles de pantalla** (`radioAnillo` + `animarFisica`). Con 13
  personas eran 235px de radio, o sea 470px de diámetro sobre una pantalla de
  375: cortado por los dos lados. Ahora, cuando `A < 720`, el tope del radio se
  acota al ancho (≈`A*0.30`, ~112px en un móvil) dejando aire para los nombres.
  Medido con datos reales: la persona de mayor grado (16) y el círculo de 13
  quedan en `[76, 299]`, con nombres holgados dentro de 375. En escritorio nada
  cambia.
- **La vista general** se proyecta en el mundo, no en pantalla. Un número fijo
  no vale porque depende de cuánta gente haya, así que se **calcula**:
  `camaraQueEncaja()` hace una búsqueda binaria de la distancia de cámara más
  pequeña que mete toda la red con margen para los nombres (`proyectarBounds(cz)`
  proyecta sin dejar rastro). Con los datos reales sale ~7200 y encaja en
  `[51, 329]`; encajaría igual con 12 o con 80 personas.
- **«Alejar al máximo» no llegaba a ver la red entera**: el tope estaba fijo en
  4500, por debajo de lo necesario. Ahora `topeZoom()` sube en móvil a
  `max(4500, camaraQueEncaja()*1.8)` (~13000 con estos datos); lo usan la rueda,
  los botones y el pellizco.
- **La ficha resumida se ponía encima de «Explorar la red».** Los mandos van
  arriba a la izquierda; la ficha arrancaba en `barra + 16` y los tapaba. Ahora
  arranca en `barra + 64` (por debajo de los mandos plegados, ~`barra + 56`) y
  con menos `z-index` que ellos, así que si se despliegan quedan por encima en
  vez de taparlos la ficha. Medido: mandos `top 64`/`bottom 106`, ficha
  `top 120`, 14px de hueco, sin solape. La causa de fondo era una maraña de
  reglas `.grafo-mandos`/`.grafo-ficha` de varias tandas: una regla base tardía
  reponía el `top` de escritorio. El `top` de los mandos se fija ahora en el
  último bloque `@media`, y el de la ficha en su regla «ficha flotante», que es
  la última de todas.
- **No se tocó la composición 3D ni las distancias base**: las mismas posiciones
  para todos los tamaños. Sólo cambia, según el ancho, cuánto se ve y el radio
  del anillo. En escritorio la red es idéntica.
- **Cómo se verificó, sin poder capturar pantalla:** el lienzo no compone frames
  en el navegador automatizado (se lee en negro, limitación ya conocida) y la
  extensión de Chrome no estaba conectada. Se expuso un hook temporal dentro de
  `grafo.js` que proyecta y devuelve los recuadros reales de nodos, corro y
  enfoque, se midió con los datos reales (encaje general, anillo de mayor grado y
  círculo mayor, posición de mandos y ficha) y se **retiró** al terminar. El
  ajuste fino queda a tu ojo en el móvil.
- El mapa (`interaccion.md`) se actualizó en el mismo cambio y
  `python mapa/comprobar.py` pasa. Recursos: `grafo.js?v=20260819d`,
  `estilo.css?v=20260819d`.

### 2026-08-24 — Descripción breve de cada persona y retirada del color

- `persona.notas_rapidas`, que estaba vacío en las 53 fichas reales, pasa a ser
  **Descripción breve**. Se puede escribir al añadir a alguien o editar su
  identidad y se muestra bajo nombre y círculo en la ficha completa, la ficha
  rápida de Personas y la ficha resumida de la Red.
- Notas también la enseña dentro de la identidad, tanto en la captura manual
  como en los borradores de voz, pero allí es fija: no se puede modificar al
  confirmar pendientes, preguntas, quedadas o datos.
- El límite queda en **cien caracteres**, aplicado con `maxlength` y de nuevo en
  el servidor. Se compararon visualmente ochenta, cien y ciento veinte: cien
  mantiene una descripción útil y no domina la ficha móvil de la Red.
- Se retiró *Su color* de la edición y del JSON de la Red. La columna histórica
  se conserva y editar otros datos no altera lo que ya tuviera guardado; no hubo
  migración ni pérdida de datos.
- Probado sobre una copia temporal de `datos.db`: alta y edición recortan a cien,
  el valor histórico de color permanece, las plantillas cargan y `/api/grafo`
  entrega la descripción sin color. Revisión visual en escritorio y 375×812 de
  ficha completa, Personas, Red, alta y Notas, sin errores de consola. La base
  real no se modificó y los temporales se retiraron.
- `python mapa/comprobar.py`, `py_compile`, `node --check` y `git diff --check`
  pasan. Recursos: `estilo.css?v=20260824a`, `app.js?v=20260824a` y
  `grafo.js?v=20260824a`.

### 2026-08-24 — Identidades alineadas y fotos mayores

- La ficha completa y los bloques de Notas comparten ahora foto de 96×96 y la
  misma fila de nombre, círculo y descripción. En Notas, *Descartar borrador*
  baja a una fila de acción equivalente a la edición de la ficha completa.
- Se quitó la frase «Sólo retira este borrador…»; la acción ya se entiende por
  su nombre y no necesita una segunda explicación permanente.
- La ficha rápida del archivador crece de 96×96 a 104×104. Se probaron 112 px,
  pero cortaban el nombre visible más largo en móvil; con 104 px y doce de
  relleno lateral, el nombre entra completo.
- El orden de esa ficha pasa a identidad → descripción → *Hablamos hace* y
  *Relaciones* → resto del contenido.
- Revisado visualmente con los datos reales copiados en escritorio y a 375×812:
  ficha completa, captura manual, archivador, descripción y nombre más largo,
  sin errores de consola. La base real no se modificó.
- Recurso: `estilo.css?v=20260824b`.
