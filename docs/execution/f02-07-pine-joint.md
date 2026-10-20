# F02.07 — Servidor PINE y coordinador conjuntos (SRC87)

Fecha: 2026-10-18. Contrato [PJ01–PJ10](../../schemas/pine-joint-v1.md).
IW-PINE-JOINT1 y 2 están verificadas en el alcance descrito. IW-PINE-JOINT3
completa las pruebas de lifecycle, objetos y custodia; su nuevo enlace completo
queda pendiente de la reserva IB02 de 20 GiB al iniciar. La configuración está
preparada, pero la compilación completa no se ha iniciado.

## Fallos reproducidos y reparación

La fuente SRC85/SRC86 conservada se ejecutó con su servidor completo, sockets
Unix y thread nativos. La primera compilación de la fixture falló porque faltaba
un tipo de consola sintético; se conserva ese intento y su corrección.

| Evidencia base | Resultado | Reparación privada |
|---|---|---|
| Comando de memoria bajo UBSan | Lectura desalineada de un entero de 32 bits | FromSpan copia bytes a una variable alineada mediante memcpy |
| Cierre bajo TSan | Carrera sobre s_msgsock en Deinitialize/MainLoop, siete escenarios | El worker posee el cierre; mutex para publicar/retirar y solicitar shutdown |
| Dos mensajes en una escritura | Falta la segunda respuesta; vence la lectura del cliente | Leer solo encabezado/cuerpo del mensaje actual, conservando el siguiente |

La primera copia reparada eliminó esos defectos, pero cuatro ejecuciones
agotaron el límite al cerrar. Una reproducción adicional y `/usr/bin/sample`
confirmaron Deinitialize esperando join y el worker dentro de AcceptClient.
La fuente y los fallos se preservan, sin declararlos aprobados.

La segunda copia usa listener no bloqueante y poll de hasta 100 ms antes de
accept; configura el cliente bloqueante y revalida parada al publicarlo bajo
mutex. Deinitialize interrumpe sockets, espera el worker y solo entonces cierra
el listener. No cierra descriptores que otro hilo todavía utiliza. El mutex no
abarca lecturas, accept ni callbacks. Initialize/Deinitialize conservan un único
propietario serial; llamadas concurrentes de lifecycle no están acreditadas.

Solo cambia PINE.cpp respecto de SRC85. Ambas copias nuevas preservan las veinte
anteriores; la fuente final tiene 2.966 archivos. Los parches y cuerpos del
proveedor permanecen exclusivamente en la raíz privada autorizada.

## Validación del servidor y del coordinador

La [fixture](../../tests/fixtures/pcsx2-pine-joint/README.md) del servidor cubre
14 escenarios en normal, ASan/UBSan y TSan: **42 ejecuciones finales correctas**.
Incluye comandos, mensajes fragmentados/consecutivos, rechazo con gate cerrado,
Work en cola, timeout, descarte, clientes conectados, parada inactiva y ciclos de
reinicio/desconexión. Se preservan los fallos de la fuente base y primera copia.

La fixture conjunta usa **73 fragmentos exactos**: servidor/dispatch más los 71
de VU/GS, dueño, Mach y Qt ya fijados. CPU es el hilo principal QCoreApplication;
el thread PINE encola mediante Host::RunOnCPUThread y el slot Qt reales. Los
workers ejecutan sus bucles nativos; los efectos de VM, memoria, render y estados
son dobles propios. Siete escenarios × tres modalidades dan **21 ejecuciones
correctas**, con QtCore instrumentado para TSan y carga de biblioteca verificada.

| Situación | Hecho observado |
|---|---|
| Load anterior al cierre | Work mantiene PINE draining; no se solicitan tokens VU/GS hasta ejecutar/destruir el callback |
| Entrada nueva | Se rechaza antes del efecto mientras está cerrada; vuelve a aceptar después del retiro |
| Completion vencida | El callback sigue reteniendo Work; al despacharlo no ejecuta Reader tarde |
| Descarte Qt | removePostedEvents destruye el callback, libera Work y no ejecuta load |
| Parada/reinicio | Cambia generación, invalida el intento anterior y permite uno nuevo |
| Parada con callback pendiente | Detener el servidor no equivale a vaciar la cola CPU; Work sigue vivo hasta el descarte |
| Deadline del coordinador | Retira el intento; el callback puede terminar después, sin retenciones activas |

Tres controles negativos eliminan la reserva de load, eliminan la reserva
retenida por Completion o congelan la generación. Los tres fallan en la aserción
esperada, sin aceptar el timeout del supervisor como detección. Se conserva el
primer fallo del recolector por buscar una cadena de aserción con mayúsculas.

PINE.cpp compila con observador ON/OFF usando argumentos del proveedor. El nuevo
CMake completo configura 825 entradas, catorce propias, preservando excepciones
solo en cooperative_gate.cpp. No cambian núcleo ni CMake públicos: no se repiten
los 160 CTest por preset ya fijados en SRC85 ni se atribuyen a este cambio.
No se utilizan supresiones de sanitizadores.

## Límite y siguiente paso

La última comprobación de capacidad para esta unidad registró 19,11 GiB libres,
por debajo de los 20 GiB iniciales de IB02. La política es una reserva de trabajo
del proyecto; se solicitó liberar unos 2 GiB. No se eliminó evidencia histórica.

La continuación concreta es:

1. Revalidar espacio y manifiesto; ejecutar el build configurado con dos jobs,
   suelo de 10 GiB y límite de etapa de 8 GiB.
2. Ejecutar los tests originales, preparar/verificar el candidato privado y
   probar testconfig con perfil aislado. Preservar el bundle original e instalación.
3. Publicar evidencia adicional del enlace; después abordar locks/backend y
   RDebug antes de modificar admisión o realizar capturas nuevas del juego.

El resultado actual acredita transporte y coordinación en macOS x86_64. No
acredita las ramas Windows/Linux, el frontend QWidget completo, callbacks
arbitrarios libres de deadlock, VM, permisos RDebug ni ejecución Nintendo.
El lector sintético rechaza captura; no se ejecuta una lectura RAM aceptada del
juego. La admisión global y las capacidades continúan vacías, y F02.07 sigue abierta.
