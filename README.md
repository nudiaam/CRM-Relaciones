# Relaciones

Una agenda de relaciones personales que funciona **entera en tu ordenador**. Guarda tus contactos, notas y grabaciones de voz sin que nada salga de tu máquina ni se suba a internet.

Puedes hablarle y ella transcribe y resume lo que digas, usando inteligencia artificial que corre en tu propio equipo.

---

## Antes de empezar

Necesitas instalar **dos programas gratuitos**. Solo se hace una vez.

### 1. Python

Es el motor sobre el que funciona la app.

- Descárgalo desde [python.org/downloads](https://python.org/downloads)
- Durante la instalación, **marca la casilla "Add Python to PATH"** (importante).

### 2. Ollama

Es lo que hace funcionar la inteligencia artificial en local.

- Descárgalo desde [ollama.com](https://ollama.com) e instálalo como cualquier otro programa.
- Una vez instalado, ábrelo y **descarga el cerebro de la IA** copiando esta línea en la ventana de comandos:

  ```
  ollama pull qwen3:14b
  ```

  Tardará un rato (es una descarga grande). Deja que termine.

> 💡 Ollama tiene que estar abierto cada vez que uses Relaciones.

---

## Instalar Relaciones

1. Descarga este proyecto (botón verde **Code → Download ZIP**) y descomprímelo donde quieras.

2. Abre la carpeta y haz doble clic en **⚠️`instalar.bat`** *(la primera vez, para preparar todo).*

3. A partir de ahí, para abrir la app haz doble clic en **⚠️`Relaciones.bat`**.


La primera vez que grabes un audio, la app descargará automáticamente el módulo de transcripción (unos 3 GB). Es normal que ese primer arranque tarde un poco más.

---

## Requisitos del ordenador

- **Windows 10/11**
- Una **tarjeta gráfica (GPU) potente** para que la IA vaya fluida. Si el ordenador va justo, la app puede configurarse para usar modelos más ligeros — pídele ayuda a alguien técnico para ese ajuste.

---

## Usar desde el móvil (opcional)

Se puede abrir la app desde el móvil dentro de tu red privada usando [Tailscale](https://tailscale.com). Es un paso avanzado y **no hace falta** para usarla en el ordenador.

---

## Tus datos son tuyos

Todo —contactos, notas y grabaciones— se guarda **solo en tu ordenador**. La app no envía nada a ningún sitio.

---

## Licencia

MIT
