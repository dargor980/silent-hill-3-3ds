# RX — Abandono del consumidor en el candidato real

Historia: como investigador, necesito comprobar la retirada del servicio cuando
el consumidor termina antes de completar el protocolo o envía datos adicionales.
Es la parte RT-T3c.1a; no sustituye cancelación UI, callbacks tardíos ni gates.

## Requisitos EARS

- **RX01:** WHEN se pruebe un abandono THEN SHALL usar el ejecutable, manifiesto,
  lector de identidad y consumidor ordinario fijados por SRC122; SHALL conservar
  sus hashes y no inyectar sondas ni cambiar fuentes o plazos del productor.
- **RX02:** WHEN el padre autenticado cierre físicamente antes de la primera
  solicitud o después de la primera respuesta THEN SHALL rechazar el canal,
  retirar CPU/DW y cerrar con código cero, sin respuesta posterior ni admisión.
- **RX03:** WHEN cierre físicamente después de validar tres respuestas THEN
  SHALL rechazar identidad terminal no disponible. WHEN envíe un byte adicional
  en ese punto THEN SHALL rechazar por protocolo, sin cuarta adquisición.
- **RX04:** WHEN se registre un resultado THEN SHALL distinguir aceptación de
  frames, motivo de rechazo, limpieza y salida del proceso. SHALL conservar cada
  intento, incluido un posible plazo agotado antes del punto que se desea probar;
  ese intento no demuestra cobertura del punto terminal.
- **RX05:** WHEN se cierre esta parte THEN SHALL ejecutar dos perfiles nuevos por
  caso y verificar ambos resultados. SHALL conservar los verificadores ordinarios
  y su límite de 5 s/2 s, además del límite global del servicio. El launcher
  SHALL autenticar al hijo antes del abandono inicial.

## Diseño y presupuesto

Una fixture específica configura un padre autenticado y selecciona entre cuatro
acciones: cerrar tras conexión, cerrar tras una respuesta, cerrar tras tres, o
enviar un byte tras tres. Solo registra frames que el canal/sesión ordinarios ya
aceptaron. Al enviar el byte conserva el descriptor hasta observar el cierre del
productor; esa espera es de limpieza y no amplía los plazos de muestras/servicio.

Reutiliza el bundle de SRC122 sin recompilarlo. Perfiles, logs y copia fijada de
la fixture se alojan en una etapa privada nueva; el perfil del usuario no cambia.
Inicio y suelo ≥10 GiB libres, etapa ≤64 MiB, supervisión cada 0,5 s, ≤100 s por
proceso y ≤600 s para ocho casos secuenciales. Un rechazo no se reintenta dentro
de la misma sesión. Las dos ejecuciones de cada caso se fijan antes de empezar.
Un fallo inesperado mantiene el caso pendiente; no se reemplaza por éxitos.

## Tareas

- [x] **RX-T1:** implementar fixture con acciones separadas de aceptación de
  muestras; fijar fuentes y presupuesto antes de ejecutar. RX01–RX04.
- [x] **RX-T2 / RT-T3c.1a:** ejecutar los ocho perfiles, contrastar hashes antes y
  después, decodificar cada frame y verificar causa/limpieza/salida. RX01–RX05.
- [x] **RX-T3:** publicar todos los resultados y separar cobertura de transporte
  de cancelación UI, callbacks tardíos y evidencia de escritores. RX04–RX05.

Resultado: [SRC123](../docs/execution/f02-07-peer-exit.md). Los ocho perfiles
cumplen la causa de rechazo, limpieza y salida esperadas; no fue necesario
repetir ningún intento fuera del plan.
