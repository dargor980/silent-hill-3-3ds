# Procedimiento de recursos — F01.06

Estado físico: **no ejecutado**. Target New Nintendo 2DS XL, Homebrew Launcher; FBI no lanza el 3DSX. Este procedimiento usa exclusivamente diagnóstico/fixture sintéticos. [Contrato y protocolo diagnostic-v1](resource-contract.md); [evidencia/build actual](../execution/f01-06-resources.md).

1. Conservar el bundle `.3dsx`/`.elf`/manifiesto/ID y verificarlo con `python -m tools.debug.bundle verify --directory build/f01-06/artifacts --build-id 327b5e3355ee`. Registrar SHA-256 y build en la hoja de sesión; no usar el ELF de F01.05 con este 3DSX.
2. Copiar `.3dsx` y `probe.txt` propios a `/3ds/sh3_diagnostic/` de SD. Registrar modelo, firmware y versiones de Homebrew Launcher/Luma/FBI conocidas; desconocidos como null. No modificar firmware ni configuración CPU como parte de esta prueba.
3. Abrir desde Homebrew Launcher; anotar estado/Result NDSP y Probe/Load/Save. Pulsar SELECT para recursos; verificar página completa, valores en bytes y build correcto. SELECT vuelve a audio/archivos, START sale. A mantiene pausa y X/Y conservan sus acciones documentadas.
4. Registrar capacidad heap/lineal, libre lineal/VRAM, capacidad/uso región APPLICATION, flag HB, familia New, límite APT y cada Result. No sumar ni convertir esos campos en B_app. Si hay SDK_ERROR/INVALID conservar estado y código, no reemplazarlos por cero.
5. Esperar calentamiento 60 intentos y ventana completa de 120; captura visible después del refresco siguiente. Registrar p95 de los tres intervalos en ticks, n y unavailable, rechazo, running/paused y estado de audio. No usar estas cifras como FPS del juego ni atribuir espera a GPU puro.
6. Pausar y reanudar con A; cerrar/abrir tapa y repetir captura. Debe reiniciarse calentamiento y ventana. Registrar comportamiento de controles, audio y pantalla por separado. Si un evento no se observa no marcar PASS por inferencia.
7. Salir con START y comprobar retorno. Archivar hoja con fecha, build/hashes, versiones, lecturas y fotos/capturas reales disponibles. La ventana gira: no representa la sesión completa.

## Hoja mínima por ejecución

| Campo | Valor antes de ensayo físico |
|---|---|
| execution_kind | physical_not_tested |
| build_id / 3dsx_sha256 / elf_sha256 | copiar del bundle concreto |
| protocol | diagnostic-v1 |
| hardware | New Nintendo 2DS XL (confirmación del usuario) |
| launcher / version / firmware / CPU clock | Homebrew Launcher / null / null / null |
| scene / language / difficulty | synthetic-diagnostic / not_applicable / not_applicable |
| audio / state / epoch | registrar |
| B_app / heap_free / largest_allocatable_block | null, sin medición |
| pool readings / Result / timing p95,n,unavailable | null, sin medición |
| verdict | pending |

Una futura medición de B_app debe definir capacidad efectivamente utilizable y coexistencia del proceso, reservas/márgenes y límites por pool; requiere método revisado antes de realizar pruebas de asignación. Esta iteración no agota memoria ni garantiza que toda memoria libre se pueda reservar de una vez. El gate de 80 % sigue pendiente.
