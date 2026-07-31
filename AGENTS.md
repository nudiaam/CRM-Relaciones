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
   carpetas, la columna central enseña hasta cinco personas por página y la
   derecha ofrece una ficha rápida. Las flechas cambian de página sin apilar
   toda la lista. Carpeta, persona, página y búsqueda cambian sólo el archivador
   mediante JavaScript: no recargan la pantalla, no usan el ancla y conservan la
   posición exacta; los enlaces y el formulario HTML siguen siendo el respaldo.
   En móvil se recorre carpeta, persona y ficha por pasos. El alta permite
   indicar nombre, apodo, círculo y varias relaciones iniciales. La
   administración de círculos no vive aquí.
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

- En día mandan papel `#f4efe1` y tinta `#14120f`. La noche no los invierte de
  forma literal: usa carbón cálido `#23241f`, crema apagada `#ddd6c6`, una capa
  `#2b2c27`, selecciones `#3a3b35` y filetes `#706d64`. Un gris secundario se
  reserva para metadatos como el círculo, los recuentos y el papel de una
  relación. Así se conserva la interfaz 1-bit sin grandes fogonazos claros. El
  color guardado de una persona sigue siendo un dato editable.
- Departure Mono se incluye localmente en `estatico/tipos/` bajo SIL OFL. Se usa
  a 11px para navegación, controles y rótulos. El texto largo usa serif a 16px.
- Títulos personales a 33px. Cuerpo a 16px. Interfaz a 11px.
- Filetes nítidos de 1px, esquinas rectas, selecciones por inversión de tinta y
  tramas binarias. El gris secundario nunca sustituye a la tinta en títulos,
  cuerpo principal, controles ni filetes.
- Las secciones se separan con aire, filete y un pequeño cuadrado de tinta.
  Las bandas negras se reservan para acciones o estados seleccionados; no se
  repiten como cabecera de todos los paneles. **Única excepción**: en la ficha
  completa (`/persona/{id}`) cada bloque sí lleva su cabecera rellena. Fuera de
  esa pantalla la regla sigue entera.
- **Toda superficie rellena usa `var(--inverso-fondo)` y `var(--inverso-texto)`,
  nunca tinta y papel crudos**: en noche la tinta cruda es crema y produce una
  caja brillante. Las marcas pequeñas —cuadrado, filete, punto— sí usan
  `var(--tinta)`.
- **Todo `:hover` vive dentro de un `@media (hover: hover)`**, o en táctil se
  queda pegado tras el toque. `:focus-visible` va fuera.
- El único color de la interfaz es `--alarma`, un rojo rebajado que aparece sólo
  al señalar con el ratón un botón que borra.
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
- *En marcha* permite completar o eliminar; las relaciones permiten editar o
  eliminar. Todo borrado pide confirmación y regresa a su sección.
- El nombre habitual lleva su círculo debajo en listas y selecciones. Cuando
  hay apodo, la ficha muestra el nombre completo debajo como subtítulo.
- Las fichas compactas no repiten «Ficha rápida» ni «Persona seleccionada»: la
  identidad ya explica el contexto. Sus rótulos de sección van a 11px, con un
  pequeño cuadrado, y el contenido vuelve a serif con más tamaño y separación.
- En las relaciones compactas, nombre y papel usan Departure Mono; el papel
  conserva el gris secundario y un punto menos para leerse como metadato.
- En la ficha completa, `PERSONA / 0000` queda encima de la fila de identidad.
  Foto, nombre y círculo forman debajo un único bloque centrado verticalmente.

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
  conexiones. Siempre usan el nombre habitual si existe y se dibujan sueltos,
  en Departure a 11px: no llevan foto, fondo ni caja.
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
  pendiente, preguntar por, datos, vistas previas compactas de quedadas y
  relaciones, y botones para apuntar o abrir la ficha. En escritorio no crea
  una barra de desplazamiento exterior.
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

Antes de buscar nada a mano, mira `mapa/`: dice a qué archivo, sección y línea
ir, con anclas de texto que no envejecen. `python mapa/comprobar.py` verifica
que el mapa siga siendo cierto y que se cumplan las normas de estilo. Si se toca
código, se actualiza el mapa en el mismo cambio.

## Cómo trabajar aquí

Un cambio cada vez. No reescribir archivos enteros para tocar una función.
Antes de añadir cualquier cosa que no esté en el encargo, preguntar. Avisar
siempre de los datos que se van a perder antes de tocar la base.

Una acción dentro de la misma pantalla **nunca puede mandar la página arriba**.
Los formularios y enlaces que recargan la ruta conservan la posición; cuando el
destino es una parte concreta, se usa un ancla explícita. Esta regla se aplica a
toda la app, no sólo a Personas.

Después de cualquier cambio, añadir una entrada fechada al registro de
`CLAUDE.md`. Ese archivo es la memoria de cambios del proyecto.

`python ejemplo.py` mete 20 personas de mentira en seis círculos para ver la red
con algo dentro, y `python ejemplo.py --quitar` las saca. Si ya están, no hace
nada: primero hay que quitarlas.
