# `estatico/estilo.css`

~4.500 líneas. Creció por capas fechadas, así que **una misma clase puede estar
definida varias veces**: manda la última. Antes de añadir una regla, comprueba
si ya existe más abajo.

## LA NORMA DE LOS DOS MODOS

Está escrita en el propio CSS, junto a las variables. Resumen:

1. **Superficie rellena** (cabecera de bloque, opción elegida, pestaña actual,
   botón sólido, fila señalada) → `var(--inverso-fondo)` y
   `var(--inverso-texto)`. **Nunca** `var(--tinta)` / `var(--papel)` crudos.
   En día son idénticos, pero en noche la tinta cruda es crema brillante y
   crea una caja que no pega con nada.
2. **Marca pequeña de tinta** (el cuadrado de las cabeceras, un filete, el
   punto de hoy) → `var(--tinta)`. Ahí «tinta» es el color del trazo y en
   noche debe ser crema.
3. Si una superficie rellena necesita retoque de noche, va **en su propia
   regla** con estas variables. La lista gigante de `html[data-modo="noche"]`
   (línea ~3658) es deuda antigua: **no crece**.
4. El rojo de borrar es `var(--alarma)` con `var(--alarma-texto)`, y sólo
   aparece al señalar. Ningún otro color entra.

Para comprobarlo: `node mapa/auditar_inverso.js`. Lista los estados invertidos
con tinta cruda; los únicos aceptables son los de la regla 2.

## `:hover` sólo con ratón

**Todo `:hover` vive dentro de un `@media (hover: hover)`.** En táctil el hover
se queda pegado tras el toque y deja los desplegables en blanco. Si añades una
regla de hover, envuélvela. `:focus-visible` va **fuera**, que hace falta con
teclado.

## Variables, línea 10

`--papel` `--tinta` `--secundario` `--filete-color` `--inverso-fondo`
`--inverso-texto` `--capa` `--alarma` `--alarma-texto` `--mono` `--lectura`
`--filete` `--barra` `--ancho`

`html[data-modo="noche"]` las redefine. `--capa` está declarada en `:root` como
`var(--papel)`: **ojo**, se calcula donde se declara, así que sólo funciona
porque `:root` es el `<html>` que lleva el modo.

## Secciones

| Sección | Línea |
| --- | --- |
| Variables y reset | 10 |
| Barra principal | 167 |
| Página y tipografía | 243 |
| Contenedores y cabeceras | 309 |
| Formularios y controles | 441 |
| Desplegables | 556 |
| Listas | 646 |
| Archivador de personas | 774 |
| Ficha (capas antiguas) | 1249 |
| Zona peligrosa | 1538 |
| Apuntar | 1585 |
| Ajustes | 1697 |
| Red | 1760 |
| Adaptación (media queries) | 1991 |
| Modo noche (lista antigua) | 3658 |
| **Ficha completa, capa vigente** | 3830 |
| Controles propios: círculo y fecha | 4243 |
| Móvil: ficha, filetes, plegado | 4472 |

## Componentes vigentes de la ficha

| Componente | Línea | Ancla |
| --- | --- | --- |
| Marco y bloques | 3830 | `.ficha {` |
| Cabecera rellena | 3842 | `.bloque-cabecera {` |
| Edición por bloque | 3929 | `data-edicion="no"` |
| Identidad | 3946 | `.bloque-identidad {` |
| De un vistazo | 4011 | `.vistazo {` |
| Líneas de contenido | 4056 | `.lineas {` |
| Rojo de borrar | 4104 | `.accion-eliminar:hover` |
| Quedadas | 4125 | `.bloque-cuerpo .quedada` |
| Relaciones | 4185 | `.bloque-cuerpo .relaciones-lista` |
| Círculo (radios) | 4243 | `.opciones {` |
| Fecha (atajos y calendario) | 4337 | `.fecha-atajos {` |

## Cabeceras de sección: quién lleva caja y quién no

| Dónde | Clase | ¿Caja rellena? |
| --- | --- | --- |
| Ficha expandida | `.bloque-cabecera` | **sí** |
| Ajustes | `.panel-cabecera` | **sí**, desde 2026-07-31 |
| Ficha compacta de la Red | `.ficha-mini-modulo > header` | no |
| Ficha rápida de Personas | `.archivo-*  header` | no |

Las dos compactas se probaron con caja y **se descartó**: cinco bandas en tan
poco alto pesaban demasiado. Además tiene una trampa: `estilo.css` pinta
`header > span:first-child` con `var(--tinta)` y el contador con el gris
secundario, así que sobre una banda de tinta el rótulo se vuelve invisible. Si
se retoma, hay que colorear **también esos dos hijos**, no sólo el contenedor.

## Trampas conocidas

- `.panel-cabecera` **es sólo de Ajustes** desde que la ficha pasó a
  `.bloque-*`. Está definida dos veces: la de arriba y otra más abajo, en la
  capa «Revisión amable», que es la que manda.
- `.apartado`, `.tarjeta-accion`, `.cosas`, `.dice`, `.aparte`,
  `.ficha-resumen` son **CSS muerto**: ninguna plantilla los usa desde el
  rediseño de la ficha del 2026-07-31.
- `.grafo-mandos button` alcanza también la barra de título de *Explorar la
  red*, porque es un `<button>`. Cualquier regla para esa barra necesita más
  especificidad.
- Bloque **captura por voz** al final del CSS. El botón flotante `.voz` va
  `position: fixed` abajo a la derecha, respetando la zona segura. Los cuadrados
  «rec» (`.voz-icono`, `.voz-punto`) se pintan con `background: currentColor`,
  no con `var(--tinta)` crudo, para no disparar la norma de los dos modos que
  comprueba `comprobar.py`. En `body.portada` el botón sube por encima de
  `.grafo-estado` para no solaparla.
- La **ficha flotante de la red** (`.grafo-ficha`) es una ventana con barra de
  título (`.grafo-ficha-titulo`, reutiliza `.ventana-titulo`) que dice «Ficha
  resumida» y lleva la × dentro. En móvil flota con márgenes de 16px a los lados
  y arriba, no de borde a borde; la altura se acota para no tapar la barra de
  estado. La barra de título es `sticky` mientras el contenido se desplaza.
