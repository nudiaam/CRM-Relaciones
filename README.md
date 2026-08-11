<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="img/Logo-Blanco_SF.png">
    <source media="(prefers-color-scheme: light)" srcset="img/Logo-Negro_SF.png">
    <img src="img/Logo-Negro_SF.png" alt="Símbolo de Relaciones" width="220">
  </picture>
</p>

<h1 align="center">Relaciones</h1>

<p align="center">
</p>

Relaciones reúne en un solo lugar lo que quieres conservar de cada persona:
qué habéis hablado, qué quieres preguntarle la próxima vez, qué tienes pendiente
con ella y cómo se relaciona con el resto de tu entorno.

Está pensada para **una sola persona**, funciona en **Windows** y guarda la
información en el propio ordenador. No tiene publicidad, cuentas ni
telemetría.

Por ejemplo, después de hablar con Laura puedes apuntar que se muda en
septiembre, que quieres preguntarle cómo fue la mudanza y que tienes que pasarle
el contacto de una academia. La próxima vez que abras su ficha tendrás ese
contexto sin depender de tu memoria.

## Dos recorridos, un solo README

No hace falta leer esta página entera. Las instrucciones están separadas por
tipo de lector, pero viven en el mismo documento para no repetir información
sobre privacidad, requisitos y copias.

| Quiero… | Ir a… |
| --- | --- |
| Entender e instalar la aplicación sin programar | [Guía para usar Relaciones](#guía-para-usar-relaciones) |
| Ejecutar, revisar o empaquetar el código | [Apéndice para personas técnicas](#apéndice-para-personas-técnicas) |

## Qué puedes hacer

- Crear una ficha para cada persona, con nombre, foto y círculo: familia,
  amistades, trabajo, barrio…
- Guardar **Datos** que no caducan, como gustos, nombres importantes o
  información familiar.
- Separar **Queda pendiente**, lo que tú tienes que hacer, de **Preguntar por**,
  aquello de su vida por lo que quieres interesarte.
- Apuntar **Quedadas** y conversaciones con fecha, medio, resumen y texto
  completo.
- Indicar relaciones entre personas y recorrerlas en una red visual en tres
  dimensiones.
- Escribir una nota manual o, de forma opcional, grabarla desde el móvil para
  obtener un borrador automático que siempre revisas antes de guardar.

## Cómo se recorre

- **Red** es la portada: permite explorar conexiones, buscar a alguien y abrir
  su ficha resumida.
- **Personas** organiza las fichas en círculos y permite dar de alta a alguien.
- **Notas** sirve para apuntar una conversación a mano o revisar una grabación.
- La **ficha de una persona** reúne lo que sigue en marcha, las quedadas, los
  datos y sus relaciones.
- **Ajustes** contiene el modo día/noche, la organización de los círculos y la
  copia de los datos.

## Lo que no hace, a propósito

- No puntúa relaciones ni calcula porcentajes, rachas o estadísticas.
- No envía recordatorios, notificaciones ni avisos de frecuencia de contacto.
- No importa la agenda del móvil.
- No necesita una cuenta para el uso local.
- No sube fichas, fotos, notas o grabaciones a un servicio externo.

Es una libreta sobre otras personas, no un panel de métricas ni un diario
personal.

---

## Guía para usar Relaciones

### Antes de descargar

> [!IMPORTANT]
> El botón verde **Code → Download ZIP** de GitHub descarga el código fuente,
> no una aplicación lista para abrir. Para usar Relaciones sin programar hace
> falta una carpeta portátil que contenga `Relaciones.exe`.

Cuando haya una carpeta portátil publicada, aparecerá en la sección
**[Releases](https://github.com/nudiaam/CRM-Relaciones/releases)** del proyecto.
Si allí no hay un archivo para Windows, el repositorio ofrece por ahora sólo el
código y tendrás que pedir una copia preparada a quien mantiene la aplicación o
seguir el [apéndice técnico](#apéndice-para-personas-técnicas).

### Requisitos

- Windows 10 u 11.
- Una carpeta portátil de Relaciones o Python 3 si vas a arrancarla desde el
  código.
- Espacio adicional de varios gigabytes sólo si quieres analizar grabaciones.

No necesitas una tarjeta gráfica dedicada para escribir y consultar fichas.
Para el análisis de voz, una tarjeta compatible acelera el proceso; si no la
hay, la transcripción intenta usar el procesador y puede tardar bastante más.

### Instalación sencilla en Windows

Relaciones es portátil: no tiene un asistente de instalación y no dispersa tus
datos por el ordenador.

1. Descarga o recibe la carpeta comprimida que contiene `Relaciones.exe`.
2. Descomprímela entera en un lugar fijo, por ejemplo
   `Documentos\Relaciones`.
3. Abre esa carpeta y haz doble clic en `Relaciones.exe`.

Si Windows muestra *Windows protegió su PC*, continúa sólo si la copia procede
de este proyecto o de alguien en quien confías. Pulsa **Más información** y,
después, **Ejecutar de todas formas**.

En la primera apertura se crean junto a la aplicación:

- `datos.db`, con las personas, fotos, relaciones y todo lo escrito;
- `audios\`, con las grabaciones originales.

Mantén la carpeta unida. Si mueves solamente `Relaciones.exe`, la aplicación
creará una libreta nueva y parecerá que tus datos han desaparecido. Para tenerla
en el escritorio, crea un **acceso directo** al ejecutable en lugar de moverlo.

### Primeros pasos

1. Entra en **Personas** y crea tu primera ficha.
2. Abre **Ajustes** para revisar los círculos iniciales y añadir los tuyos.
3. Usa **Notas** para apuntar una conversación.
4. Vuelve a la ficha de esa persona para comprobar qué ha quedado pendiente,
   qué quieres preguntarle, sus datos y vuestras quedadas.
5. Regresa a **Red** para explorar las conexiones.

No hace falta rellenarlo todo desde el principio. Puedes empezar con unas pocas
personas y guardar sólo lo que de verdad quieras recordar.

### Notas de voz y análisis automático — opcional

La aplicación funciona sin inteligencia artificial: todas las fichas y notas
se pueden escribir a mano. El análisis automático sólo convierte una grabación
en un borrador editable.

Para usarlo hacen falta dos componentes que trabajan en el ordenador:

- **Whisper** transcribe la voz. El modelo `large-v3` se descarga la primera vez
  que se necesita.
- **Ollama con Qwen** ordena la transcripción por persona y propone qué guardar.

#### Preparar Ollama y Qwen

1. Instala
   **[Ollama para Windows](https://ollama.com/download/windows)**.
2. Abre **Terminal** o **PowerShell** desde el menú Inicio.
3. Pega este comando y pulsa Intro:

   ```powershell
   ollama pull qwen3:14b
   ```

4. Espera a que termine y comprueba que Ollama sigue abierto en segundo plano.

Las primeras descargas requieren internet y ocupan varios gigabytes. Después,
Whisper y Qwen procesan el contenido en el ordenador: Relaciones no envía la
grabación a una API externa.

Cada persona detectada aparece como un bloque revisable. Puedes corregirlo,
cambiar la persona o descartarlo; nada se incorpora a una ficha sin tu
confirmación.

### Usarla desde el móvil — opcional

El móvil no guarda otra copia de la aplicación ni de la base de datos: abre la
que sigue funcionando en el ordenador. Por eso el ordenador debe estar
encendido y Relaciones debe permanecer abierta.

La opción prevista es **Tailscale Serve**, que crea una dirección privada con
HTTPS entre tus propios dispositivos. Ese HTTPS permite que el navegador del
móvil use el micrófono.

1. Instala [Tailscale](https://tailscale.com/download/windows) en el ordenador y
   en el móvil e inicia sesión con la misma cuenta.
2. Abre Relaciones en el ordenador.
3. Abre PowerShell y ejecuta:

   ```powershell
   tailscale serve --bg http://127.0.0.1:9765
   ```

4. Abre en el móvil la dirección `https://…ts.net` que muestre Tailscale.
5. Si quieres, usa **Añadir a la pantalla de inicio** desde el navegador.

Usa **Serve**, nunca **Funnel**: Serve mantiene el acceso dentro de tu red
privada y Funnel lo haría público. Puedes consultar la configuración con
`tailscale serve status`.

Al entrar desde otro aparato, Relaciones pide una llave de red una vez. Si la
aplicación se inicia desde el código, la llave aparece en la ventana de
comandos; en una carpeta portátil preparada para otra persona, quien la haya
creado debe entregarla junto con la aplicación.

### Tus datos y las copias

La opción **Ajustes → Guardar copia** descarga todo lo escrito, incluidas las
fotos, en un archivo JSON. La llave de red y las grabaciones originales no se
incluyen.

Para conservar absolutamente todo:

1. cierra Relaciones;
2. copia la carpeta completa a otro disco o ubicación segura.

Esa copia debe incluir `datos.db` y `audios\`. No subas ninguno de los dos a un
repositorio público: contienen información personal.

Antes de actualizar, guarda una copia de la carpeta. Después sustituye sólo
`Relaciones.exe`; no reemplaces `datos.db` ni `audios\`.

Para desinstalar Relaciones, cierra la aplicación y elimina su carpeta. Haz una
copia antes si quieres conservar la información. Ollama y Tailscale se
desinstalan por separado desde **Aplicaciones instaladas** de Windows.

### Problemas habituales

#### No aparece ninguna ventana

- Espera unos segundos durante la primera apertura.
- Comprueba si Windows ha dejado un aviso detrás de otra ventana.
- Si existe `relaciones-error.txt`, contiene los detalles del fallo.
- Relaciones usa siempre el puerto `9765`. Si otra aplicación lo ocupa, no
  arrancará hasta que el puerto quede libre.

#### La aplicación aparece vacía

Comprueba que `Relaciones.exe` siga junto al `datos.db` que estabas usando. Una
copia del ejecutable en otra carpeta crea una base nueva.

#### Una grabación no avanza

- Comprueba que Ollama esté abierto.
- Ejecuta `ollama ls` y confirma que aparece `qwen3:14b`.
- La primera transcripción puede seguir descargando Whisper.
- Mantén Relaciones abierta mientras se procesa el audio.

El archivo original se conserva aunque falle el análisis y puede volver a
intentarse.

### Privacidad, en claro

- La base, las fotos y los audios se guardan en tu ordenador.
- No hay publicidad, analítica ni telemetría.
- La aplicación no llama a APIs, CDN ni servicios de inteligencia artificial
  externos.
- Ollama y Whisper trabajan localmente una vez descargados.
- La instalación de dependencias y modelos sí necesita descargarlos de sus
  sitios oficiales.
- Tailscale es opcional y sólo interviene si decides conectar el móvil.

---

## Apéndice para personas técnicas

Esta parte no es necesaria para utilizar una carpeta portátil con
`Relaciones.exe`.

### Arrancar desde el código

```powershell
git clone https://github.com/nudiaam/CRM-Relaciones.git
cd CRM-Relaciones
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requisitos-paquete.txt
.\venv\Scripts\python.exe .\main.py
```

Después de la primera preparación también se puede abrir `Relaciones.bat` con
doble clic.

La aplicación escucha en `0.0.0.0:9765`. El puerto es fijo: si ya está ocupado,
el arranque muestra un error y no busca otro.

### Arquitectura

- Python 3, FastAPI y uvicorn; el backend vive en `app.py`.
- pywebview abre la interfaz como una ventana de escritorio desde `main.py`.
- SQLite mediante la biblioteca estándar, sin ORM; los datos viven en
  `datos.db`.
- HTML, CSS y JavaScript planos, sin npm, CDN ni fuentes remotas.
- faster-whisper `large-v3` para transcripción y Ollama `qwen3:14b` para el
  borrador local.

Antes de buscar código a mano, consulta el **[mapa del
proyecto](mapa/README.md)**. Sus documentos señalan las rutas, pantallas,
interacciones, estilos y decisiones relevantes. Para comprobarlo:

```powershell
python mapa/comprobar.py
```

### Datos de prueba

```powershell
python ejemplo.py
python ejemplo.py --quitar
```

El primer comando añade personas ficticias y el segundo las retira. No lo uses
sobre una base real sin saber exactamente qué va a cambiar.

### Construir la carpeta portátil

```powershell
powershell -ExecutionPolicy Bypass -File .\construir.ps1
```

El proceso usa PyInstaller y deja `Relaciones.exe` en la raíz. El ejecutable,
`datos.db` y `audios\` están excluidos del control de versiones; una publicación
para personas no técnicas debe empaquetar el ejecutable en un ZIP separado y
adjuntarlo a una Release.

### Licencia

Relaciones se publica bajo la [licencia MIT](LICENSE).
