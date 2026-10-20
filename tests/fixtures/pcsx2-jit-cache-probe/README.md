# Harness de caché y entrada JIT

El fixture es propio. Requiere `cache.inc`, `vtlb-scalar.inc`, `vtlb-128.inc` y
`jit-entry.inc`, extraídos literalmente del proveedor fijado instrumentado y
conservados en la etapa privada. Los cuerpos GPL-3.0+ no se distribuyen aquí.

Compilar con C++20, `lifetime.cpp`, `physical_writes.cpp`, includes del observador,
`tests/cpp` y la etapa privada, con `-Wall -Wextra -Werror`. Ejecutar ON, OFF y
ON con ASan/UBSan; exigir 70 casos y el mismo resumen de efectos. No usa ISO/BIOS.

Mapa, registros, logger, fastjmp y callback compilado son dobles. El callback
preexistente demuestra que la barrera no depende de generarlo después de conectar;
no representa un bloque PS2 emitido por el JIT. El bypass demuestra que no es
seguro admitir armado durante un bloque ya activo. La captura real sigue cerrada.

Ver [SRC68](../../../docs/execution/f02-07-jit-cache-probe.md) y
[evidencia](../../../docs/compatibility/jit-cache-probe-evidence.json).
La CI pública no genera estos fragmentos ni ejecuta el harness privado.
