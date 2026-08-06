# Relaciones

Relaciones es una libreta privada para acordarte mejor de la gente que te
importa. Guarda a quién conoces, qué habéis hablado, qué quieres preguntarle la
próxima vez y qué cosas tienes pendientes con esa persona.

No es una red social ni una agenda de contactos. No envía tus datos a una nube,
no muestra publicidad y no necesita una cuenta. Está pensada para una sola
persona y guarda todo en su propio ordenador.

Por ejemplo, después de hablar con Laura puedes apuntar que:

- se muda en septiembre;
- quieres preguntarle cómo ha ido la mudanza;
- tienes que pasarle el contacto de una academia;
- la conversación fue por teléfono.

La próxima vez que abras su ficha tendrás ese contexto sin depender de tu
memoria.

## Por dónde empezar según quién seas

Este documento tiene tres partes. Ve directo a la tuya:

1. **[Qué es Relaciones](#1-qué-es-relaciones)** — si aún no conoces el producto.
2. **[Instalarla y usarla](#2-instalarla-y-usarla)** — la guía completa para
   ponerla en marcha, incluidos el móvil y las notas de voz.
3. **[Cómo funciona por dentro](#3-cómo-funciona-por-dentro)** — para personas
   técnicas.

---

# 1. Qué es Relaciones

## Qué puedes hacer

- Crear una ficha para cada persona, con nombre, foto y círculo: familia,
  amistades, trabajo, barrio…
- Guardar **Datos** que no caducan, como gustos, nombres importantes o
  información familiar.
- Separar lo que tú tienes que hacer en **Queda pendiente** de aquello por lo que
  quieres interesarte en **Preguntar por**.
- Apuntar **Quedadas** y conversaciones, con fecha, medio, resumen y texto
  completo.
- Indicar relaciones entre personas y explorarlas en una red visual.
- Grabar una nota de voz desde el móvil. Si instalas los componentes opcionales,
  Relaciones la transcribe y prepara un borrador para que lo revises.
- Usarla desde el móvil mediante una conexión privada con Tailscale.

El análisis de audio nunca confirma información por ti: siempre puedes cambiar,
corregir o descartar cada bloque antes de guardarlo en una ficha.

## Las cuatro pantallas

La aplicación se recorre con cuatro destinos siempre visibles:

- **Red**: la portada. Un mapa en tres dimensiones donde cada persona es un
  punto y las relaciones son líneas. Puedes girarlo, buscar a alguien y abrir su
  ficha resumida.
- **Personas**: un archivador. Los círculos funcionan como carpetas y a la
  derecha aparece una ficha rápida de cada persona. Desde aquí se dan de alta.
- **Notas**: donde apuntas una conversación, a mano o grabando una nota de voz.
- **Ajustes**: modo día/noche, administración de círculos y copia de todo.

Cada persona tiene además su **ficha completa**, con su identidad, lo que tienes
en marcha con ella, las quedadas, los datos y sus relaciones.

## Qué NO hace, a propósito

- No pone puntuaciones, porcentajes ni «salud de la relación» al lado de nadie.
- No manda recordatorios, notificaciones ni avisos de «hace mucho que no hablas».
- No tiene cuentas, contraseñas ni permisos.
- No llama a internet, ni a APIs ni a servicios externos.
- No importa los contactos de tu móvil.

Es una libreta sobre otras personas, no un panel de métricas ni un diario
personal.

---

# 2. Instalarla y usarla

Esta parte cubre, en orden:

- [Instalación sencilla en Windows](#instalación-sencilla-en-windows)
- [Primeros pasos](#primeros-pasos)
- [Notas de voz y análisis automático](#notas-de-voz-y-análisis-automático--opcional)
  *(opcional)*
- [Usarla desde el móvil](#usarla-desde-el-móvil--opcional) *(opcional)*
- [Tus datos, copias y actualizaciones](#tus-datos-copias-y-actualizaciones)
- [Problemas habituales](#problemas-habituales)
- [Privacidad](#privacidad)

## Instalación sencilla en Windows

Relaciones es una aplicación portátil. No tiene un asistente de instalación:
se guarda una carpeta completa en el ordenador y se abre con doble clic.

### Qué necesitas

- Windows 10 u 11.
- La carpeta de Relaciones, que debe contener al menos `Relaciones.exe`.
- Espacio adicional sólo si quieres analizar audios: los modelos ocupan varios
  gigabytes.

No necesitas instalar Python para usar `Relaciones.exe`.

### Paso a paso

1. Descarga o recibe la carpeta comprimida de Relaciones.
2. Descomprímela entera en un lugar fijo, por ejemplo:
   `Documentos\Relaciones`.
3. Abre la carpeta y haz doble clic en `Relaciones.exe`.

La primera apertura puede tardar un poco mientras Windows revisa el archivo. Si
Windows muestra *Windows protegió su PC*, continúa únicamente si la copia
procede de alguien en quien confías: pulsa **Más información** y después
**Ejecutar de todas formas**.

Al abrirse por primera vez, Relaciones crea automáticamente:

- `datos.db`, donde guarda las fichas, fotos y todo lo que apuntas;
- `audios\`, donde guarda las grabaciones originales.

Estos elementos deben permanecer junto a `Relaciones.exe`. Si mueves sólo el
ejecutable a otra carpeta, parecerá que tus datos han desaparecido porque se
abrirá una libreta nueva y vacía.

Si quieres tener un acceso en el escritorio, crea un **acceso directo** a
`Relaciones.exe`; no muevas el archivo original.

## Primeros pasos

1. Abre **Personas** y crea tu primera ficha.
2. En **Ajustes**, revisa los círculos iniciales y añade los que necesites.
3. Usa **Notas** para apuntar una conversación manualmente.
4. Vuelve a la ficha de esa persona para ver sus pendientes, preguntas, datos y
   quedadas.
5. Abre **Red** para explorar cómo se conectan las personas.

No hace falta rellenarlo todo. La aplicación funciona bien empezando con unas
pocas personas y apuntando sólo lo que realmente quieres recordar.

## Notas de voz y análisis automático — opcional

La aplicación funciona sin inteligencia artificial. Si no instalas esta parte,
puedes seguir usando todas las fichas y escribir las notas a mano.

Para convertir grabaciones en borradores necesitas dos componentes locales:

- **Whisper**, que transcribe la voz. Ya viene preparado dentro del ejecutable;
  el modelo `large-v3` se descarga la primera vez que se necesita.
- **Ollama con Qwen**, que ordena la transcripción por persona y propone qué
  guardar.

### Instalar Ollama y Qwen

1. Descarga el instalador oficial de
   [Ollama para Windows](https://ollama.com/download/windows) y ejecútalo.
2. Abre **Terminal** o **PowerShell** desde el menú Inicio.
3. Pega este comando y pulsa Intro:

   ```powershell
   ollama pull qwen3:14b
   ```

4. Espera a que termine la descarga y vuelve a abrir Relaciones.

Ollama se inicia como aplicación de Windows y queda disponible en segundo plano.
Si un audio no avanza, comprueba primero que Ollama esté abierto.

La primera transcripción también puede tardar bastante porque Whisper debe
descargar su modelo. Después, tanto Whisper como Qwen trabajan en el ordenador.
Una tarjeta gráfica compatible acelera el proceso, pero si no la hay Whisper
intenta trabajar con el procesador y será más lento.

Durante estas descargas iniciales sí hace falta conexión a internet. Una vez que
los modelos están instalados, Relaciones procesa las grabaciones localmente.

## Usarla desde el móvil — opcional

En el móvil no se copia la base de datos ni se instala una segunda aplicación.
El móvil abre la aplicación que sigue funcionando en el ordenador. Por eso el
ordenador debe estar encendido y Relaciones debe permanecer abierta.

La opción recomendada es **Tailscale Serve**: crea una dirección privada con
HTTPS para tus dispositivos. El HTTPS es necesario para que el navegador permita
usar el micrófono.

### Configuración

1. Instala [Tailscale en Windows](https://tailscale.com/download/windows) y en
   tu móvil.
2. Inicia sesión con la misma cuenta en ambos dispositivos.
3. Abre Relaciones en el ordenador.
4. Abre PowerShell y ejecuta:

   ```powershell
   tailscale serve --bg http://127.0.0.1:9765
   ```

5. Tailscale mostrará una dirección parecida a
   `https://mi-ordenador.…ts.net`. Ábrela en el móvil.
6. Desde el menú del navegador puedes elegir **Añadir a la pantalla de inicio**
   para abrir Relaciones como cualquier otra aplicación.

Si Tailscale pide autorizar HTTPS, abre el enlace que muestra y confirma la
configuración. Usa **Serve**, no **Funnel**: Funnel haría el servicio público,
mientras que Serve lo mantiene dentro de tu red privada.

Si aparece una pantalla pidiendo una llave, utiliza la llave entregada con tu
copia. Cuando la aplicación se inicia desde el código, esa llave aparece en la
ventana de comandos.

La configuración actual de Tailscale Serve puede consultarse con:

```powershell
tailscale serve status
```

## Tus datos, copias y actualizaciones

Tus datos están en dos lugares:

- `datos.db`: personas, fotos, relaciones y todo lo escrito;
- `audios\`: grabaciones originales.

La copia más sencilla y completa consiste en:

1. cerrar Relaciones;
2. copiar la carpeta entera a otro disco o ubicación segura.

En **Ajustes → Guardar una copia** también puedes obtener un archivo con la
información escrita. Para poder restaurar la aplicación tal como estaba,
incluidos los audios, conserva además una copia de la carpeta completa.

Para actualizar Relaciones:

1. cierra la aplicación;
2. guarda una copia de la carpeta;
3. sustituye únicamente `Relaciones.exe` por la nueva versión.

No reemplaces `datos.db` ni la carpeta `audios\`.

Para desinstalarla, cierra la aplicación y elimina su carpeta. Haz antes una
copia si quieres conservar la información. Ollama y Tailscale se desinstalan por
separado desde **Aplicaciones instaladas** de Windows.

## Problemas habituales

### No se abre ninguna ventana

- Espera unos segundos en la primera apertura.
- Comprueba si Windows está mostrando un aviso detrás de otra ventana.
- Si existe `relaciones-error.txt`, contiene información sobre el fallo.
- Relaciones usa siempre el puerto **9765**. Si otra aplicación lo está usando,
  Relaciones no arrancará hasta que ese puerto quede libre.

### Se abre vacía aunque ya tenía personas

Seguramente se ha movido `Relaciones.exe` sin `datos.db`. Cierra la
aplicación y vuelve a colocar el ejecutable junto a la base y la carpeta
`audios\`.

### El móvil no abre la aplicación

Comprueba, en este orden:

1. que el ordenador esté encendido;
2. que Relaciones siga abierta;
3. que Tailscale esté conectado en el ordenador y en el móvil;
4. que ambos usen la misma cuenta de Tailscale;
5. que `tailscale serve status` siga mostrando la dirección.

### El audio no se procesa

- Confirma que Ollama esté abierto.
- Ejecuta `ollama ls` y comprueba que aparece `qwen3:14b`.
- La primera transcripción puede estar descargando Whisper y tardar más.
- No cierres Relaciones mientras el audio está siendo procesado.

El audio original se conserva aunque falle el análisis, por lo que podrás
reintentarlo.

## Privacidad

- Relaciones no tiene usuarios, publicidad ni telemetría.
- Las fichas, fotos y grabaciones se guardan en tu ordenador.
- Whisper y Qwen procesan el contenido localmente.
- Tailscale conecta tus propios dispositivos mediante una red privada; no
  convierte Relaciones en una página pública.
- La aplicación no importa contactos del móvil ni comparte información con
  otras aplicaciones.

Instalar Ollama, Tailscale y los modelos requiere descargar archivos desde sus
sitios oficiales. Ese paso de instalación es independiente del uso normal de
Relaciones.

---

# 3. Cómo funciona por dentro

Para personas técnicas. Esta parte no es necesaria si utilizas `Relaciones.exe`.

## La pila

- **Python 3** sobre Windows. Todo el backend vive en un solo archivo, `app.py`,
  con **FastAPI** servido por **uvicorn**.
- `main.py` arranca uvicorn en un hilo demonio (`0.0.0.0`, puerto **9765** fijo)
  y abre una ventana **pywebview** contra `http://127.0.0.1:9765`. El puerto no
  se negocia: si está ocupado, la app avisa y no arranca.
- **SQLite** con el módulo `sqlite3` de la estándar, en `datos.db`, sin ORM. El
  esquema se crea al arrancar si no existe y las bases de versiones anteriores se
  ponen al día en `poner_al_dia()`, que es idempotente.
- **HTML, CSS y JavaScript planos**: sin frameworks, sin build, sin npm, sin CDN
  y sin fuentes remotas. La única tipografía es un `@font-face` local (Departure
  Mono, bajo SIL OFL).
- La estética es una interfaz pixelada de **un bit**: sólo papel y tinta, sin
  grises salvo un secundario para metadatos, filetes de 1px y tramas binarias.

Los formularios que escriben datos son `POST` + redirección 303. Las únicas
rutas que devuelven otra cosa son `GET /api/grafo` (JSON de la red) y `POST
/audio` (subida de una grabación).

## Nada sale a internet

La aplicación no llama a ninguna API, CDN ni telemetría. La transcripción de voz
(**faster-whisper**, modelo `large-v3`) y el análisis (**Ollama** con
`qwen3:14b`) corren en local. No hay usuarios, login ni contraseñas; la «llave de
red» sólo protege el acceso directo por IP, no es un sistema de cuentas.

## Arrancar desde el código

```powershell
git clone <dirección-del-proyecto>
cd Relaciones
python -m venv venv
& .\venv\Scripts\Activate.ps1
python -m pip install -r requisitos-paquete.txt
python main.py
```

Si existe una instalación válida de Python dentro de `venv\`, `main.py` se
relanza con ella automáticamente, para disponer de faster-whisper sin activar el
entorno a mano. Para ver la red con datos de mentira:

```powershell
python ejemplo.py          # mete 20 personas de prueba en seis círculos
python ejemplo.py --quitar # las saca
```

## Construir el ejecutable

```powershell
powershell -ExecutionPolicy Bypass -File .\construir.ps1
```

`construir.ps1` prepara dependencias aisladas, empaqueta con `Relaciones.spec`
(excluye Torch, TensorFlow y NumPy, que la app no usa) y deja `Relaciones.exe` en
la raíz del proyecto. Los modelos de IA no se empaquetan: siguen en sus almacenes
locales.

## El mapa del código

Antes de buscar nada a mano, mira la carpeta `mapa/`: cinco documentos
(`backend.md`, `pantallas.md`, `estilos.md`, `interaccion.md`, `decisiones.md`)
que dicen a qué archivo, sección y línea ir. `python mapa/comprobar.py` verifica
que el mapa siga siendo cierto y que se respeten las reglas de estilo. Si tocas
código, se actualiza el mapa en el mismo cambio.
