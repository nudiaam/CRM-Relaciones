from faster_whisper import WhisperModel
import sys, time

audio = sys.argv[1]

print("Cargando modelo large-v3 en la GPU...")
modelo = WhisperModel("large-v3", device="cuda", compute_type="float16")

print("Transcribiendo:", audio)
t = time.time()
segmentos, info = modelo.transcribe(
    audio,
    language="es",
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
    condition_on_previous_text=False,
)

print("\n--- TRANSCRIPCION ---")
for s in segmentos:
    print(s.text.strip())
print("---------------------")
print(f"Tardo {time.time()-t:.1f}s")
