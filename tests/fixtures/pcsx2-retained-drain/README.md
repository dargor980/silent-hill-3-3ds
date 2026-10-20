# Pruebas del propietario persistente

El harness conserva los 45 escenarios comunes y cinco de frontera de SRC74.
Actualiza tres resultados del bucle a rejected: vaciar PINE ya no equivale a
completar la exclusión. El puerto de producción carece de barrera GS/VU y la
rechaza explícitamente. Los once escenarios de coordinación siguen presentes.

Diez escenarios adicionales ejecutan entradas reales de Execute/DoLoadState
con request queued, PINE draining o fase posterior rechazada aún sin retirar;
comprueban el resultado y la puerta antes del primer efecto original. También
ejecutan el slot Qt y su fast path inline durante drenaje PINE y después de
iniciada la fase posterior. El primer caso permite terminar trabajo anterior;
el segundo retira antes del callback. Total: 26 extras ON/sanitizadores.

Los trece fragmentos exactos se conservan en la etapa privada. La comparación
anterior OFF usa nueve y cuatro includes vacíos. Se ejecutan cuerpos reales con
dobles de VM/Qt, no una VM completa. Solo Execute y DoLoadState se ejecutan entre
las catorce entradas instrumentadas; las demás se compilan y auditan en entrada.
El puerto real rechazado no demuestra retención de trabajadores; la fase
pending/held y su orden de liberación se prueban con un puerto propio en CTest.

Los diez escenarios portables de `test_retained_drain.cpp` forman parte de CI.
El harness privado no requiere originales del juego, pero sí fuentes del
proveedor y no entra en CI pública. No se repite el probe QtCore de SRC74.
