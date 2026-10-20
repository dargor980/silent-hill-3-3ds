# F02.07 / LP-C — Productores y dependencias de VU/GS

Fecha: 2026-10-18. Fuente: SRC75. Completa **CQ3-A / WD-T1**.
Contrato [WD01–WD12](../../schemas/worker-drain-v1.md).
Evidencia: [inventario y resultados](../compatibility/worker-producers-evidence.json).

## Resultado y alcance

El siguiente paso necesita excluir productores y obtener acuses de retención
de trabajadores. Encadenar WaitVU y WaitGS no proporciona ese contrato: ambas
interfaces retornan void, no cierran entradas y no tienen plazo de cancelación.
Además, GS puede ejecutar presentación ociosa después de señalar cola vacía.

Se revisa la copia SRC74 del commit
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, sin modificarla. Se verifican sus
2.955 archivos y se indexan 235 referencias léxicas en cuatro directorios:
149 GS, 71 VU y 15 GIF. Los metadatos fijan 43 archivos, incluidos soportes de
sincronización y UI. Las referencias incluyen definiciones y declaraciones;
**no son 235 productores independientes ni un grafo transitivo de llamadas**.
La tabla siguiente agrupa lo revisado e identifica explícitamente rutas abiertas.

Este lote entrega inventario, diseño y pruebas aisladas. No integra todavía
retenciones VU/GS, no cambia admisión y no ejecuta una nueva aplicación PCSX2.

## Matriz de productores

Las ubicaciones son relativas al proveedor fijado; líneas y hashes están en la
evidencia. «Requerido» describe CQ3-B/C, no una exclusión ya implementada.

| ID | Entrada y contexto | Efecto o dependencia | Exclusión o rechazo requerido |
| --- | --- | --- | --- |
| WP01 | CPU: Vif_Codes, Vif, Vif_Unpack, VU1micro y Memory → VU_Thread | ExecuteVU, VifUnpack, WriteMicroMem/DataMem, VI/VF, col/row reservan y publican trabajo VU; ExecuteVU también modifica estado CPU | Impedir antes de la operación completa, no solo en CommitWritePos; Execute desactivado no cubre escrituras host |
| WP02 | CPU: SaveStateBase::mtvuFreeze, reset y proveedores CPU | Reset cambia posiciones; carga repuebla memoria/registros; Open/Close cambian la vida del trabajador | Invalidar intento antes de transición; configuración MTVU=false no prueba hilo inexistente o cola vacía |
| WP03 | CPU: GIF/VIF/DMA/GS → Gif_AddGSPacketMTVU/Completed/Blank, PostVsyncStart | Paquetes GS, readAmount, buffers GIF y datos VSync; caso MTVU publica un marcador que GS deberá esperar | Cierre antes de cambios de buffer/contadores; no introducir un retorno void que pierda paquetes |
| WP04 | CPU: MTGS::InitAndReadFIFO | Ruta normal encola escritura por puntero y espera GS; modos unsynchronized/disabled hacen lectura directa o memset sin pasar por la cola | Cubrir también la entrada y los efectos directos; cerrar SendPointerPacket no alcanza |
| WP05 | CPU: Freeze, ResetGS, ApplySettings, GameChanged, captura y SPU2::UpdateSampleRate | Freeze retiene puntero del caller; reset puede alterar readpos; configuración/captura encolan AsyncCall y algunas esperan | Abortar/liberar retenciones antes de efectos o conservar solicitud completa; no diferir un puntero de stack fuera de su vida |
| WP06 | Eventos CPU Qt: resize, redraw, fullscreen/surfaceless, snapshot/captura | onDisplayWindowResized y redraw producen durante pausa; cambio de ventana/captura puede esperar GS | Conservar PINE mientras progresa su trabajo previo; después cubrir cada entrada tardía antes de efectos |
| WP07 | Host::RunOnGSThread del frontend Qt | Encola primero en CPU y después llama MTGS::RunOnGSThread | Distinguirlo de la llamada directa MTGS; revocación CB actual no libera futuras retenciones por sí sola |
| WP08 | UI: MainWindow::updateLanguage → QtHost::InstallTranslator | El bloque LocaleChanged llama MTGS::RunOnGSThread directamente; el bloque de fuentes de la misma unidad sí usa Host::RunOnCPUThread | Serializar la ruta directa por el propietario o diferirla con prueba; hasta entonces no acreditar único productor CPU |
| WP09 | Worker MTVU: ExecuteRingBuffer y Gif_Path | Escribe VU, ejecuta unpack/programas, completa paquetes y publica semaXGkick; puede esperar espacio GIF que libera GS | Dejar GS progresar mientras drena VU; después acuse VU ligado a generación y sin efectos posteriores |
| WP10 | Worker GS: MainLoop | Consume paquetes, ejecuta AsyncCall/Freeze/FIFO; espera semaXGkick y libera readAmount | Mantenerlo activo hasta completar VU; luego confirmar y conservar retención desde una frontera propia |
| WP11 | Worker GS: presentación ociosa y FullscreenUI | CheckForWork puede señalar vacío y seguir con presentación; UI renderizada puede encolar trabajo CPU y tomar locks | El acuse debe cubrir también presentación ociosa y reapertura del dispositivo, no solo readpos/writepos |
| WP12 | Achievements, ImGui/overlays, hotkeys, grabación y otros callbacks | Referencias a RunOnGSThread y callbacks CPU en múltiples unidades; sus raíces y restricciones no están cerradas globalmente | Rechazar rutas/configuraciones no cubiertas; inventario léxico no concede exclusión a estos escritores |
| WP13 | PINE, RDebug y accesos host directos | PINE tiene barrera propia; RDebug/otros escritores siguen desconocidos; pueden alcanzar efectos de memoria fuera de GS | Mantener PINE hasta el final; no promover RDebug ni other_writers_excluded |
| WP14 | GSDumpReplayer, GSRunner y ramas por plataforma | Fuentes alternativas de FIFO/VSync/carga y otros ciclos de vida | Permanecen fuera del perfil inicial Qt; su presencia se registra, sin extrapolar pruebas x86_64 a ARM64/3DS |

Las primitivas GS de preparación/publicación usan estado de paquete compartido
y documentan escritura desde EE; no proporcionan una cola de múltiples productores
protegida por mutex. Por eso WP08 es un impedimento para afirmar exclusión CPU,
no evidencia suficiente por sí sola de una carrera observada en ejecución.

## Esperas inversas y locks

| Dependencia observada | Evidencia del proveedor | Regla para el coordinador |
| --- | --- | --- |
| GS → VU | MainLoop, MTVUGSPacket: espera semaXGkick, liberando temporalmente s_mtx_RingBufferBusy2 | No detener VU antes de completar paquetes ya publicados |
| VU → GS | Gif_Path::RealignPacket/CopyGSPacketData → mtgsReadWait → WaitGS débil; GS reduce readAmount y retira paquetes | No retener GS mientras VU necesita liberar espacio |
| CPU → VU/GS | ReserveSpace/WaitOnSize, GenericStall, VSync, Freeze y WaitVU/WaitGS | No usar una cola de datos llena para enviar el control de retención |
| GS → UI | GSDevice::AcquireWindow → Host::AcquireRenderWindow; MainWindow conecta adquisición/liberación con BlockingQueuedConnection | Mantener UI disponible; no solicitar captura síncrona desde UI esperando a CPU/GS |
| GS → CPU, asíncrona en rutas revisadas | FullscreenUI e ImGui llaman Host::RunOnCPUThread | Un despacho posterior es un productor potencial; estas rutas no prueban ausencia universal de esperas síncronas |
| GS → locks host | FullscreenUI/Settings toman settings, Achievements y GameList locks; GS MainLoop usa RingBufferBusy2 | Ninguno debe cruzar la espera del coordinador; el mutex breve de CooperativeGate tampoco cruza callbacks |

El orden **VU→GS** es de confirmación de retenciones. Durante el primer drenaje
ambos trabajadores deben poder ejecutar trabajo previo. Detener GS primero puede
impedir que VU libere espacio; detener VU con marcadores pendientes puede dejar GS
esperando semaXGkick. La liberación debe habilitar GS antes de productores VU.

## Qué no prueban las APIs actuales

- Paused se publica en SetState antes de sus esperas. No prueba fin de efectos.
- IsDone compara posiciones VU; no cierra productores ni acredita generación.
- WorkSema::WaitForEmpty retorna false si murió el trabajador y permite un solo
  waiter. No acepta deadline; añadir otro hilo auxiliar que también espere vacío
  incumpliría ese contrato.
- WaitVU ignora ese bool. WaitGS retorna sin resultado si GS está cerrado y usa
  pxFailRel si muere durante la espera normal. La variante débil puede terminar
  tras progreso parcial de path1. Ninguna variante sirve como acuse cancelable.
- GS MainLoop puede señalizar vacío mediante CheckForWork y luego presentar;
  al cerrar también iguala readpos/writepos y mata el semáforo. Igualdad no
  demuestra consumo exitoso ni que el trabajador permanecerá detenido.
- Un AsyncCall al final de la cola confirma solo su prefijo. Los productores
  posteriores y la presentación ociosa seguirían abiertos.

## Diseño que debe implementar CQ3-B/C

El propietario CPU conservará el cierre PINE de SRC74 durante todo el intento.
Tras drenar reservas previas debe controlar las entradas WP01–WP08 antes de
solicitar retención a VU y después a GS. Cada acuse necesita ID, generación,
publicación de efectos y estado explícito. El controlador consulta progreso y
cancela; no llama las esperas void actuales para inferir éxito.

El despacho Qt requiere trabajo adicional: un Activity actual invalida una
frontera, pero no invalida automáticamente PineDrain ni libera futuros workers.
La integración deberá interceptar callbacks tardíos antes de efectos, cancelar
y liberar, o conservarlos para después. No es correcto retener GS/VU y seguir
ejecutando callbacks arbitrarios con el event loop de SRC74. Tampoco es correcto
descartarlos ni bloquear el CPU en una espera circular. El canal de control y
las entradas concretas se implementarán y ensayarán en CQ3-B.

Se mantienen los rechazos de VIF dinámico y las condiciones desconocidas del
sampler. Este inventario no transforma un estado de configuración en exclusión,
ni acredita el ciclo de vida completo del servidor PINE, recursos o memoria.

## Validación y custodia

El [probe](../../tests/fixtures/pcsx2-worker-drain/README.md) ejecuta siete
fragmentos exactos: clase WorkSema, cinco métodos y WaitVU. Sus cinco escenarios
pasan en normal y ASan/UBSan: publicación de efectos, muerte, actividad ociosa,
productor posterior y descarte de fallo de WaitVU. Se usa Apple Clang 21,
x86_64 y C++20. No se observan fallos de compilación, assertions ni sanitizadores.

KernelSemaphore se reemplaza por semáforos C++20 con barreras deterministas;
el worker y los efectos son propios. Se validan cuerpos del proveedor aislados,
no MTGS::MainLoop, el renderer, los semáforos nativos, Qt ni la VM completa.
Se conserva una etapa privada nueva, con supervisión de 120 s para compilar y
15 s para ejecutar, reserva de 10 GiB y presupuesto de etapa de 256 MiB.

La auditoría de custodia SRC74 se repite y obtiene exactamente sus 22.800 bytes
y SHA-256 `ac4fd51ef450c136235c917a0015f1c964bbbbc49e9c492da086904654323c07`.
Esto vuelve a verificar las once copias, artefactos y snapshots anteriores;
no reejecuta los tests históricos. Dos auditorías SRC75 comprueban el inventario,
los fragmentos, recibos, binarios y fuentes propias con resultados idénticos.

No cambia código productivo, CMake ni pipelines. El CTest de 110 casos por preset
y la suite Python no se repiten para este lote; sus resultados anteriores no se
presentan como ejecuciones nuevas. La CI pública conserva sus comprobaciones
de documentación/custodia, sin requerir el proveedor privado. El probe no entra
en ella. CI remota, enlace PCSX2 y consola siguen sin validación en este lote.

## Siguiente tarea

CQ3-A queda completada en el alcance de inventario, riesgos y contrato.
**CQ3-B / WD-T2** debe implementar propiedad persistente de PINE, entrada de
productores, tratamiento de callbacks Qt/UI y canal de control. CQ3-C añadirá
acuses VU/GS; CQ3-D/CQ-4 cerrarán integración y coste antes de AD-3.
