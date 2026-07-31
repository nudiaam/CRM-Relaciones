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

Cabecera, bloque *Añadir persona* (con relaciones iniciales clonables) y el
archivador de tres columnas: carpetas · lista · ficha rápida. El archivador se
recarga por trozos desde `app.js` bloque 10.

## `nota.html`

Recorrido lineal de tres pasos: qué ocurrió · cuándo y por dónde · con quién.
El paso 02 usa el **control de fecha propio**; el nativo queda en un `<noscript>`.

## Palabras prohibidas en pantalla

`hilo` `hecho` `nota` `entorno` `tema` y cualquier término de base de datos.
La tabla de equivalencias está en `CLAUDE.md`.
