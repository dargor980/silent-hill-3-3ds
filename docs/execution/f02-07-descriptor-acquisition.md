# F02.07 — Generación de descriptores y adquisición multirrango

Unidad: `origin/load-provenance/LP-C`. Fecha: 2026-10-18.
Estado: **consistencia del descriptor y coordinador implementados y probados
con fixtures; apertura real y vínculo con el archivo pendientes**.
Contrato [DA01–DA09](../../schemas/descriptor-acquisition-v1.md).
[Evidencia SRC57](../compatibility/descriptor-acquisition-evidence.json).

## Investigación estática

Nueve ventanas del ELF coinciden íntegramente con el estado fijado en SRC55:
**1.692 bytes** de asignación, codificación, comprobación, liberación, apertura,
comparación y resolución de catálogo. Se fijan dieciséis instrucciones para
contrastar las transiciones y las salidas de rango. La ruta de apertura
incrementa la generación al completarse; el identificador combina esa
generación con el índice de tabla. La liberación marca la fila como cerrada
sin borrar necesariamente su generación, offset y tamaño.

El resolver candidato compara referencias de catálogo y devuelve offset y
tamaño mediante dos parámetros de salida. Se ha localizado esa ruta estática,
pero aún falta observar qué registro y ruta selecciona para la carga candidata.
Una coincidencia de rango no identifica el contenedor.

La multiplicación R5900 escribe también el resultado bajo en el registro
destino. Se contrastó ese detalle en el archivo local
[R5900OpcodeImpl.cpp de la revisión fijada](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/R5900OpcodeImpl.cpp),
idéntico entre baseline y árbol instrumentado: 41.762 bytes, SHA-256
`6ae749a7e3a297a291f1844d2f96a17bf7c53a9c6f6f4ab4ddab27781a78c2b4`.
No se incorpora su implementación al proyecto.

La tabla del estado posterior a la carga contiene **16 filas cerradas**. Una
conserva generación y rango anteriores; ninguna coincide con el rango del
candidato. Esto impide usar la tabla residual como prueba de apertura activa.
Los planes, direcciones, palabras de código y estados permanecen privados.

Dos análisis verifican la ISO completa, ELF, estado, planes previos y fuentes
locales, y producen el mismo informe de **3.109 bytes**, SHA-256
`9d18b46ba5a6873a56650d1b66e22fbdc81d4c1190cad15896004cd4a2e2d78a`.
Se cierran lectores antes de publicar; se revalidan entradas y no se
sobrescriben planes. Son repeticiones estáticas, sin nueva sesión de PCSX2.

## Implementación

[archive_descriptor](../../tools/inspectors/archive_descriptor.py) interpreta
dos rangos con mapa comprobado: configuración de tabla y fila. Exige capacidad
de 2 a 256, índice válido, dirección derivada, descriptor subyacente abierto,
generación positiva y rango exacto. La capacidad determina la menor potencia
de dos que la cubre. El contrato conservador rechaza tokens fuera del rango
positivo soportado, desbordamientos y vuelta completa de generación.

Al conciliar dos pausas exige identidad, tabla, fila y mapas conservados,
secuencias consecutivas, slots distintos y ciclos crecientes dentro de LP.
Detecta un identificador reciclado aunque mantenga el índice. Comprueba
consistencia de datos suministrados: todavía no verifica el código de la
apertura, su ejecución ni la identidad del archivo.

[observer_multirange](../../tools/inspectors/observer_multirange.py) valida de
uno a ocho planes antes de construir los adaptadores locales o realizar I/O.
Obtiene **un solo estado guardado**, tres observaciones por rango y contraste
PINE/estado/mapa, manteniendo proceso, sesión, entorno, PC, ciclo y slot
comunes. Solo reintenta la respuesta de guardado pendiente, hasta 256 sondeos
y 30 segundos cooperativos. No repite la solicitud de guardado.

Un fallo en cualquier rango, guardia, plazo o cierre impide publicar aceptación.
Conserva escrituras parciales y publica después de cerrar socket y lectores;
una publicación fallida no se reintenta automáticamente. El presupuesto se
comprueba entre operaciones; el supervisor externo sigue siendo necesario
para limitar una sesión completa o un puerto bloqueado.

La interpretación del descriptor permanece pura. El coordinador depende de
puertos separados para canal, custodia, identidad y publicación, con reloj
inyectable. Reutiliza AC/MP/LF sin cambiar el productor ni el build de PCSX2.
Los recibos contienen metadatos, cero eventos `Read`, capacidades/vínculos
vacíos y autenticación no provista. La composición local se prueba con
custodia real sobre datos sintéticos y productor simulado.

## Pruebas y pipeline

**103 casos nuevos:** 44 de descriptores y 59 de adquisición. Cubren capacidades
potencia de dos e intermedias, cierre/reserva, generación reciclada y desbordada,
direcciones y rangos incorrectos, identidad y límites temporales; uno/ocho rangos,
4.096 bytes, fallos en cada intercambio, cambios entre observaciones, planes
inválidos antes de resolver rutas, escritura parcial, cierre y publicación.

La primera regresión registró 2.534 aprobadas y un fallo en un test anterior:
buscaba los dígitos del PID sintético dentro de `repr()`, donde coincidieron
por azar con la dirección hexadecimal de un objeto. Se corrigió el oráculo
para comprobar que se conserva `object.__repr__`, sin representación de los
campos. No cambió el módulo histórico. El hash anterior del test queda en
SRC52 y el nuevo se registra en SRC57; no se reescribe la evidencia histórica.

La segunda regresión pasó 2.535 casos. Tras añadir el rechazo anticipado en
la composición local y su caso negativo, la regresión final pasa **2.536
pruebas, sin fallos ni omisiones**, en 36,451 segundos según JUnit. Se conservan
los tres resultados; no se publicaron informes durante las regresiones.

| Cobertura final | Líneas | Ramas |
|---|---:|---:|
| archive_descriptor | 38/38 (100 %) | 2/2 (100 %) |
| observer_multirange | 95/95 (100 %) | 14/14 (100 %) |
| Todas las herramientas | 4.698/4.743 (99,05 %) | 1.341/1.374 (97,60 %) |

Gate independiente 80/80 y Ruff/formato aprobados en los 122 archivos del
alcance Python de CI. El job existente descubre los módulos y pruebas sin
originales del juego. Los controles de repositorio, custodia, enlaces y diff
se registran en SRC57. No se ejecutó CI remota, una nueva compilación C++/3DS
ni una captura multirrango real.

## Siguiente tarea: apertura y vínculo de catálogo

1. **Fijar la selección:** seguir el resolver y el resultado de apertura desde
   un punto anterior a la carga. Entradas: origen ISO/MFA de SRC55 y ventanas
   de SRC56/SRC57. Entregable: contrato de observación para solicitud, registro
   seleccionado, ruta resuelta, rango y resultado. Aceptación: enlazar la
   selección al ID/rango/hash del catálogo; un nombre o rango aislado no basta.
2. **Componer el vínculo:** verificar código/mapas de apertura y resolución,
   descriptor subyacente, token y generación, y continuidad hasta la llamada
   de transferencia. Mantener el adaptador separado de la adquisición. Añadir
   fixtures de selección ajena, apertura fallida, fila residual, reciclado,
   mapa cambiado y mismo rango en otro contenedor; no crear `Read` sin vínculo.
3. **Posición y ruta efectiva:** observar posición antes/después, solicitud y
   retorno, destinatario indirecto y estado de caché. Para caché, probar el
   origen del sector y el contrato ABI de copia; para lectura, fijar su
   finalización. Aceptación: cadena completa soportada o rechazo explícito
   con la frontera pendiente, sin inferir acceso al disco del payload.
4. **Captura LP-D:** completar primero el plan de puntos/rangos y comprobar
   los presupuestos de LP: 48 estados, 256 solicitudes regionales/hits,
   60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB libres. Usar
   perfil español/Normal/Normal desde antes de la carga, sin restauraciones
   intermedias; reimportar dos veces y verificar cierre y custodia.

LP-C sigue parcial. Procedencia real, semántica de cámara, F02.07/Q05/G02,
dos salas conectadas y validación física en New Nintendo 2DS XL siguen pendientes.
