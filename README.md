# Relaciones

App personal para cultivar relaciones. Corre en tu ordenador, guarda todo en
`datos.db` y **no habla con internet nunca**.

## Arrancar

En Windows, basta con hacer doble clic en `Relaciones.exe`. El ejecutable abre
la ventana sin PowerShell y guarda la información en el `datos.db` que tenga al
lado. Si se mueve a otra carpeta, hay que mover también `datos.db` para llevarse
los datos.

El archivo ronda los 29 MB porque es autónomo: lleva dentro Python, el servidor,
la ventana y el tratamiento de imágenes para que no haya que instalar nada. No
incluye un navegador completo; usa el WebView de Windows. El empaquetado excluye
NumPy, una integración opcional que la app no necesita.

Para arrancar desde el código:

La primera vez, instalar las dependencias:

```bash
pip install -r requisitos.txt
```

Después, siempre:

```bash
python main.py
```

Se abre una ventana de escritorio. En la consola verás algo así:

```
Relaciones
  Ventana y ordenador:  http://127.0.0.1:9765
  Desde el móvil:       http://192.168.1.42:9765
  Llave para entrar desde la red: 3f9c1a8b
```

El puerto es siempre el 9765 y no cambia nunca: así la dirección que guardes en
el móvil sigue valiendo mañana. Si está ocupado, la app te lo dice y no arranca,
en vez de moverse a otro puerto a tus espaldas. Se eligió lejos de los puertos
donde trabajas con otras cosas (8188, por ejemplo): la app no toca nada por
debajo del 9765. La base de datos se crea sola la primera vez, con los círculos
Amigos, Familia, Trabajo y Barrio.

## Entrar desde el móvil

Con el ordenador encendido y `main.py` corriendo, en el móvil (misma wifi) abre
la dirección `http://<la IP que sale en consola>:<puerto>`. Te pedirá la llave
una vez y se queda guardada en una cookie de un año.

La llave no es un sistema de usuarios: no hay cuentas, ni registro, ni
contraseñas. Es una llave para que un dispositivo cualquiera de tu wifi no entre
sin más. Se genera aleatoria la primera vez, se guarda en `datos.db` y se imprime
en cada arranque. La ventana del ordenador (127.0.0.1) entra siempre sin nada.

Si quieres cambiarla:

```bash
python -c "import sqlite3,secrets; c=sqlite3.connect('datos.db'); c.execute('UPDATE ajuste SET valor=? WHERE clave=\"llave\"',(secrets.token_hex(4),)); c.commit()"
```

## Atajos

- `N` en cualquier pantalla: apuntar algo.
- `Ctrl + Enter` dentro del texto de una quedada: guardar.
- Enter en los campos de una línea (añadir una persona, un dato, un círculo): guardar.
- Botón **Noche** en Ajustes: alterna día y noche. Se recuerda en el aparato, no
  en la base de datos, así que el móvil y la ventana pueden ir distintos.

## La portada es la red

`/` sirve el lienzo a pantalla completa que dibuja `estatico/grafo.js`: la red en
3D, nítida, sin anillos y con la ficha flotante al señalar a alguien. Los
círculos se exploran desde los cuadrados del panel. Arrastrar desplaza la vista
dentro de un límite con el botón derecho o central; el izquierdo gira y la
rueda controla el zoom.
Se abre siempre ahí, aunque la base esté vacía.
La app sólo pone el JSON, `GET /api/grafo`, con la forma que lee tu `grafo.js`:

```json
{
  "generado": "2026-07-25T22:10:02",
  "circulos": [{"id": 1, "nombre": "Amigos", "orden": 0}],
  "personas": [{"id": 3, "nombre": "Marta Ruiz", "color": "#C2452D",
                "circulo_id": 1, "circulo": "Amigos",
                "notas": 12, "ultima_nota": "2026-07-22", "hablamos": "tres días",
                "pendiente": ["Devolverle el libro"],
                "preguntar": ["Se examina en octubre"],
                "quedadas": [{"cuando": "22 jul", "canal": "en persona",
                              "texto": "Café en la plaza…"}],
                "relaciones": [{"id": 8, "nombre": "Javi Alonso",
                                "etiqueta": "su pareja"}]}],
  "aristas":  [{"a": "p3", "b": "p8", "tipo": "persona"}]
}
```

Los ids de `aristas` van prefijados con `p`. Las aristas juntan dos cosas sin
distinguirlas: las que has enlazado a mano y las que salen de haber apuntado a
dos personas en la misma quedada. `pendiente` y `preguntar` son como mucho tres
cada una, y `quedadas` dos, con el texto cortado: es lo que cabe en la ficha
flotante. `hablamos` viene ya dicho en palabras. `notas` es cuántas veces has
apuntado algo de esa persona, que es lo que da tamaño a su punto. Si alguien no
tiene color, `color` viene vacío.

## Copia de seguridad

**Guardar una copia de todo**, en Ajustes, descarga un JSON con la base de datos
entera. La llave de red no se exporta. También puedes copiar `datos.db` tal cual
(si la app está abierta, copia además `datos.db-wal`).

## Los archivos

| Archivo | Qué es |
| --- | --- |
| `main.py` | Arranque: servidor en un hilo + ventana pywebview |
| `app.py` | Todo el backend: base de datos y rutas |
| `plantillas/` | HTML (Jinja2) |
| `estatico/estilo.css` | Todo el CSS, hoja v4: documento técnico monocromo |
| `estatico/app.js` | El JS de la app, todo opcional |
| estatico/grafo.js | La red de la portada, nítida |
| `estatico/tipos/` | Departure Mono, cargada con @font-face local |
| `ejemplo.py` | 20 personas de mentira para ver la red (`--quitar` las saca) |
| `datos.db` | Tus datos |
| `temas-borrados-2026-07-25.json` | Los temas que había antes de quitarlos |
| `para-code-2.md`, `contrato-marcado.md` | Encargos viejos, ya recogidos en `CLAUDE.md` |
| `CLAUDE.md` | Modelo de datos y lo que no se debe construir |
