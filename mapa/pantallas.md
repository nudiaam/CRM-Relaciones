# `plantillas/`

Jinja2 sin build. `base.html` monta la barra y carga los recursos; el resto
extiende de ella.

| Archivo | Ruta | Líneas |
| --- | --- | --- |
| `base.html` | todas | ~40 |
| `grafo.html` | `/` | ~59 |
| `personas.html` | `/personas` | ~180 |
| `ficha.html` | `/persona/{id}` | ~380 |
| `notas.html` | `/nota` | ~230 |
| `_audio_proceso.html` | incluida en `/nota` | ~230 |
| `nota.html` | `/nota/{id}` | ~130 |
| `_grabadora.html` | incluida | ~30 |
| `_audios_lista.html` | incluida | ~25 |
| `ajustes.html` | `/ajustes` | ~95 |
| `entrar.html` | `/entrar` | ~25 |

## `ficha.html` — la más grande

Dos macros arriba y luego un bloque por sección. **Cada sección es un
`<section class="bloque" data-bloque>`** con su cabecera plegable y, si se puede
editar, su botón *Editar*.

| Bloque | `id` | Ancla |
| --- | --- | --- |
| macro de cabecera | — | `{% macro cabecera(` |
| macro de línea de hilo | — | `{% macro hilo_linea(` |
| Identidad + edición de persona + foto | — | `bloque-identidad` |
| De un vistazo | `vistazo` | `cabecera("De un vistazo"` |
| Queda pendiente | `atencion` | `cabecera("Queda pendiente"` |
| Preguntar por | — | `cabecera("Preguntar por"` |
| Quedadas | `quedadas` | `cabecera("Quedadas"` |
| Datos | `datos` | `cabecera("Datos"` |
| Relaciones | `relaciones` | `cabecera("Relaciones"` |
| Cosas que ya están | — | `cabecera("Cosas que ya están"` |
| Zona peligrosa | — | `class="zona-peligrosa"` |

**Los `id` los usa `app.py` para redirigir.** Si renombras uno, mira
[backend.md](backend.md) § anclas de redirección.

### Reglas de la ficha

- En reposo, **ni un botón dentro del contenido**. Todo lo que escribe datos
  lleva `data-solo-edicion`.
- La navegación (páginas, enlaces a otra persona, *Sigue*) **no** lleva
  `data-solo-edicion`: no es edición.
- Los vacíos son una línea de serif en cursiva, no un panel.

## `personas.html`

Cabecera, bloque *Añadir persona* y el archivador de tres columnas: carpetas ·
lista · ficha rápida. El archivador se recarga por trozos desde `app.js`
bloque 10.

El paso 02 del alta tiene **dos maneras** de enlazar, y se pueden usar a la vez:

- **Filas sueltas** (`data-relacion-alta`), clonables, cada una con su persona y
  su par de etiquetas. Viajan como `otras[] / etiquetas[] / inversas[]`.
- **Enlazar con varias** (`data-enlazar-varias`): casillas, atajos por círculo y
  un solo par de etiquetas. Viaja como `varias[] / etiqueta_varias /
  inversa_varias`.

Si alguien sale en las dos, **manda la fila suelta**: el grupo se aplica después
y salta a quien ya está enlazado.

El mismo componente vive también en la ficha, dentro del bloque *Relaciones*,
apuntando a `/persona/{id}/relaciones`. Los dos comparten estilos y el bloque
9 quater de `app.js`, que recorre **todas** las instancias.

## `notas.html`

La pestaña **Notas** ordena la pantalla así: grabadora integrada arriba sólo en
móvil · audio activo opcional · captura manual · archivo de audios al final.
Sin una elección explícita no abre ningún bloque personal. El archivo empieza
plegado y se pagina de cinco en cinco sin crear una zona de scroll interna.

La captura elige personas existentes con el selector integrado. Cada elección
clona un formulario `.ficha` independiente: identidad y cuatro bloques con las
mismas `.bloque-cabecera` y `.bloque-cuerpo` de la ficha completa. Pendientes,
preguntas y datos son repetibles; la quedada es única y lleva día, resumen y
texto completo, además de *Por dónde*. Los cuatro bloques empiezan desplegados
y conservan su control individual de plegado. *Descartar borrador* sólo retira
ese formulario y lo explica junto al botón; nunca borra la persona ni
modifica su ficha. El análisis automático rellena exactamente esos mismos campos.
No se crea gente desde aquí.

En el borrador automático, *Preguntar por* contiene asuntos que completan el
rótulo («El viaje a Huelva»), no preguntas completas. El resumen se redacta
como un recuerdo natural y relativo; el texto extendido conserva las fechas y
los detalles exactos. El canal inferido sigue siendo editable antes de validar.

`_audio_proceso.html` se carga dentro del audio activo: estado, transcripción
plegada, borradores editables y acciones de revisión. *Editar* cambia a *Enviar
a Qwen*; *Volver a analizar* repite Whisper desde el original y se convierte
en un estado visible mientras trabaja. Cada bloque permite *Cambiar persona* o
*Descartar bloque*; descartar no guarda nada y cierra la revisión si no quedan
otros bloques pendientes. Una identidad dudosa aparece en rojo con ✓ y
selector alternativo. *Validar todo* confirma
sólo bloques completos y deja visibles los dudosos o incompletos.

`nota.html` queda sólo para `/nota/{id}`: editar una quedada existente, también
su resumen. Usa el control de fecha propio y conserva el respaldo `<noscript>`.

## Archivo de audios

`_audios_lista.html` es el contenido compartido por el final de Notas y la ruta
antigua `/audios`; `_audios_paginas.html` comparte sus flechas de paginación.
Sólo llegan a ambas plantillas filas cuyo archivo todavía existe. Enseña fecha natural,
estado del proceso, un botón *Escuchar* propio (sin control
nativo, lo mueve `voz.js`) y *Eliminar* manual con confirmación. La grabadora
vive en `_grabadora.html`: `base.html` la incluye flotante salvo en `/nota`,
donde `notas.html` la coloca arriba dentro del contenido.

## Palabras prohibidas en pantalla

`hilo` `hecho` `entorno` `tema` y cualquier término de base de datos. **Notas**
es ahora el nombre explícito de la pestaña; la tabla `nota` sigue llamándose
**Quedadas** cuando se habla de esos registros.
