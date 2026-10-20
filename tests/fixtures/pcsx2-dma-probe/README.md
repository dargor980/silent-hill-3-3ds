# Harness DMA del proveedor fijado

`harness.cpp` contiene únicamente fixtures y dobles propios. No compila solo:
requiere ocho archivos `.inc` generados literalmente desde la copia privada
instrumentada de PCSX2. Esos archivos conservan la licencia GPL-3.0+ del proveedor
y no se incluyen en este repositorio.

Los cuerpos son `memcpy_from_spr`, `MemCopy_WrappedDest`, `hwMFIFOWrite`,
`sifFifo::read`, los dos `WriteFifoToEE` de SIF0/SIF2,
`IPU_Fifo_Output::read` y `vif1TransferToMemory`. Se colocan en la etapa privada con
los nombres indicados en los `#include`; no se reescribe su contenido.

El pipeline local compila este archivo con `lifetime.cpp`, `physical_writes.cpp`,
los includes del observador, `tests/cpp` y la etapa privada. Ejecuta C++20 ON/OFF
y ON con ASan/UBSan, `-Wall -Wextra -Werror`, y exige 54 casos y el mismo resumen
de efectos. Los wrappers comprueban avisos antes de las copias y llaman al puente
real; las dependencias de VM son dobles explícitos. No requiere ISO ni BIOS.

El detalle, hashes, límites y distinción frente a una VM real están en
[SRC67](../../../docs/execution/f02-07-dma-write-probe.md) y su
[evidencia](../../../docs/compatibility/dma-write-probe-evidence.json).
La CI pública no genera estos cuerpos ni ejecuta este harness privado.
