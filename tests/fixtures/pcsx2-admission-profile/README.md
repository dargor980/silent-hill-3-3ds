# Fixtures de admisión del proveedor

`harness.cpp` contiene dobles y oráculos propios. La etapa privada aporta seis
fragmentos exactos: inicialización/cierre del hilo CPU, Execute, sampler, marcas
locales al hilo y clase ScopedGuard. La comparación anterior usa cuatro fragmentos
reales y dos archivos vacíos para las nuevas declaraciones desactivadas en OFF.

Se ejecutan 34 casos en ON, OFF, ASan/UBSan y copia anterior OFF. Incluyen fallo
de reserva, inicialización parcial, otro hilo, cinco estados no pausados, opciones
contradictorias con punteros, nulos, replayer, cambio pendiente, PINE/config,
reentrada en Execute, excepción y ejecución anidada. Los efectos de subsistemas
se comparan mediante secuencia controlada y resumen idéntico en cuatro modos.
Las aserciones del sampler se ejecutan solo en ON y sanitizadores.

Configuración, objetos CPU, memoria, PINE, Achievements y subsistemas son dobles.
Las ramas de inicialización específicas de Windows/x86 no se ejecutan aquí; la
unidad real x86_64 se compila separadamente. `newVifDynaRec=true` coincide con
la constante del proveedor fijado. No hay ZIP, sockets, RAM del juego ni VM.

La suite pública portátil del evaluador enumera 262.144 subconjuntos de
incumplimientos; eso no enumera todas las combinaciones de una VM. Los campos de
exclusión siguen desconocidos en el sampler real. El harness no demuestra
quiescencia, cierre PINE, unión con época, ausencia de deadlocks ni captura real.

[Contrato AP01–AP08](../../../schemas/admission-profile-v1.md).
