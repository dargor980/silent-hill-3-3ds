# F02.07 — Servicio IO en el candidato PCSX2

Fecha: 2026-10-19. Contrato [RT01–RT07](../../schemas/runtime-service-v1.md).
Evidencia [SRC117](../compatibility/runtime-service-evidence.json).

## Resultado

Se completan **RT-T1/RT-T2 / RS-T3b.1–2**: servicio IO propio, hooks de pausa y
cierre en Qt, candidato enlazado y firmado, y control sin VM. El candidato final
también inicializa una VM pausada con la ISO europea y BIOS privada, alcanza el
trabajador nativo, rechaza el inventario y termina con código cero.

**No hay muestras aceptadas ni captura. RT-T3 / RS-T3 / RB-T3 / DW-T3 siguen
pendientes.** El rechazo observado es `inventory`, con `origins=10` (`preflight`),
`prepared=0` y `sampled=0`. No identifica todavía qué condición interna del
preflight falló; no se atribuye a una imagen o escritor específico.

## Implementación y ciclo de vida

El servicio copia endpoint, manifiesto, hashes y disparador desde configuración
local antes de crear IO. La identidad del padre se fija localmente. Conexión
no bloqueante, autenticación nativa completa, cola CPU y muestras comparten un
deadline de cinco segundos. El disparador de pausa tiene una espera inicial
cancelable de 60 s; no pausa la VM ni renueva el plazo posterior.

IO compone la fábrica nativa y la sesión existentes usando la vinculación del
ticket real. Finaliza con tres respuestas como máximo o el primer rechazo.
Los errores de construcción recorren la misma limpieza: cancelar, cerrar canal,
esperar retirada CPU, unir DW y destruir recursos. El frontend solo une IO
después de su terminación y conserva CPU activo hasta entonces.

La copia privada integra `Host::OnVMPaused`, el arranque optativo y el epílogo de
`main`. El código del servicio es independiente de Qt y del estado interno de
VMManager; usa el frontend de cola ya existente. Las pruebas sustituyen ese
puerto, no el servicio ni el socket. La fábrica/protocolo/transporte mantienen
sus responsabilidades.

## Build y pruebas

- **2.132 ejecuciones nativas:** 533 por Debug, Release, ASan/UBSan y cobertura.
  Incluyen 16 escenarios nuevos; el test histórico de reloj real se compila
  pero sigue excluido de ejecución como en SRC115.
- **16 casos adicionales con TSan arm64**, sin diagnóstico de carreras.
- **QtHost completo ON/OFF**, con MOC propio para cada modo. OFF no introduce
  referencias al observador. El arreglo final regenera MOC y recompila QtHost ON.
- **113 tests originales de PCSX2** pasan en el build nuevo. La reparación
  posterior modifica solo el cierre Qt y reutiliza los componentes ya probados.
- Servicio: **146/157 líneas (92,99 %), 126/182 ramas (69,23 %)**. No se afirma
  un gate 80 % de ramas para este archivo. LLVM conserva el aviso agregado de
  68 funciones con datos incompatibles entre ejecutables.
- Los controles de repositorio/supervisión, Ruff y `git diff --check` se
  verifican al publicar. La CI remota, Linux y 3DS no se ejecutan en esta etapa.

El build completo parte de **26,63 GiB libres**, tarda **356,882 s**, usa dos
jobs y respeta IB02. El enlace de reparación parte de **22,04 GiB** y tarda
**28,163 s**. Ambos usan supervisor, suelo de 10 GiB y límite de etapa de 8 GiB.
Las baterías pequeñas usan un máximo de 512 MiB por etapa.

La fuente inicial privada tiene **3.040 archivos**. Se conserva completa y una
segunda copia cambia únicamente QtHost para reparar la salida. El nuevo enlace
reutiliza **469 entradas verificadas** y reemplaza un objeto QtHost. Los paquetes
anteriores, fuentes, objetos y fallos permanecen disponibles.

El paquete final conserva **200 archivos regulares y 42 Mach-O x86_64**. Se
verifican firma ad hoc, resolución de frameworks y ausencia de dependencias
hacia el prefijo privado/Homebrew. SHA-256 del ejecutable probado:

`9e4037c2c7c4c5241900f70dc07e0fddc02e4c69e7d186a172f7b7bb688af53d`

## Fallos conservados y reparaciones

1. El medidor encontró un temporal de CMake que desapareció durante `stat`.
   El supervisor cerró el proceso; una etapa nueva tolera solo esa desaparición.
2. Una prueba detectó `reason=0` cuando se cancelaba entre publicación CPU y
   construcción de DW. Se corrige a `cancelled`; las pruebas finales pasan.
3. Dos controles sin VM usaban `-batch/-nogui` sin archivo de arranque. PCSX2
   mostraba un error modal antes de iniciar el servicio. La pila y el código
   privado identifican esa validación. El control corregido usa el frontend normal.
4. La ruta PINE excedía el espacio disponible en el socket Unix. Los intentos
   que solo cambiaban `XDG_RUNTIME_DIR` no la corrigieron: macOS usa `TMPDIR`.
   El launcher final fija ambas variables a un directorio temporal privado
   corto. La repetición con VM observa `pcsx2.sock.30117` antes de consultar al
   servicio y no registra errores de bind.
5. El cierre con VM encontraba la confirmación modal de apagado. Se desactiva
   solo en los perfiles de prueba, junto con tarjetas de memoria y guardados.
6. Aun sin diálogo, `QApplication::quit()` entraba en `NSApplication terminate:`
   y `exit`, con SIGABRT durante finalización estática. La reparación usa
   `QCoreApplication::exit()` en UI y detiene el timer, retornando al epílogo
   que limpia IO y CPU. Las pilas e informes de los tres fallos quedan privados.
7. El primer objeto de reparación incluyó el MOC de la ruta anterior, duplicando
   declaraciones. Se conserva el fallo y se regenera MOC en otra etapa.
8. El primer paquete reenlazado carecía de LC_RPATH y falló antes de arrancar.
   Otro paquete añade la ruta de frameworks, verifica resolución y repite firma,
   testconfig, control sin VM y VM. No se cuenta el fallo como arranque válido.

## Ejecución real y límite pendiente

El candidato final pasa `-testconfig`. Sin VM, el servicio devuelve `unavailable`
sin adquirir inventario y cierra correctamente. Con VM, los logs privados
identifican **SLES-51434, revisión 1.02, CRC 5088CCDB**, BIOS Europa 2.00, inicio
de subsistemas, cero segundos de juego y liberación de memoria al salir.

El rechazo del inventario se reproduce en los cinco arranques con VM de esta
etapa. `cpu_pending` registra si CPU aún estaba pendiente al empezar la limpieza:
es uno en cuatro arranques y cero en el primer arranque del candidato reparado;
el servicio espera su retirada antes de terminar. `clean=1` del servicio no
equivale a salida correcta del proceso: los primeros tres fallan y los dos del
candidato final terminan con código cero. La última repetición corrige además
PINE. Se conservan todas las observaciones.

Esto valida la conexión y el cierre del rechazo en VM, no la entrega positiva,
la jugabilidad ni la matriz completa de lifecycle/escritores. Los flags de JIT,
caché, DMA y escritores no acreditados conservan su semántica anterior; no se
habilitan modos ni capacidades de captura.

**Siguiente tarea RT-T3a:** desglosar el fallo `preflight` en rango de caché,
lectura/header, pertenencia declarada y estabilidad del loader, con observaciones
locales acotadas y pruebas negativas. Después repetir inventario positivo y la
matriz de lifecycle/gates con el candidato exacto. No aumentar límites ni admitir
imágenes desconocidas para convertir el rechazo en éxito.
