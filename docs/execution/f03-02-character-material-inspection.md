# CT-T5 — Integración del material al visor

2026-10-22. **CT-T5a–d completadas; CT-T5e física fallida.** Build
**`3fde5682ed11`**, aplicación **SH3 textured character**.
[EARS y diseño](../specs/sh3-3ds/character-material-inspection.md),
[protocolo para New 2DS XL](../compatibility/character-material-inspection.md).

Actualización del 2026-10-22: el reemplazo **`ced27c955e41`** supera
**CT-T5e.1 funcional** según el usuario: caballo con texturas, Q12 avanza,
60 segundos sin bloqueo, controles, START, tapa y HOME. CT-T5e.2 conserva
las métricas nuevas pendientes. El resultado fallido de v1 se conserva abajo.

## Resultado y alcance

La malla animada `0x0209` / clip `0x1449` conserva exactamente SCM1 y SAN1
de CM-T5. SCT1 incorpora las tres imágenes 512×512 y los grupos contrastados
en [CT-T4](f03-02-character-material-runtime.md). Se dibujan 1.113 triángulos
candidatos procedentes de 1.455 vértices; no se aplica el descarte de caras VU
que reducía el conjunto visible en la captura PS2.

| Imagen / CLUT | Submallas | Primer índice | Índices |
|---|---|---:|---:|
| 0 / 0 | 0–5 | 0 | 1263 |
| 1 / 0 | 6–8 | 1263 | 879 |
| 2 / 0 | 9–14 | 2142 | 1197 |

UV signed Q12 /4096, sin inversión V. Subida RGBA→ABGR/Morton de 8×8,
alfa `round(255*a/128)`, bilineal y clamp al borde. Mezcla ONE/ZERO, prueba
alfa desactivada y profundidad GEQUAL con escritura, conservando la proyección
de inspección. Los texeles de alfa cero se dibujan sin descarte ni mezcla.

El color neutro equivale a RGB de vértice PS2 128. **La iluminación dinámica
del juego no está implementada.** Se conserva el giro de presentación de
180° sobre X, la componente W y dos caras. Tampoco se afirma equivalencia
del filtro GS/PICA a nivel de píxel, mundo definitivo o daño/muerte.

## Separación de responsabilidades y recursos

- Dominio: validación de tres rangos contiguos, UV del vértice expandido y
  opción de luz neutra; sin acceso a archivos ni SDK.
- Adaptador de archivos: SCT1 acotado, cabecera/tamaño/CRC, vínculo al CRC SCM
  y rechazo de alfa fuera de 0–128 antes de iniciar GPU. CRC incremental
  compartido evita duplicar algoritmo o reservar otro payload de 3 MiB.
- Renderer: tres texturas, tres draws y un buffer dinámico de vértices;
  espera SYNCDRAW antes de reescribir y libera tras finalizar la GPU.
- Preparador Python: hashes de CM-T5, malla, CT-T3 y referencia CT-T4, identidad
  de recursos, correspondencia de las 15 submallas y perfil GS admitido.
  Dos fuentes A/B producen los mismos archivos y metadatos.

SCT1 ocupa **3.145.796 bytes**. Texturas GPU: **3.145.728 bytes** persistentes;
staging CPU: otros 3 MiB solo durante carga. Vértice de 36 bytes,
**120.204 bytes por cuadro**, sin nuevas reservas ni lecturas de archivos
durante reproducción. El visor anterior conserva su aplicación/carpeta;
al recompilarlo comparte ahora el vértice de 36 bytes, aunque no usa texturas.

## Validación

| Comprobación | Resultado |
|---|---|
| Nuevos tests Python CT-T5 | 39 aprobados; conversión, hashes, grupos, alfa y entrega exclusiva |
| C++ Release | 298 aprobados |
| C++ ASan/UBSan | 298 aprobados |
| SCT1 entre Python y C++ | Archivo válido, 21 corrupciones y fallos de lectura/cierre |
| Subida GPU | 262.144 texeles sintéticos asimétricos contrastados; alfa 0/64/128 y rangos inválidos |
| SDK simulado | Fallos por etapa y por textura, orden de binds/draws, liberación y 1.000 cuadros sin nuevas reservas SDK |
| ARM | Nuevo visor y regresión de personaje, vidrio y animación compilados |
| Azahar 2126.2 Vulkan | Texturas/dibujo, A/R/L, cámara, zoom, reset y START comprobados |
| New 2DS XL | Fallida: caballo ausente y bloqueo; Q12=0, GPU previous=0,00 ms |

La suite Python completa ejecutó 4.506 casos: 4.500 pasaron y seis del
supervisor fallaron porque el sandbox bloqueaba `/bin/ps`. La repetición
autorizada de sus 23 casos pasó fuera del sandbox. Cuatro pruebas adicionales
de identidad elevan el conjunto a 4.510 casos cubiertos entre ejecuciones;
no se presenta como una única ejecución completa sin restricciones.
Cobertura Python acumulada: 98,36 % de líneas y 96,67 % de ramas; gate
aprobado. Encoder SCT1: 100 %; preparador: 98,48 % de líneas y 96,43 % de
ramas. Ruff, formato, contratos del repositorio y `git diff --check` pasan.

El SDK se fija en `toolchains/devkitpro-image.txt`; la compilación local usa
una copia solo de código y contenedor sin red. El pipeline incorpora
`scripts/build_character_material_probe.sh` y publica únicamente código y
metadatos del build. No se ha ejecutado CI remoto en esta sesión.

La primera apertura de Azahar mostró MISSING por copiar inicialmente a la
SD del perfil estándar. Se trasladaron los archivos al perfil portátil del
proyecto y se verificaron nuevamente por hash. El error permitió salir con
START. Las capturas posteriores pertenecen al build final.

Se mantuvo reproduciendo durante 149 segundos entre comprobaciones, con
contador activo y sin error observado; no fue una captura continua de vídeo.
Lecturas puntuales mostradas: Skin CPU 5,84 ms, Submit+wait 7,64 ms y GPU
previous 0,25 ms, únicamente del emulador. START regresó a la lista.
Pausa/reinicio mostraron Q12=0; R avanzó a 3686. La cámara se movió manteniendo
ese contador, y B restauró el encuadre. Los tiempos observados en emulador
no son un benchmark físico. HOME/tapa se conservan mediante la aplicación
existente y sus pruebas host; requieren la nueva confirmación física.

## Entrega privada

Directorio: `/Users/germancontreras/sh3-private-data/f03-02-3ds-character-material-v1/`.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| animation.san | 1248 | `8adbe5e59f05923c65d0813e2acfc6d88c9364db1d7e18641bdec27f6ac89381` |
| character.scm | 47670 | `3ccf6bbbce726ccedd0b481cd7667ebe95213acc1a2f1dcdf3b27c5a2f792479` |
| character.sct | 3145796 | `9b1ab590c10a8ce2de0b0fa333dc9b7339a7ab64d5650e543c426c2e29932bf3` |
| sh3_character_material_probe.3dsx | 275716 | `6363f9189b13b645bf1d06d0296fd921258e965a57d14a8bd38422bb68281409` |
| sd-card.zip | 3487279 | `6d90662458c348c98f98e13184a339e3bd198b3c76495575d38b44416d82131b` |

Preparación reproducible: `python -m tools.pipeline.prepare_character_material_probe --help`.
El manifiesto registra fuentes, build, rangos y hashes. Los datos originales
y capturas permanecen fuera del checkout y CI. Evidencia privada en
`f03-02-character-material-native-check-v1/`; resumen local sin imágenes en
`reports/local/f03-02-character-material-inspection-v1.json`.
Manifiesto SHA-256: `41478d3d6056a06ba07865a3966c390e24bead7d57b3e0e29e79d79d0d354211`.
Recibo UI SHA-256: `8d7905c33b9ba1b1a702f490a7d0712b86f2003bbf09f01d63ca316c4cad7983`.

**Entrega física posterior:** el usuario conectó la SD «NO NAME» y solicitó
la copia. Se copiaron seis archivos, 3.485.367 bytes, a
`/3ds/sh3_character_material_probe/`, verificando tamaños y SHA-256 mediante
lectura posterior. Los otros visores se conservaron y la SD se expulsó
correctamente. Comprobante privado `f03-02-character-material-native-check-v1/sd-copy.json`,
SHA-256 `0e2f8ab78c8f87b9de1ace524b2091eab3b14b4a90db810f30c8d1ebb4598966`.
La prueba posterior del usuario falló: no se renderizó el caballo y tuvo que
apagar la consola. La foto confirma este build, Q12=0, Sample=0 y lecturas
Skin CPU=16,53 ms, Submit+wait=16,98 ms, GPU previous=0,00 ms. No son un
benchmark de reproducción. El resultado de Azahar queda como evidencia
limitada de emulación. Se prepara la corrección **CT-T5f** y se mantiene
abierta entonces la repetición física de CT-T5e. El reemplazo
[ced27c955e41 y la regresión del shader](f03-02-character-material-gpu-fix.md)
ya superó la repetición funcional en consola comunicada por el usuario:
texturas, Q12, 60 segundos sin bloqueo, controles, START, tapa y HOME.
Los tiempos del build corregido siguen pendientes en CT-T5e.2.
