# F02.07 — Plan y validación de observaciones privadas

Fecha: 2026-10-17. `camera-runtime-observation-plan-eu` completada como infraestructura.
**No se ha ejecutado Silent Hill 3 ni capturado registros reales.** PCSX2 está instalado
y el perfil acepta la comprobación de configuración. Se copió el ROM2 aportado por el usuario; falta la BIOS principal.
La siguiente instancia es `camera-runtime-capture-eu`. F02.07/Q05/G02 permanecen abiertos.

## Resultado y alcance

Se generaron dos planes idénticos desde la ISO europea, regenerando la cadena de
evidencia anterior: **tres fronteras, 25 puntos y seis rangos de código**. Nueve puntos
son antes/entrada/retorno; dieciséis son checkpoints opcionales dentro de ventana.
Los puntos fuera de ventana quedan diferidos. El estado es `not_performed`.

Los archivos `reports/local/f02-07-camera-observation-plan-v1.json` y
`reports/local/f02-07-camera-observation-plan-v1-repeat.json` miden **12.137 bytes**;
SHA-256 `55285f27e8dc2c9c894e1d07c9882f10091ef094a26e509a28d0cead89bfdd6b`.
Contienen posiciones, identificadores, relaciones y hashes; no instrucciones,
tablas, valores de registros o bytes originales.

Cada ejecución verifica el hash completo de ISO, perfil y ejecutable, fija ambas
copias del informe de fronteras y exige igualdad canónica con su regeneración.
El catálogo se fija por hash y se contrasta su identidad de origen/alcance; no se
releen ni revalidan individualmente los 1740 payloads en esta operación.
Las identidades heredadas se conservan en el [informe anterior](f02-07-camera-boundary.md).
Comandos, tiempos y resultados quedan en
`build/f02-07-camera-observation/real-execution.json` y `real-identity.json`.

## Contrato, SOLID y pruebas

[CO01-CO08](../../schemas/camera-observation-v1.md) precedieron a la implementación.
`observation_plan` prepara puntos y rangos sobre evidencia reconciliada;
`observation_capture` valida mediante un puerto de lectura;
`capture_files` administra custodia/descriptores y cierre estable;
`camera_observation` compone CLI y publicación. No se alteraron inspectores históricos,
extractor o runtime.

Se exige sesión/entorno/versiones, eventos contiguos, PC/GPR exactos por punto y
una invocación completa por frontera. Entrada JAL valida el enlace bajo de GPR31.
Capturas parciales, invocaciones mezcladas, campos extra, claves duplicadas,
tipos ambiguos, hashes falsos o rangos desbordados se rechazan sin recibo válido.
La lectura privada rechaza enlaces, permisos públicos y cambios de identidad hasta
el cierre. Límites: JSON 1 MiB, 128 eventos, 32 snapshots y 16 muestras de datos,
cada blob de hasta 4096 bytes. Los datos opcionales no se clasifican como recursos.

El recibo solo publica hashes/conteos/comparaciones. Los hashes del emulador, BIOS e
INI son declarados por el capturador y no inspeccionados por este validador.
`execution_authentication: not_provided` conserva ese límite. Una igualdad observada
en una invocación no demuestra preservación global; `not_reached` no demuestra ausencia.
No existe todavía un recibo de captura real.

**128 casos nuevos; 1435/1435 pruebas aprobadas.** Cobertura global independiente:
**2815/2855 líneas (98,60 %) y 1003/1030 ramas (97,38 %)**. Los tres módulos de
plan/contrato/lectura privada alcanzan 100 % de líneas y ramas. La CLI alcanza 52/53
líneas y 19/20 ramas; su entrada `__main__` se ejerció aparte en los dos planes reales.

Fixtures propios cubren el recorrido completo ISO sintética → plan → captura privada
→ recibo repetible, argumentos después del slot, diferencias al retornar, ausencia
de retorno, versiones/sesiones/orden alterados, límites, symlinks/hardlinks/FIFO,
permisos públicos, cambios durante/después de leer, sustitución de directorios y
fallos al cerrar sin publicación. No se usan originales en tests o CI.

El primer recorrido completo coincidió con la creación de archivos ignorados de
planes reales: el control de custodia vio rutas posteriores a su inventario inicial
y falló (1434 aprobadas, una fallida). Se preservó esa evidencia como `initial-*`.
Tras terminar la generación, la suite estable pasó sin cambiar controles ni tests.
Ruff, formato, cobertura y contratos de arquitectura/custodia/enlaces se verifican
en el mismo job quality. CI remota, hardware y builds C++/ARM no se ejecutaron:
no cambiaron runtime, SDK ni configuración de compilación.

## PCSX2 instalado por solicitud del usuario

Se descargó el paquete macOS de la [release oficial v2.8.2](https://github.com/PCSX2/pcsx2/releases/tag/v2.8.2):
24.377.200 bytes, SHA-256
`3ed9eb40a33eae67134142c24255a079be444f0616ca29575a04a37981f7d426`,
coincidente con el digest publicado. Instalación en la carpeta Applications del usuario,
sin reemplazar otro bundle. Firma estricta y Gatekeeper del instalado: salida 0,
aceptado como Notarized Developer ID. macOS 26.5 ARM64 ejecuta el binario x86_64
con Rosetta ya presente. [Procedencia y hashes](../compatibility/camera-observation-research-evidence.json).

Se creó un perfil privado, acceso `PCSX2 SH3.command`, biblioteca apuntando a `binaries`,
opciones avanzadas, arranque pausado y parches desactivados. El acceso aplica `umask 077`
y usa `-datapath`; PCSX2 normalizó el INI y conservó los ajustes comprobados.
`-testconfig` terminó con salida 0, sin arrancar una VM ni el juego. La primera
inicialización con la ruta base inexistente salió 1; se creó explícitamente y se
repitió con éxito. El asistente queda incompleto porque falta BIOS.

La automatización de UI agotó su tiempo y no permitió inspección visual. Una consulta
CLI dentro del sandbox falló por restricciones de servicios macOS; fuera del sandbox,
ayuda y comprobación del perfil funcionaron. Los checks de firma se repitieron fuera
del sandbox para evitar atribuir al bundle errores de acceso a esos servicios.
No se deshabilitó Gatekeeper ni se modificó la firma.

El [protocolo de captura](../compatibility/camera-runtime-capture.md) indica rutas,
controles, pasos y límites. La [BIOS requerida](https://pcsx2.net/docs/setup/bios/)
debe proceder de una PS2 propia. Después de la instalación el usuario indicó un ROM2 en Descargas: se copió al directorio privado, conservando el original, con modo 0600 y SHA-256 verificado. Mide 524.288 bytes, no contiene ROMVER y no supera el mínimo de autodetección de 4 MiB de la versión; es insuficiente como BIOS principal. La selección real de BIOS sigue pendiente. El código GPL de
PCSX2 solo se consultó para opciones/formato de configuración; no se incorporó al port.
El emulador es herramienta host externa, sin redistribución por este proyecto.

## Evidencia y siguiente tarea

JUnit, cobertura, comandos, entorno, verificación de instalación, manifiesto de fuentes
y comprobación de evidencia histórica quedan en `build/f02-07-camera-observation`.
Los 140 archivos de la línea base conservan su hash, incluidos los 65 archivos previos de código/pruebas y los informes históricos. Las extracciones anteriores se contrastaron por sus cuatro recibos, sin releer payloads.
Los planes locales siguen ignorados y con permisos privados. El manifiesto excluye
este informe para evitar referencia circular; su propia identidad está en
`source-manifest-identity.json`.

`camera-runtime-capture-eu` requiere seleccionar la BIOS propia, fijar el INI definitivo,
observar A y B en el depurador y validar los archivos de sesión privados. Después
se investigará el vínculo del dato con ID/rango/hash del catálogo. La instalación,
el plan y sus pruebas no resuelven campos 92/108, colas, decoder, las doce categorías
ni las dos salas conectadas del slice.
