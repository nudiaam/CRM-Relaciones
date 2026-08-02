# Relaciones

Una agenda personal de relaciones. Un CRM privado para tu vida, no para el trabajo:
guarda quién es cada persona que te importa, qué habéis hablado, qué quedó
pendiente y cuándo fue la última vez que coincidisteis. Todo vive en tu propio
ordenador; nada sale a la nube.

La idea de fondo: en lugar de fiarlo todo a la memoria, apuntas las cosas —a mano
o dictando un audio desde el móvil— y la aplicación las organiza por persona, con
una vista de red que muestra cómo se relacionan entre sí.

---

## Qué hace

- **Fichas de personas.** Cada persona tiene su ficha: datos, círculo (familia,
  amigos, trabajo…), foto, lo que tenéis pendiente, lo que quieres preguntarle y
  el histórico de quedadas.
- **Vista de red.** Un grafo que dibuja a las personas y sus relaciones, navegable
  con el dedo en el móvil.
- **Apuntar por voz.** Grabas un audio desde el móvil y la aplicación lo transcribe
  y propone qué apuntar, para que tú lo confirmes. *(En construcción — ver más abajo.)*
- **Acceso desde el móvil** a través de una red privada (Tailscale), sin abrir el
  ordenador a internet.
- **Privado por diseño.** La base de datos y los audios se quedan en tu máquina.
  El repositorio nunca los incluye.

---

## Cómo está construido

| Pieza | Tecnología |
|---|---|
| Servidor | Python + FastAPI |
| Ventana de escritorio | pywebview |
| Base de datos | SQLite (un solo archivo, `datos.db`) |
| Interfaz | HTML + CSS + JavaScript, sin framework |
| Acceso remoto | Tailscale (red privada entre tus dispositivos) |
| Transcripción de audio | faster-whisper (modelo Whisper large-v3), local |
| Análisis de texto | Ollama + Qwen3, local |

Todo el procesamiento —incluida la voz y la IA— ocurre en tu ordenador. No se
llama a ningún servicio externo.

---

## Requisitos

- **Windows** (probado en Windows 11).
- **Python 3.11.**
- Para la parte de audio con aceleración por GPU: una **tarjeta NVIDIA**. El
  proyecto se ha montado sobre una RTX 5090 (arquitectura Blackwell), que necesita
  una versión concreta de PyTorch — ver más abajo.
- **Tailscale**, si quieres acceder desde el móvil.

> La parte de audio (Whisper + Ollama) es opcional. La aplicación funciona sin ella;
> simplemente no tendrás el "apuntar por voz".

---

## Instalación

### 1. Clonar el proyecto

```
git clone <url-del-repositorio>
cd Relaciones
```

### 2. Crear el entorno virtual

Aísla las dependencias del proyecto del Python del sistema.

```
python -m venv venv
```

Activarlo:

- En **CMD**: `venv\Scripts\activate.bat`
- En **PowerShell**: `& .\venv\Scripts\Activate.ps1`
  *(si PowerShell bloquea el script, ejecuta antes `Set-ExecutionPolicy -Scope Process -Bypass`)*

Sabrás que está activo porque la línea de comandos empieza por `(venv)`.

### 3. Instalar las dependencias

```
pip install -r requisitos.txt
```

### 4. Arrancar

```
python main.py
```

Se abrirá la ventana de escritorio y, en la propia terminal, verás las direcciones
de acceso y la llave para entrar desde la red.

La aplicación escucha siempre en el **puerto 9765**. Si ese puerto está ocupado,
avisa y no arranca (no busca otro puerto), para no romper el acceso configurado
desde el móvil.

---

## Acceso desde el móvil

La aplicación se sirve a sí misma; en el móvil no se instala nada, solo se abre en
el navegador.

1. Instala **Tailscale** en el ordenador y en el móvil, y entra con la **misma
   cuenta** en los dos. Esto crea una red privada entre ellos.
2. En el ordenador, deja la aplicación arrancada.
3. Activa `tailscale serve` sobre el puerto 9765 para obtener una dirección segura
   (`https://…ts.net`). El HTTPS es **imprescindible** para poder usar el micrófono
   desde el navegador.
4. Abre esa dirección `https://…ts.net` en el móvil. La primera vez pedirá la
   **llave de acceso** (se muestra al arrancar la aplicación); luego la recuerda.

Desde ahí puedes **añadir la aplicación a la pantalla de inicio** (es una PWA): se
abre a pantalla completa, como una app normal.

> **Nota sobre la dirección de Tailscale:** conviene apuntar cuál es tu dirección
> `…ts.net`, porque es la que usa el acceso instalado en el móvil.

---

## La parte de audio (opcional)

Esta es la funcionalidad de "apuntar por voz". Requiere instalar dos motores que
corren en local. **Se instalan una vez.**

### Whisper (transcripción)

Con el entorno virtual activado:

1. **PyTorch con CUDA.** Para tarjetas Blackwell (serie RTX 50xx) hace falta la
   build de CUDA 12.8, no la estándar:
   ```
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   ```
   Comprobar que la GPU se detecta, sin ningún aviso de incompatibilidad:
   ```
   python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
   ```
2. **faster-whisper:**
   ```
   pip install faster-whisper
   ```
   La primera transcripción descarga el modelo `large-v3` (unos 3 GB); queda
   cacheado para siempre.

Dos ajustes importantes con los que se configura la transcripción:

- **Filtro de voz (VAD) activado:** recorta los silencios antes de transcribir, lo
  que evita que Whisper "alucine" frases inventadas en las pausas.
- **Contexto de nombres:** se le pasa la lista de personas de la base de datos para
  que acierte con los nombres propios. Esta lista se genera automáticamente desde
  la base; no se mantiene a mano.

### Ollama (análisis del texto)

1. Instalar **Ollama** desde [ollama.com/download](https://ollama.com/download).
   Corre en segundo plano.
2. Descargar el modelo:
   ```
   ollama pull qwen3:14b
   ```

El texto transcrito se le pasa a este modelo, que propone qué apuntar y sobre quién.
La fecha de hoy se le da desde el reloj del sistema en cada análisis, para que pueda
interpretar expresiones como "ayer" o "el lunes".

> **Principio clave:** ni Whisper ni el modelo escriben directamente en la base de
> datos. Siempre generan un **borrador que tú confirmas** antes de guardar nada.
> Es la red de seguridad frente a los errores de transcripción y de interpretación.

---

## Estructura del proyecto

```
Relaciones/
├── main.py            Arranque: servidor + ventana de escritorio
├── app.py             La aplicación: rutas, lógica, acceso a la base
├── datos.db           Base de datos SQLite (NO se sube al repositorio)
├── audios/            Audios grabados (NO se suben al repositorio)
├── estatico/          CSS, JavaScript, tipografías, iconos
├── plantillas/        Las vistas HTML
├── requisitos.txt     Dependencias de Python
└── venv/              Entorno virtual (NO se sube al repositorio)
```

---

## Privacidad

Este proyecto guarda información sobre personas reales, así que la privacidad no es
un extra, es el punto de partida:

- **La base de datos y los audios nunca se suben al repositorio.** Están excluidos
  en `.gitignore`.
- **Todo el procesamiento es local.** La transcripción y el análisis con IA ocurren
  en tu ordenador; ningún audio ni texto se envía a servicios externos.
- **El acceso remoto es una red privada** (Tailscale), no una web abierta a internet,
  y está protegido por una llave.
- Si compartes o publicas el proyecto, revisa que no haya datos personales en los
  archivos de documentación (`README.md`, y los archivos de notas del proyecto).

---

## Estado

- **Funcionando:** fichas de personas, círculos, vista de red, acceso desde el
  móvil, PWA instalable, grabación y subida de audios (con cola que reintenta si no
  hay conexión).
- **En construcción:** la conexión entre la grabación y el análisis —transcribir el
  audio automáticamente y proponer el borrador de qué apuntar—. Las piezas (Whisper
  y Ollama) están instaladas y probadas por separado; falta integrarlas en la
  aplicación.
- **Idea a futuro:** poder preguntarle a la aplicación por una persona y que
  responda a partir de lo que tienes guardado.
