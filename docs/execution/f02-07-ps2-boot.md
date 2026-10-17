# F02.07 — BIOS principal y comprobación de arranque PS2

2026-10-17 · avance de `camera-runtime-capture-eu/environment`.

La BIOS principal proporcionada por el usuario está copiada y seleccionada en el
perfil privado de PCSX2 v2.8.2. PCSX2 reconoce **Europa v2.00 (2004-06-14)** y sus
logs registran la carga del ejecutable europeo de Silent Hill 3 durante una prueba
breve. **No se ha verificado visualmente el juego ni capturado los puntos de cámara.**
F02.07/Q05/G02 permanecen abiertos.

## Identidad y configuración

Origen indicado por el usuario: `Downloads/SCPH-70004_BIOS_V12_PAL_200.BIN`.
Se conservaron el original y el ROM2 anterior. La copia principal está en
`/Users/germancontreras/sh3-private-data/pcsx2/PCSX2/bios`, con modo 0600.
Mide **4.194.304 bytes**, SHA-256
`d6653f4e93be2f6f9e9d690a934f26cf0f6ad4e348b69f41ef736732c3a6685b`.
La inspección acotada identificó ROMVER y 101 entradas con rangos dentro del archivo;
el reconocimiento posterior de PCSX2 coincide con esos metadatos. No se copiaron
bytes de BIOS al repositorio ni se publicaron sus tablas.

Se respaldó el INI anterior, se seleccionó el `.BIN` y se completó la configuración
manualmente. Se mantienen carpeta de ISO, teclado, opciones avanzadas y parches
opcionales desactivados. El acceso `Applications/PCSX2 SH3.command` sigue usando
la raíz privada con `umask 077`. El perfil final restaura **arranque pausado** para
depuración; al iniciar una sesión se debe reanudar para ejecutar.

INI final, después de `-testconfig` con salida 0: SHA-256
`374aab2aee57025debfbba90ab3c8c71cf4230583f79c227e9da7579774b5c06`.
El asistente ya no queda pendiente de BIOS. El perfil y los binarios privados mantienen
0600; las salidas NVM/MEC creadas por PCSX2 también quedan en la carpeta privada.

## Pruebas realizadas y límites

1. **BIOS sin disco:** prueba de 20 segundos, arranque sin pausa. El log de PCSX2
   reconoce Europa v2.00 e inicializa Metal, controles y subsistemas. Al faltar NVM/MEC
   inicialmente, PCSX2 registra su creación predeterminada. Terminación solicitada
   mediante SIGTERM; cierre controlado, salida 0.
2. **ISO europea:** se revalidó el SHA-256 completo de la imagen ya identificada y
   se ejecutó una prueba `-fastboot` de 25 segundos. Los logs registran
   `SLES-51434`, ELF de 3.395.784 bytes, CRC activo `5088CCDB`, inicialización Metal
   y eventos de sincronización vertical. Cierre controlado por SIGTERM, salida 0.
3. **Perfil final:** se restauró pausa inicial y se comprobó con el acceso real
   `PCSX2 SH3.command -testconfig`. Salida 0; selección de BIOS, directorio de juego,
   estado del asistente, permisos y hash del INI comprobados después de guardar.

PCSX2 aplica sus ajustes automáticos de GameDB: clamp VU0/VU1 en modo 2, blending
mínimo 4 y deinterlace 9, registrados en la evidencia. Desactivar cheats y parches
opcionales no desactiva estos ajustes automáticos. El entorno de captura deberá
conservar esta versión y documentar cualquier cambio.

Estas pruebas acreditan reconocimiento/carga y funcionamiento del proceso durante
el intervalo observado. No se inspeccionaron píxeles, sonido, respuesta de controles,
menús, idioma o dificultad; tampoco se observaron breakpoints del plan. No se
declara una partida jugable o equivalencia del port. Las direcciones de entrada que
imprime el cargador son metadatos, no una traza de instrucciones ejecutadas.

Los logs completos permanecen en `pcsx2/PCSX2/verification` dentro de la raíz privada.
Al usar `-logfile`, la consola solo conserva mensajes iniciales; la comprobación de
BIOS/ELF utiliza el log dedicado. Metadatos sanitizados, comandos y resultados:
`build/f02-07-ps2-boot`. [Evidencia publicable](../compatibility/ps2-boot-evidence.json).

No cambiaron código Python/C++, tests, SDK o pipelines. Se comprobaron contratos de
repositorio, custodia y enlaces; no se repitió la batería histórica de 1435 pruebas
por esta configuración de host. La evidencia de la instancia anterior permanece
intacta; no se reescribe como si ya hubiera dispuesto de BIOS.

## Siguiente paso

Continuar el [protocolo](../compatibility/camera-runtime-capture.md): abrir el depurador
EE, contrastar rangos/hash del plan, seleccionar español y Normal/Normal y observar
una invocación completa por frontera A/B. Los valores y snapshots seguirán fuera del
checkout. Solo después se podrá validar la captura e investigar su relación con el
catálogo de recursos; el vínculo de cámara sigue sin demostrar.
