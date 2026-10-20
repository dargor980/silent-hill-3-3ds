# F02.07 — Candidato 2.048, manifiesto de componentes y cierre final

Fecha: 2026-10-19. Contrato [LC-B](../../schemas/image-capacity-candidate-v1.md).
Evidencia [SRC121](../compatibility/capacity-candidate-evidence.json).

## Resultado

**RT-T3b.3a completo:** se reconstruyó y firmó un candidato privado con los
cambios de SRC120, sin las sondas históricas. El preflight pasa con capacidad
2.048. Dos perfiles nuevos aceptan **dos muestras PD v2 cada uno**, con
**30 imágenes respaldadas por archivos explícitos y 1.040 de la caché**.
El inventario permanece estable dentro de cada sesión y el proceso cierra con
código cero. No se admite captura ni ejecución por este resultado.

**RT-T3b.3 permanece abierto por la entrega final:** el productor informa tres
respuestas y ningún fallo de inventario, pero el consumidor acepta dos y rechaza
la tercera como `channel_unavailable`. El servicio cierra inmediatamente después
de su tercera entrega; el canal Python rechaza datos adicionales o EOF tras un
frame. Los tiempos medidos están dentro de 5 s/2 s, por lo que este resultado
no se atribuye a agotar esos plazos. La observación de dos sesiones y el código
son coherentes con esa incompatibilidad; falta una prueba dirigida y su corrección.

## Reconstrucción y preservación

- **128 objetos reconstruidos**, 75 archivos MOC regenerados y 470 entradas
  verificadas en el enlace; las otras 342 entradas conservan sus hashes.
- **19 archivos estáticos y 390 miembros**: dependencias sin las cabeceras
  afectadas, fuentes coincidentes y bytes de cada miembro idénticos al objeto.
  La comparación conserva miembros con nombres repetidos y separa el índice
  de símbolos Darwin de las unidades compiladas.
- Fuente limpia de 3.040 archivos; seis fuentes/cabeceras propias actualizadas.
  Se retiran cuatro fuentes instrumentadas y dos cabeceras de sonda del candidato
  del censo, sin perder las reparaciones previas del servicio y del frontend.
- Bundle de 200 archivos regulares y 42 Mach-O, frameworks resueltos, firma ad
  hoc verificada y `testconfig` aprobado. Consumidor privado de 92 archivos,
  fijado antes de las sesiones. ISO y BIOS se verifican por hash, sin copiarlas.

SHA-256 del ejecutable sin sondas:
`f16a81a0a6f0296b86dcb37423082c5668004c8000082b1a2601cd65b542010a`.

La secuencia de build duró 353,05 s; el enlace, 23,195 s. Se aplicó el presupuesto
LC-B específico: inicio ≥12 GiB libres, suelo 10 GiB, máximo 1 GiB de etapa y
compilación secuencial. El mínimo observado fue 12,34 GiB libres; el máximo
combinado medido de los dos candidatos fue 518,36 MiB. IB02 general conserva
20 GiB. No se compilaron dependencias de terceros ni se borraron builds.

## Causa adicional: archivos del sistema fuera de la caché

Con el manifiesto inicial de 43 archivos, los dos arranques superan preflight
y rechazan `PlatformInventoryFailure::uncovered`. Una variante privada añade
registro únicamente en las dos ramas terminales de esa causa. Se verifica que
revertir la inserción reproduce exactamente la fuente original; solo se recompila
`platform_inventory.cpp`, se preservan las otras 469 entradas y se firma de nuevo.
La sonda no cambia la clasificación, la capacidad, los plazos ni los retornos.

Las repeticiones identifican sucesivamente:

| Archivo | Tamaño | Identidad de firma Apple |
| --- | ---: | --- |
| IOHIDLib | 357.840 bytes | `com.apple.iokit.IOHIDLib` |
| AGXMetalG14G | 23.592.976 bytes | `com.apple.AGXMetalG14G` |
| CoreAudio | 3.114.480 bytes | `com.apple.audio.units.Components` |

Las identidades de dispositivo/inodo/tamaño y tiempos observadas coinciden con
disco. Cada archivo tiene arquitectura x86_64, firma verificada y requisito con
`anchor apple`. La primera verificación de IOHID dentro del contexto restringido
no pudo consultar confianza (`CSSMERR_TP_NOT_TRUSTED`); el mismo archivo sin
cambios pasa con acceso a los servicios de confianza del host. No se sustituye
esa verificación por el nombre o por el mero contenido de la firma.

Se conservan los manifiestos de 43, 44 y 45 archivos y sus rechazos. El manifiesto
final fija **46 archivos y cinco raíces exactas**, añadiendo los tres componentes
por hash y tamaño antes de arrancar el proceso. Se aplica la clasificación
ordinaria por archivo: no se los etiqueta automáticamente como caché, se omiten
ni se incorporan durante una sesión. Los componentes del sistema no se copian
ni se redistribuyen. Las pruebas positivas usan el candidato **sin sondas**.

## Sesiones y límites

| Sesión final | Primera consulta | Segunda | Tercera intentada | Aceptadas |
| --- | ---: | ---: | ---: | ---: |
| Perfil 1 | 1,626 s | 1,402 s | 1,409 s | 2 |
| Perfil 2 | 1,576 s | 1,446 s | 1,410 s | 2 |

Son tiempos de consulta del consumidor; no representan un benchmark de juego.
Cada productor registra `prepared=1`, `sampled=1`, `origins=0`, `inventory=0`,
`replies=3`, `clean=1`, `admitted=0`. `cpu_pending=1` indica que el cierre tuvo
que esperar la retirada CPU; no es una afirmación de CPU pendiente al salir.
Las cuatro muestras aceptadas tienen secuencias 1/2, identidad/nonce/épocas
coherentes dentro de cada sesión y revisión del loader estable. Conservan
condiciones desconocidas o violadas: no prueban los gates de JIT, caché, DMA
o ciclo de vida necesarios para captura.

El control sin VM rechaza por indisponibilidad y termina limpiamente. Se
conservan los rechazos iniciales, los seis perfiles de la sonda y los dos
rechazos intermedios con manifiestos incompletos. Los intentos preparatorios
del verificador de archivos estáticos también quedan identificados; no se
presentan como compilaciones aprobadas.

Pasan **304 pruebas Python** de codec/canal/sesión/presupuesto. Los 58 casos del
repositorio y supervisor se ejecutan con acceso a la tabla de procesos; el primer
intento restringido conserva seis fallos por `ps: Operation not permitted`,
sin modificar las pruebas. Las suites C++ de SRC120
son evidencia previa, no nuevas ejecuciones de esta etapa. No se ejecutan CI
remota, Linux, build 3DS ni captura de RAM del juego.

## Trabajo siguiente

1. Reproducir con una prueba dirigida la pérdida de la tercera respuesta cuando
   el productor cierra inmediatamente, preservando el rechazo de EOF del cliente.
2. Diseñar la terminación después de la última entrega: dueño único del canal,
   espera de liberación del consumidor dentro del plazo ya existente, cancelación,
   rechazo de bytes adicionales y conservación de CPU/DW hasta su retirada.
3. Validar negativos, sanitizadores y dos perfiles nuevos del candidato con las
   tres respuestas aceptadas. Solo entonces cerrar RT-T3b.3; RT-T3c y los gates
   RS-T3/RB-T3/DW-T3 conservan sus criterios independientes.
