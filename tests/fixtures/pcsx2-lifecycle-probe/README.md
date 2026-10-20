# Fixture propio de ciclo de vida

El harness requiere 21 fragmentos exactos privados: asignación/liberación de
memoria, tres operaciones SysMemory, diez operaciones VTLB, preparación y flujo
de carga de estado, ejecución, reset y dos variantes de configuración.
Los manifiestos fijan archivo, hash de fuente y hash de cada fragmento `.inc`.
No se incorporan al repositorio cuerpos PCSX2 ni datos de Silent Hill 3.

Hay 54 escenarios: 15 de mapas, 7 de TLB, 7 de memoria, 13 de ejecución/reset/
configuración y 12 de restauración. Se comparan ON, OFF, ON con ASan/UBSan y
funciones anteriores con OFF, usando el mismo núcleo/puente actual. Los avisos
no forman parte del resumen de efectos; se comprueban por separado antes del
primer efecto y con causas, contador y estados terminales esperados.

Son dobles los tipos/mapas VTLB y operaciones de fastmem/OS, CPU, trabajadores,
subsistemas, configuración, ZIP y cargadores internos. Los fallos parciales
provienen de esos cargadores controlados; no se descomprime un estado real.
`memReset` y `cpuReset` son dependencias simuladas. Sus cuerpos, `vtlb_Init` y
`VMManager::Shutdown` solo se compilan en las unidades reales; este harness
ejecuta 20 de los 24 puntos nuevos. No es una prueba de fastmem del OS ni de VM.

Los tests portables de `test_host_lifecycle` comprueban época, agotamiento,
concurrencia de contador/avisos, conexión y terminales. No ejecutan efectos de
memoria concurrentes. La época puede avanzar varias veces por una llamada con
fronteras anidadas; los conteos del harness corresponden a sus dependencias.

La CI pública ejecuta los tests portables mediante CMake. Este harness necesita
los fragmentos privados y no se ejecuta automáticamente en ella. Se mantienen
`-Wall -Wextra -Werror`; los comandos y resultados se fijan en la evidencia.
