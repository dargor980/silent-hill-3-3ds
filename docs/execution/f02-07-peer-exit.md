# F02.07 — Abandono del consumidor con VM real

Fecha: 2026-10-19. Contrato [RX01–RX05](../../schemas/runtime-peer-exit-v1.md).
Evidencia [SRC123](../compatibility/peer-exit-evidence.json).

**RT-T3c.1a y RX-T1–RX-T3 completos.** Ocho perfiles nuevos del candidato real
verifican rechazo y limpieza cuando el padre autenticado abandona el canal o
envía datos adicionales. Cada uno de los cuatro casos se ejecutó dos veces,
según el plan fijado antes de comenzar; los ocho pasaron.

| Acción del consumidor | Perfiles | Respuestas aceptadas por perfil | Motivo del productor | Liberación terminal |
| --- | ---: | ---: | --- | --- |
| Cierre físico tras autenticar, antes de pedir datos | 2 | 0 | `peer_lost` (4) | No |
| Cierre físico tras primera respuesta | 2 | 1 | `peer_lost` (4) | No |
| Cierre físico tras tercera respuesta | 2 | 3 | `peer_lost` (4) | Sí |
| Byte adicional tras tercera respuesta | 2 | 3 | `protocol` (7) | Sí |

Todos registran `clean=1`, `admitted=0`, salida cero y ausencia de procesos
pendientes en la supervisión. `cpu_pending=1` indica que el servicio esperó
retirada CPU antes de terminar. No se interpreta como un recurso pendiente al
salir. En los dos casos de byte adicional, el padre mantiene abierto el socket,
observa EOF y contrasta por separado el rechazo del productor y la salida.

Se decodifican nuevamente los **14 frames aceptados** con solicitud, secuencia
y expectativas fijadas. Tienen 30 imágenes por archivo, 1.040 de caché, revisión
1.071 y épocas `[53, 3, 1, 1]`; identidad y nonce se conservan dentro de cada
sesión. Los hechos desconocidos o violados permanecen así. El máximo observado
de una primera consulta fue 1,703 s y de una revalidación 1,497 s. Esta tanda
no modifica ni invalida el rechazo por plazo conservado en SRC122.

## Implementación y preservación

La [fixture](../../tests/fixtures/runtime-service/peer_exit_launcher.py) usa el
lector nativo, canal, codec y sesión ordinarios ya fijados. La selección de la
acción terminal está separada de la aceptación de muestras. Antes del abandono
inicial también autentica PID, nacimiento y usuarios del hijo. Registra si se
alcanzó realmente el punto deseado; un fallo previo de muestra no habría contado
como prueba del cierre terminal.

No se modifica ni recompila el candidato de SRC122, cuyo SHA-256 sigue siendo
`45c78a01a374f24ee271e7c0736a42f0ac9d086639f123a8458fdb078cda8689`.
Bundle, fuentes propias, consumidor de 92 archivos, lector nativo y manifiesto
conservan sus hashes. ISO/BIOS se contrastan antes y después de la tanda.
No se cambia el perfil del usuario ni se añade instrumentación al productor.

La secuencia duró **66,43 s**. El presupuesto de esta etapa, que reutiliza el
ejecutable, exige inicio/suelo de 10 GiB, máximo 64 MiB, 100 s por proceso,
600 s de secuencia y supervisión cada 0,5 s. Se observaron al menos 12,24 GiB
libres y como máximo 0,29 MiB de etapa. IB02 y los límites de muestras no cambian.

Pasan Ruff y formato de la fixture, y **58 pruebas del repositorio/supervisor**.
Las 433 ejecuciones nativas y 304 Python de SRC122 son evidencia previa de
componentes sin cambios; no se presentan como nuevas ejecuciones. No se ejecutó
CI remota, Linux, compilación 3DS ni captura de RAM.

## Lo que falta en ciclo de vida

- **RT-T3c.1b:** provocar cancelación desde la ruta real de la interfaz y durante
  inventario/entrega, distinguiendo señal de cancelación, retiro CPU y unión DW.
  Necesita una coordinación observable del punto de inyección; un retardo fijo
  no demuestra que se alcanzó la fase.
- **RT-T3c.1c:** ejecutar callbacks tardíos/duplicados en la cola Host real y
  verificar que no adquieren ni publican después de cancelación o retirada.
  Los casos existentes con cola de prueba no sustituyen este contraste.

RT-T3c.2 conserva la investigación del margen temporal. RT-T3c.3 y los gates
RS-T3/RB-T3/DW-T3 de escritores y ciclo de vida siguen abiertos. Rechazar un
consumidor que termina correctamente no concede permiso para capturar memoria.
