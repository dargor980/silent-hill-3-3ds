# HG-T5 — Entrega identificada y protocolo de giros

2026-10-30. **HG-T5 completada en preparación de entrega**, build
**0188790baedd**. Paquetes privados A/B idénticos, releídos y verificados;
[protocolo de consola](../compatibility/heather-turns.md) incluido en ambos.
Instalación en SD verificada y tarjeta expulsada de forma segura.
[Prueba funcional de HG aceptada según el usuario](../compatibility/heather-turns-results.md),
con resultados por caso y límites de las lecturas registrados.
Las mediciones/pruebas adicionales de HM-T5 y pared 60 siguen aplazadas.

## Identidad y procedencia

Se reutiliza exactamente el ARM de [HG-T4.4](f06-02-heather-turns-resources.md),
sin recompilar ni modificar el código de consola. Se verifican sus seis
checksums, ELF32 ARM, ID embebido en ELF/3DSX, SDK fijado y la identidad
calculada de los 126 archivos fuente de engine/CMake.

Las entradas privadas de `/Users/germancontreras/sh3-private-data` son:

- `heather-room-material-runtime-v2-copy-a` y `-copy-b`, manifiesto SHA-256
  `862ca8e110892fa00820578bf46545ad43803934fac3288acb096612ae851af0`.
- `heather-turns-a-v1` y `heather-turns-b-v1`, manifiesto SHA-256
  `a33d89733b506a286e11c00d3f8553f7a2c179f10bc2d08e5baebadfb9f0ca30`.

Se releen sus inventarios completos, hashes y manifiestos pendientes cuando
existen. El oráculo estructural verifica SRI2 perfil 2, cinco clips y 78 muestras.
Las trece texturas compartidas coinciden byte a byte. Los 26 archivos de
runtime resultantes coinciden con los auditados en HG-T4.4.

Frente al runtime HM, solo cambian `heather.sri` y los cuatro bytes de su CRC
en `scene.srr` (offset 20). Se conservan mapa, materiales, orden/visibilidad,
texturas, spawn, yaw, suelo y las 32 cajas. El presupuesto sigue siendo
51824452 bytes, **49,42/64 MiB**; no es una nueva medida física.

## Paquetes

Copias nuevas y exclusivas:

- `/Users/germancontreras/sh3-private-data/heather-turns-3ds-0188790baedd-v1-copy-a/`
- `/Users/germancontreras/sh3-private-data/heather-turns-3ds-0188790baedd-v1-copy-b/`

Cada carpeta tiene 29 archivos para SD, `sd-card.zip`, `manifest.json` y su
enlace `.manifest.pending.json`: 32 entradas, directorio 0700 y archivos 0600.
El ZIP contiene 30 entradas: los 29 archivos bajo `3ds/sh3_heather_room/`
y `SHA256SUMS` en su raíz. Payload SD: **29364875 bytes**. Basta instalar A o B.

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| `sd-card.zip` | 29372356 | `04b151e9cc1bc66cb97475260c82ec78257b0300638e72c82037d7d3d388da62` |
| `sh3_heather_room.3dsx` | 238360 | `8c2612a3a203cb7e6a8b1995c9d0aade0a31112e43a437b49ccaa26b016d9f2d` |
| `heather.sri` | 310356 | `c275f3bbfc7cc5dcb45af738460b2c71b184aad4f90973e5f0b22e7725b24865` |
| `scene.srr` | 596 | `c30d89193c3fe668b41e3522953792a793e4d46e956c05f930e85426f087e660` |

Manifiesto A/B idéntico, SHA-256
`4c081f73cafd5e279d701a0e571bf8b8360fe765ea2263cf8778d40533e936bd`.
No incluye ELF, fuentes originales ni informes privados en la carpeta SD.
ELF y paquetes del SDK se conservan en `build/heather-turns-resources/arm/`.

El adaptador local `build/heather-turns-delivery/prepare.py` reutiliza
`verified_build`, `PinnedInputs`, `inspection_archive` y `_write_bundle`.
Exige los pins de HG-T4.4 y las lecturas anteriores; no flexibiliza el
preparador histórico de HM. La publicación es exclusiva, sin sobrescribir
entregas anteriores. Relee cada salida y sus fuentes antes de publicar el
manifiesto; al terminar vuelve a verificar ambas copias y fuentes.
La atomicidad es por copia, sin transacción entre directorios ni garantía
de durabilidad frente a pérdida de energía.

## Validación del paquete y protocolo

- ZIP determinista al invertir el orden del diccionario de entrada;
  fechas/permisos fijos, conjunto exacto, sin nombres duplicados, CRC y los
  29 SHA-256 internos verificados. A/B y manifiestos completos releídos.
- **22 pruebas del empaquetador existente aprobadas**, con fuentes inventadas:
  corrupción, identidad, enlaces, cambios durante publicación y fallos A/B.
- ZIP A/B extraído, archivos releídos y ejecutados por los binarios host
  actuales Release y ASan/UBSan: **ocho ejecuciones aprobadas**.
  Cuatro ejecuciones de runtime recorren las cinco acciones a 25/60/143 Hz
  (200 pasos por replay), con render, contactos, pausa, HID/APT y limpieza.
  Cuatro ensayos de recursos suman **2048 actualizaciones sin asignaciones**,
  liberación completa y el mismo pico rastreado de 34252665 bytes de HG-T4.4.
- El validador local `check_protocol.py` lee las tablas numéricas del propio
  Markdown y las coteja con el controlador C++ existente: **123 pasos y
  69 puntos de tabla por configuración**, Release y ASan/UBSan coincidentes.
  Comprueba ambos ciclos/retornos, inversiones y cancelación de intención.
  Esas pruebas usan poses/contactos sintéticos y no acreditan pulsaciones
  físicas ni el comportamiento de HOME/tapa en la consola.

El protocolo pide Build, estado, Step, Clip, Q12, R raw, R steps y Error,
más observación visual. Distingue contador siguiente de pose visible y
destino de mezcla de estado estable. Explica que L no borra los contadores
de R y usa sus diferencias desde la base. Los ciclos llegan a Step 24 y
vuelven a espera en Step 33; el wrap muestra Q12 39168→512→2816.

Incluye pausa dentro de una mezcla HG, R sostenido, cambio de sentido por
espera, cancelación de un objetivo, conservación de caché tras HOME/tapa,
reinicio, cinco acciones en reproducción normal y salida. Las pruebas
generales pendientes de HM-T5 permanecen separadas y aplazadas.

## Evidencia y siguiente paso

Informe local: `reports/local/heather-turns-delivery-0188790baedd.json`, SHA-256
`afc34faeb62addceb5116cef83a8b449a304409b61590dcb51c363eaf43b145d`.
Protocolo validado: `reports/local/heather-turns-console-protocol-v1.json`, SHA-256
`6f9174f13c27d8169d290a3f19644da2275bac4368a48d2766c574166d0d2a09`.
JUnit y logs por copia/configuración quedan en `build/heather-turns-delivery/`.
El Markdown empaquetado tiene SHA-256
`4553d9e6e22b576e2483485e9ee5e3d9194fa3c63f4db35f646bc0301f2e6b94`.
La evidencia previa HG-T4.4 se conserva sin modificar.

La preparación inicial no copió a SD ni ejecutó ARM en emulador/consola.
La instalación posterior solicitada por el usuario se registra a continuación.
La prueba posterior de `0188790baedd` está registrada en
[resultados físicos](../compatibility/heather-turns-results.md): giros/retornos,
inversiones, cancelación, pausa/R, HOME/tapa, L, cinco acciones en RUNNING y START.
La aceptación es funcional para los casos comunicados. No se cierran F06.02
global, G04/G05 ni las mediciones adicionales de HM-T5.

## Instalación en SD verificada

2026-10-30, 23:10:25 UTC. Se identificó la SD `NO NAME`, UUID
`2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`, y se cotejó la instalación anterior
`c3aae59d1a70` con su recibo antes de escribir. Fuentes A/B, manifiestos,
ZIP y ejecutable coincidieron con los hashes fijados arriba.

Se instalaron los **29 archivos, 29364875 bytes**, en
`/3ds/sh3_heather_room/`. La copia temporal se verificó antes de sustituir
la carpeta; todos los archivos instalados se releyeron y cotejaron por
SHA-256 después de sincronizar. El visor `/3ds/sh3_heather_probe/` permaneció
idéntico. La carpeta anterior completa, incluidos sus auxiliares de macOS,
se conservó y verificó en:

`/sh3-room-install-0188790baedd-20261030T231025Z/previous-c3aae59d1a70/`.

`diskutil` confirmó la expulsión de `disk12`; el volumen dejó de estar montado.
Recibo: `reports/local/heather-turns-sd-delivery-0188790baedd.json`.
El instalador reproducible queda en
`build/heather-turns-delivery/sd-install/install_sd.py`.
Los manifiestos de preparación conservan sus indicadores históricos;
el nuevo recibo acredita instalación y expulsión, no aceptación física.
HM-T5 adicional y pared 60 continúan aplazadas.

## Prueba física comunicada

Después de la instalación, el usuario confirmó la identidad en pantalla y
los puntos de Step/Clip/Q12 de ambos giros, retornos a espera e inversiones.
El objetivo izquierdo cancelado no reapareció. Pausa, R sostenido, reinicio
y conservación de mezcla tras HOME/tapa coincidieron; el último reinicio
dejó Step 0/Clip 101/Q12 0 y R steps 129. Confirmó también Step creciente en
RUNNING, ausencia de errores/saltos y retorno normal por START.

Recibo independiente: `reports/local/heather-turns-physical-0188790baedd.json`.
El [detalle](../compatibility/heather-turns-results.md) conserva las lecturas
R raw distintas de R steps y los puntos no transcritos individualmente.
No se inventan causas de las señales brutas ni medidas de rendimiento/memoria.
