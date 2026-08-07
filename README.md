# Relaciones

CRM personal *privacy-first* que corre íntegramente en local. Gestiona tus contactos y relaciones sin que ningún dato salga de tu máquina.

Incluye captura de voz con transcripción y análisis mediante modelos de IA locales (nada de APIs externas).

## Características

- Gestión de contactos y notas en base de datos local (SQLite)
- Aplicación de escritorio nativa (pywebview) sobre backend FastAPI
- Captura de voz → transcripción con **faster-whisper** → análisis con **Qwen3** vía Ollama
- Acceso opcional desde el móvil como PWA a través de Tailscale

## Requisitos

- **Python 3.10+**
- **Ollama** ([ollama.com](https://ollama.com))
- **GPU con ~12 GB de VRAM** recomendada para correr los modelos con soltura. Con menos, ver la sección [Ajustar los modelos](#ajustar-los-modelos).
- CUDA compatible si quieres aceleración por GPU en la transcripción

## Instalación

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/⚠️tu-usuario/relaciones.git
cd relaciones

python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Descargar el modelo de lenguaje (Ollama)

Con Ollama instalado y corriendo:

```bash
ollama pull qwen3:14b
```

Asegúrate de que Ollama esté activo antes de arrancar la app (`ollama serve` o el servicio en segundo plano). La app espera encontrarlo en `http://localhost:11434`.

### 3. Modelo de transcripción (faster-whisper)

No requiere descarga manual: **large-v3** se baja solo (~3 GB) la primera vez que se usa. El primer arranque tardará un poco más mientras lo descarga.

### 4. Arrancar

```bash
python ⚠️main.py
```

## Ajustar los modelos

Si tu GPU tiene menos VRAM, puedes usar modelos más ligeros editando ⚠️`config.py` / `.env`:

| Ajuste | Por defecto | Alternativa ligera |
|---|---|---|
| Modelo Ollama | `qwen3:14b` | `qwen3:8b` |
| Modelo Whisper | `large-v3` | `medium` / `small` |

Recuerda hacer `ollama pull` del modelo alternativo si cambias el de lenguaje.

## Acceso móvil (opcional)

La app funciona perfectamente en local sin esto. Si quieres acceder desde el móvil como PWA, expón el servidor a través de [Tailscale](https://tailscale.com) dentro de tu red privada. ⚠️*(Añadir pasos concretos si procede.)*

## Privacidad

Todos los datos —contactos, notas, grabaciones y transcripciones— se quedan en tu máquina. No se envía nada a servicios externos.

## Licencia

⚠️ Indica aquí tu licencia (p. ej. MIT).
