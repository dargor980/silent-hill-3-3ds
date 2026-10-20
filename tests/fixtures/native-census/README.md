# Censo independiente de eventos del loader

`image_census.hpp` conserva un conjunto fijo y contadores propios. El registro
de producción sigue rechazando con su límite de 1.024; la sonda no aporta
inventario ni cambia admisión. Contrato: [IC01–IC07](../../../schemas/native-image-census-v1.md).

`instrument.py` genera sustituciones exactas y reversibles en dos archivos de
una copia privada. Alimenta el censo bajo el mutex existente y copia los datos
antes de emitirlos fuera del bloqueo. `census_report.hpp` declara únicamente el
corte final solicitado desde Qt después de parar CPU. No se incluyen estos
hooks en el producto público. La sonda puede afectar los tiempos observados.

Los 16 casos `image_census_*` están integrados en el CMake nativo y comprueban
borde nuevo/duplicado/nulo, retirada, capacidad, presupuesto, fallo persistente,
direcciones y tamaño, sin asignaciones dinámicas. SRC119 ejecuta 186 casos
nativos en tres modos y 27 con TSan, incluidas las regresiones del envoltorio.
Tras completar las variantes de `delete` exigidas por GCC se repiten 80
ejecuciones del harness final en GCC/Clang y sanitizadores locales. El estado
del censo y la instrumentación privada mantienen sus bytes originales.

`footprint.cpp` mide el ABI x86_64 con cabeceras originales y con una copia
aislada que solo cambia la constante a 2.048. Suma los arrays locales declarados;
no mide marcos de pila reales, RSS, concurrencia ni plazos. Es una medición para
la propuesta de presupuesto, no una aceptación del nuevo límite.

El [informe](../../../docs/execution/f02-07-native-census.md) documenta cuatro
ejecuciones reales, los cortes observados, el reenlace acotado IC-L y las
condiciones pendientes de RT-T3b.2/RT-T3b.3.
