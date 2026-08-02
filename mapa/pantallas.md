# `plantillas/`

Jinja2 sin build. `base.html` monta la barra y carga los recursos; el resto
extiende de ella.

| Archivo | Ruta | Líneas |
| --- | --- | --- |
| `base.html` | todas | ~40 |
| `grafo.html` | `/` | ~59 |
| `personas.html` | `/personas` | ~180 |
| `ficha.html` | `/persona/{id}` | ~380 |
| `nota.html` | `/nota`, `/nota/{id}` | ~130 |
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

## `nota.html`

Recorrido lineal de tres pasos: qué ocurrió · cuándo y por dónde · con quién.
El paso 02 usa el **control de fecha propio**; el nativo queda en un `<noscript>`.

## `/audios` (dentro de Apuntar)

`audios.html`. La lista de audios grabados por voz: fecha en lenguaje natural,
estado (siempre *Pendiente* de momento), un botón *Escuchar* propio (sin control
nativo, lo mueve `voz.js`) y *Eliminar* manual con confirmación. Se llega desde
el enlace *Apuntar por voz* de la cabecera de `/nota`. El botón flotante de
grabar no vive aquí: está en `base.html` y sale en todas las pantallas.

## Palabras prohibidas en pantalla

`hilo` `hecho` `nota` `entorno` `tema` y cualquier término de base de datos.
La tabla de equivalencias está en `CLAUDE.md`.
