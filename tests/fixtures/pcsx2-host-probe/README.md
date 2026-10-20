# Fixture propio para escritores host de PCSX2

`harness.cpp` contiene datos, oráculos y dobles propios. Requiere catorce
fragmentos `.inc` extraídos exactamente de la copia privada fijada del proveedor;
no contiene sus implementaciones ni bytes de Silent Hill 3.

Inputs privados: `ram-write`, `safe-write`, `safe-read`, `safe-compare`,
`parse-args`, `load-first`, `load-second`, `deci`, `ra-write`, `tlb-unload`,
`tlb-layout`, `debug-writes`, `idempotent-scalar` e `idempotent-bytes`.
El manifiesto registra fuente, hash del archivo y hash del fragmento. La tabla
usa la estructura exacta del proveedor; todos sus registros son sintéticos.

Los 85 escenarios se ejecutan con observador ON, OFF, ON con ASan/UBSan y
fragmentos de la copia anterior con OFF. Comprueban memoria, retornos, registros,
avisos anteriores al efecto y ramas sin escritura. Los cuatro resultados deben
ser iguales por sus oráculos y resumen de efectos normalizado.

Son dobles explícitos el mapa físico/virtual, CPU, logger, VMManager, disco,
formateo de rutas, DMA y validación de direcciones del depurador. `memWrite32`
del arranque delega en el harness a la hoja RAM real; no simula handlers ni caché.
Se prueba el callback RAIntegration como función aislada, no su aplicación Windows.
Las hojas utilizadas por PINE se ejecutan; su parser, socket e hilo no se ejecutan.

La compilación usa C++20, `-Wall -Wextra -Werror`, el núcleo y puente reales,
sin relajar advertencias. La evidencia privada fija comandos y resultados.
La CI pública mantiene las pruebas portables y no ejecuta este harness sin sus
fragmentos privados. No constituye una prueba de VM, concurrencia, admisión de
modos, ciclo de vida completo ni ejecución en New Nintendo 2DS XL.
