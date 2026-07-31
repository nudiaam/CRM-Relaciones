# Mapa del código

Estos archivos existen para **no tener que leer 5.000 líneas** cada vez que hay
que tocar algo. Dicen a qué archivo, a qué sección y a qué línea aproximada ir.

| Archivo | Para qué |
| --- | --- |
| [backend.md](backend.md) | `app.py` y `main.py`: rutas, consultas, filtros, arranque |
| [pantallas.md](pantallas.md) | las plantillas: qué bloque vive en cuál |
| [estilos.md](estilos.md) | `estilo.css` por secciones, y **la norma de los dos modos** |
| [interaccion.md](interaccion.md) | `app.js` y `grafo.js`: qué hace cada bloque numerado |
| [decisiones.md](decisiones.md) | por qué las cosas son como son, y qué NO se construye |

## Cómo mantenerlos

**Los números de línea envejecen.** Por eso cada entrada lleva también un
**ancla de texto**: una cadena que se puede buscar con `grep` y que no cambia
aunque el archivo crezca. Si el número no cuadra, busca el ancla.

Después de cualquier cambio que mueva bloques de sitio, añada rutas o cree
componentes, hay que actualizar el mapa correspondiente **en el mismo cambio**,
igual que se actualiza el registro de `CLAUDE.md`.

Para refrescar los números de línea de golpe:

```bash
python mapa/comprobar.py
```

Ese script no reescribe nada: recorre las anclas, dice en qué línea está cada
una ahora y avisa de las que ya no existen.
