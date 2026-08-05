# Decisiones que no se rediscuten

Cosas que ya se probaron o se descartaron a propósito. Si algo de aquí parece
una buena idea, **no se hace: se dice**.

## Nunca

- Ninguna puntuación, porcentaje, racha, «salud de la relación» ni métrica al
  lado del nombre de nadie.
- Ningún recordatorio, notificación ni frecuencia de contacto.
- Ningún dashboard, gráfica ni estadística.
- Ninguna importación de contactos del móvil.
- Ningún usuario, login ni contraseña. La llave de red no es un login.
- Ninguna llamada a internet, API, CDN ni telemetría.
- Ningún campo de «cómo nos conocimos», deudas de dinero, ni notas positivas
  o negativas.
- Ningún diario personal: esto registra a otras personas.
- Nada de «persona en pausa».
- Ninguna otra forma de clasificar gente aparte del círculo.

## Ya se probó y salió mal

| Idea | Qué pasó |
| --- | --- |
| Dibujar la red pixelada, a un tercio de resolución | Destrozaba las líneas finas y se comía la profundidad |
| Anillos concéntricos por círculo | Se sustituyeron por cuadrados en la leyenda; nadie cambia de sitio |
| Fotos a 1 bit con tramado | A 256px el umbral destrozaba las caras. Ahora escala de grises |
| Aplastar el eje Y de la red | Quedaba una cáscara plana |
| Buscar puerto libre al arrancar | Rompía la dirección guardada en el móvil. Ahora 9765 fijo |
| Dos columnas en *De un vistazo* | Etiqueta y valor quedaban en extremos opuestos |
| Bandas negras en todos los paneles | Se prohibió… y luego se pidió justo para la ficha (ver excepción) |

## El service worker no cachea, y no es un olvido

`estatico/sw.js` existe **sólo** para que el navegador ofrezca instalar la app.
Su manejador de `fetch` está vacío a propósito. **No añadir caché**: la app vive
en la red del usuario, no hay latencia que compensar, y cachear sólo serviría
para que el móvil enseñe versiones viejas justo después de tocar algo.

## Excepciones vigentes

Dos cosas contradicen la letra de `CLAUDE.md` porque se pidieron
explícitamente. **Están acotadas y no se extienden:**

1. **Banda rellena como cabecera de sección**, en la ficha completa y en los
   bloques personales de la captura de Notas (`.bloque-cabecera`). Comparten el
   mismo componente; el resto de la app sigue separando con aire y filete.
2. **Un rojo** (`--alarma`), para el hover de un borrado y para una identidad
   propuesta por la voz que aún necesita confirmación. No entra en otros estados.

## Reglas de trabajo

- Un cambio cada vez. No reescribir archivos enteros para tocar una función.
- Antes de añadir algo que no esté en el encargo, preguntar.
- Avisar de los datos que se van a perder antes de tocar la base.
- Una acción dentro de la misma pantalla **nunca manda la página arriba**.
- Después de cualquier cambio: entrada fechada en el registro de `CLAUDE.md`
  **y** actualizar el mapa que corresponda.
- Subir el `?v=` de los recursos estáticos o el móvil usará la caché vieja.
- Nunca matar procesos por nombre; localizar por el puerto 9765.
- Los audios son archivos sueltos en `audios/`, nunca dentro de la base, y
  fuera de git y de la copia de todo: contienen voz. Archivo y fila forman una
  pareja uno-a-uno: el arranque reconcilia ambos y subir/borrar compensan fallos.
- El audio se guarda tal cual llega del móvil (Opus donde se pueda), sin
  transcodificar: cero dependencias nuevas y nada sale a internet.
- Notas puede usarse sin audio. Al subir una grabación, la cola local ejecuta
  Whisper y Qwen automáticamente; elegirla sólo decide qué proceso se revisa.
- Una quedada guarda resumen y texto completo: las fichas compactas enseñan el
  primero y la ficha general el segundo. Las filas antiguas caen a su texto.
- La voz separa utilidad y precisión: *Preguntar por* guarda sólo el asunto
  natural («El viaje a Huelva»); el resumen compacto recuerda lo esencial con
  tiempo relativo («esa misma semana»); el texto extendido conserva fechas,
  horarios, canal y discurso indirecto natural. Un plan o una compra puntual
  pertenece a la quedada, nunca a Datos.
