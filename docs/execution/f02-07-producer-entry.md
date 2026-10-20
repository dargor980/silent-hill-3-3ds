# F02.07 — Entradas productoras CPU y cambio de idioma (SRC77)

Fecha: 2026-10-18. Completa CQ3-B/B2 y EP-T1–T3 del
[contrato EARS EP01–EP07](../../schemas/producer-entry-v1.md).
El intento se cancela antes de efectos en 38 entradas revisadas; la operación
original continúa. LocaleChanged pasa por CPU antes de publicar a GS.
CQ3-B global y la retención real VU→GS siguen pendientes.

## Cambio y responsabilidades

Nueva copia privada del proveedor fijado en
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, derivada de SRC76.
Solo cambian `pcsx2/MTGS.cpp`, `pcsx2/MTVU.cpp` y
`pcsx2-qt/Translations.cpp`; los 2.957 archivos de SRC76 se conservan.
Parche privado SHA-256:
`d24af5aef1ffdb6927de4253882911af95411d9625bf1f25fbf42752a568a2ea`.

Se reutiliza el puente CPU de SRC76 sin cambiar sus controladores. MTGS/MTVU
notifican al principio del cuerpo; RetainedDrain decide y conserva PINE cerrado
hasta terminar release. El callback tardío aborta la observación y continúa
su trabajo. No se añaden locks, reservas de cola ni otra autoridad de estado.
Las reservas anteriores de PINE pueden progresar antes de iniciar la fase
posterior. Un aviso en otro hilo no manipula el propietario CPU.

| Archivo | Entradas instrumentadas | Primeros efectos cubiertos por posición |
|---|---|---|
| MTGS | StartThread, ShutdownThread, WaitForOpen, WaitForClose | Flags, arranque/cierre y esperas |
| MTGS | ResetGS, PostVsyncStart, InitAndReadFIFO, WaitGS, Freeze | Reset, preparación de paquete, escritura FIFO directa, notificación/espera y sincronización |
| MTGS | RunOnGSThread, GameChanged, ApplySettings, ResizeDisplayWindow, UpdateDisplayWindow | Captura de configuración, asignación/publicación de callback |
| MTGS | SetVSyncMode, UpdateVSyncMode, SetSoftwareRendering, ToggleSoftwareRendering, SaveMemorySnapshot, PresentCurrentFrame | OSD, consulta, callback, resultado por referencia y presentación |
| GIF en MTGS.cpp | Gif_AddGSPacketMTVU, Gif_AddCompletedGSPacket, Gif_AddBlankGSPacket, Gif_MTGS_Wait | Preparación/copia, readAmount antes de envío y espera |
| MTVU | Open, Close, Reset, Get_MTVUChanges, KickStart, WaitVU | Ciclo de vida, writeback, notificación/espera |
| MTVU | ExecuteVU, VifUnpack, WriteMicroMem, WriteDataMem, WriteVIRegs, WriteVFRegs, WriteCol, WriteRow | Writeback antes de ReserveSpace, copia/publicación y actualización de ciclos |

Son 24 entradas MTGS/GIF y 14 MTVU. Se verifica automáticamente que el hook
precede toda instrucción original y que retirarlo recupera el archivo anterior.
Los helpers internos no se sustituyen por una falsa barrera. SetRunIdle y los
bucles de GS/VU requieren acuses de trabajador en CQ3-C. El hook no cubre efectos
al evaluar argumentos en el llamador ni rutas ajenas anteriores a estas entradas.

El aviso de idioma comprueba EmuThread en UI, GS abierto al despachar CPU y
FullscreenUI inicializada al ejecutar GS. El callback no captura widgets ni
espera al CPU/GS. Si la UI se destruye entre despachos se omite su actualización;
si se inicializa antes del despacho GS recibe el aviso vigente. Esta corrección
se aplica también con observador OFF y cambia intencionalmente la ruta histórica.
No representa una transacción con identidad de sesión o versión del idioma.

## Pruebas ejecutadas

- **Seis objetos reales:** MTGS, MTVU y Translations con ON/OFF; Apple Clang,
  x86_64, C++20 y configuración local fijada. Los símbolos de aviso están en
  MTGS/MTVU ON y ausentes en OFF. No se enlazó el frontend completo.
- **110 escenarios comunes por modalidad:** 22 operaciones × cinco fases,
  ejecutando cuerpos exactos en ON, OFF, ASan/UBSan y SRC76 OFF. Digest común
  `71852b6e507507ad`. Se verifican FIFO directo/encolado, ambas ramas GIF en el
  doble, readAmount, payloads VU, snapshot/freeze y callback demorado/destruido.
- **Seis escenarios de idioma por modalidad:** ausencia de EmuThread, cierre
  GS antes de CPU, destrucción UI antes de GS, entrega normal, inicialización
  tardía y callback con retención. El baseline ejecuta expectativas históricas
  explícitas; estos efectos distintos se excluyen del digest comparable.
- **Un caso adicional ON y ASan/UBSan:** hilo ajeno no retira el intento CPU;
  el propietario lo cancela después. No acredita exclusión del hilo ajeno.
- **Dos controles negativos:** mover el aviso después de readAmount y
  restablecer UI→GS directo. Ambos compilan y fallan en la aserción prevista.
  Las mutaciones están aisladas; no alteran la copia del proveedor validada.

El [fixture](../../tests/fixtures/pcsx2-producer-entry/README.md) ejecuta 16 de
las 38 entradas nuevas, los tres cuerpos de puente y slot/despacho CPU, más el
bloque LocaleChanged: 22 fragmentos exactos por copia. Los otros 22 hooks se
compilan y auditan por posición. RetainedDrain/PineDrain/gate/frontera son reales;
puerto de efectos, colas, registros, semáforos y operaciones GS/VU son dobles.
El puerto productivo continúa devolviendo rejected. No se ejecutó QtCore real
esta vez ni se usó el bucle completo de PCSX2.

Todas las compilaciones y pruebas positivas pasaron al primer intento. El primer
comando de auditoría usó Python del sistema y falló al importar pycdlib; se
corrigió invocando `.venv/bin/python`, sin instalar ni cambiar dependencias.
Los fallos intencionales de los controles negativos no son fallos del proveedor.

## Custodia y reproducción local

La auditoría verifica los inventarios de las trece copias privadas, parche,
posición de los 38 hooks, fragmentos, objetos, ejecutables y recibos. Repite
SRC76 con el mismo hash histórico y produce dos informes SRC77 idénticos.
La [evidencia pública](../compatibility/producer-entry-evidence.json) contiene
hashes y alcance; los informes completos están en `reports/local` y los scripts
locales en `build/f02-07-producer-entry`, ambos excluidos de Git.

Receta ejecutada, con la raíz privada previamente autorizada y sus dependencias:

```text
rtk proxy python3 build/f02-07-producer-entry/prepare.py
rtk proxy python3 build/f02-07-producer-entry/compile_private.py
rtk proxy python3 build/f02-07-producer-entry/make_harness.py
rtk proxy python3 build/f02-07-producer-entry/run_harness.py on
rtk proxy python3 build/f02-07-producer-entry/run_harness.py off
rtk proxy python3 build/f02-07-producer-entry/run_harness.py sanitize
rtk proxy python3 build/f02-07-producer-entry/run_harness.py baseline
rtk proxy .venv/bin/python build/f02-07-producer-entry/negative_controls.py
rtk proxy .venv/bin/python build/f02-07-retained-drain/audit.py f02-07-retained-drain-v1-src77-custody.json
rtk proxy .venv/bin/python build/f02-07-producer-entry/audit.py f02-07-producer-entry-v1.json
rtk proxy .venv/bin/python build/f02-07-producer-entry/audit.py f02-07-producer-entry-v1-repeat.json
```

La preparación exige destinos nuevos; no debe repetirse sobre las copias ya
creadas. Compilador limitado a 180 s, ejecución a 30 s, piso libre de 10 GiB y
presupuesto de etapa de 1 GiB. Son compilaciones de objetos/probes, no el build
completo. Se comprueban recibos de salida y cierre de procesos supervisados.

No se cambia CMake, el núcleo portable ni el workflow público. La batería
host de 120 CTest por preset sigue siendo evidencia histórica SRC76; no se
repite aquí, tampoco la suite Python completa, CI remota o compilación 3DS.
Se ejecutan los controles de repositorio, Ruff y whitespace después del cambio.
La CI pública conserva su independencia de estas fuentes privadas.

## Siguiente tarea

B3 debe cubrir eventos Qt tardíos antes de sus primeros efectos y proporcionar
un canal de control solicitar/consultar/liberar que no use el ringbuffer de datos.
Debe avanzar con cola llena y sin esperar CPU/UI ni retener locks necesarios por
trabajadores. CQ3-C implementará acuses VU→GS y presentación ociosa.
B4/CQ3-D/CQ-4 completarán reentrada, cierre, servidor y VM reales y coste.

No se admite ningún modo ni captura real: VIF dinámico, escritores ajenos y
ciclo de vida completo siguen sin acreditarse. Esta entrega prepara el tooling
host para observar cargas; no modifica el runtime Nintendo ni produce un port
jugable o nuevos eventos Read.
