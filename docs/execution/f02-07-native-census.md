# F02.07 — Censo independiente de módulos

Fecha: 2026-10-19. Contrato [IC01–IC07](../../schemas/native-image-census-v1.md).
Evidencia [SRC119](../compatibility/native-census-evidence.json).

## Resultado

**RT-T3b.1 e IC-T1–IC-T3 completos:** el evento 1.025 añade una dirección nueva,
distinta de las 1.024 ya registradas. Su dirección coincide con la traza real
`capacity` de SRC118. El censo permanece completo después del rechazo original:
no aparecen duplicados, retiradas desconocidas ni presupuestos agotados.

| Perfil independiente | Primera lectura | Corte después de parar CPU | Altas / bajas en el corte | Pico |
| --- | ---: | ---: | ---: | ---: |
| Sin VM, primera | 644 | 1.067 | 1.067 / 0 | 1.067 |
| Sin VM, repetición | 644 | 1.067 | 1.067 / 0 | 1.067 |
| VM pausada, primera | 644 | 1.069 | 1.069 / 0 | 1.069 |
| VM pausada, repetición | 643 | 1.069 | 1.069 / 0 | 1.069 |

Las dos VM ya muestran 1.069 en la lectura que precede a `first_read` del
preflight. La variación 643/644 pertenece al corte inicial; las cuentas finales
coinciden por perfil. Son demandas observadas en estos arranques breves, no una
cota para toda la partida ni para eventos posteriores a la destrucción de Qt.
El corte final ocurre después de `EmuThread::stop()` y antes de borrar la ventana.

Se conserva el rechazo de producción: límite 1.024, revisión 1.025,
`first_read` en VM, cero muestras aceptadas y cero inventarios adquiridos.
Los cuatro procesos cierran IO y salen con código cero. Sin VM el servicio
termina con `reason=9`; la VM devuelve `reason=2`, `origins=10`. La ISO europea
inicializa SLES-51434, versión 1.02, CRC 5088CCDB, con BIOS Europa 2.00 y PINE;
el registro de juego sigue en cero segundos.

## Implementación y validación

La máquina pura tiene responsabilidad única: observar un conjunto acotado de
direcciones. Usa 32.832 bytes; cada observación ocupa 64. No hace asignaciones,
llamadas de sistema ni lecturas de memoria del juego. El dueño existente
serializa eventos bajo mutex; otro adaptador copia y emite las observaciones.
No se modifica `ImageLedger`, su ABI, sus fallos ni el protocolo del servicio.

- **186 ejecuciones nativas:** 62 casos en Debug, Release y ASan/UBSan. Son
  16 del censo y 46 regresiones de identidad, preflight y eventos por modo.
- **27 ejecuciones TSan arm64:** 16 del censo y 11 del envoltorio de eventos,
  con concurrencia y fork. Todas pasan. ASan/UBSan y los otros modos son x86_64.
- **80 ejecuciones adicionales del harness final:** los 16 casos del censo
  pasan con GCC local en macOS arm64 y Clang Debug/Release/ASan-UBSan x86_64 y
  TSan arm64. GCC detectó las variantes con tamaño de `delete` faltantes;
  se añaden siguiendo los otros tests de asignación del repositorio. La única
  diferencia son esas dos funciones del test; censo y candidato no cambian.
  La compilación fallida de GCC queda conservada y verificada por separado.
- El CMake nativo incorpora los 16 escenarios, disponibles para el pipeline
  existente. No se ejecutan CI remota, Linux, compilación 3DS ni la batería
  completa de SRC117; su evidencia anterior permanece intacta.
- Copia privada de **3.042 archivos**: dos archivos modificados y dos cabeceras
  propias añadidas sobre SRC118. Se reconstruyen dos unidades y el MOC de QtHost;
  **468 de las 470 entradas de enlace** conservan sus hashes. El paquete contiene
  200 archivos regulares y 42 Mach-O; firma, frameworks, `-testconfig` y
  manifiesto de 43 archivos verificados.
- Se validan custodia, arquitectura y enlaces del repositorio antes de publicar.

El postcheck inicial buscaba una traza en el JUnit, cuyo stdout de casos
aprobados CTest recorta a 1.024 bytes. El nuevo censo desplazó esa traza fuera
del fragmento. Los 186 tests sí habían pasado. Un postcheck separado verifica
JUnit y los logs completos de CTest, donde siguen las seis causas del registro
y `cache_flag_outside`. Se conserva el fallo del auditor y no se repiten ni
alteran los resultados para ocultarlo.

La primera auditoría de publicación trasladaba de SRC118 una expectativa de
orden entre `SH3_RT_END` y la traza del loader sin VM. Las dos repeticiones
presentan órdenes distintos: son hilos independientes y ese orden de salida
no es un criterio de aceptación. La segunda versión lo registra como dato,
conserva el intento fallido y mantiene los mismos controles del censo y cierre.
La tercera corrige además el nombre del recibo histórico de SRC117 a
`qt-link.json` y contrasta su hash con la evidencia publicada; no altera el enlace.
La evidencia final incluye la revisión de portabilidad posterior al informe
preliminar y sus pruebas; ambos estados y sus hashes quedan conservados.

SHA-256 del ejecutable diagnóstico:

`e5a997a6b014f3075a9e1306d543849a96fd9e7181780400de035b37b179d50d`

## Recursos del reenlace

Se aplica únicamente la excepción **IC-L**: 12 GiB iniciales, suelo de 10 GiB,
etapa máxima de 512 MiB y 180 s por compilación/enlace, con supervisor y cierre
del grupo de procesos. El enlace parte de 16,94 GiB libres, dura **22,179 s** y
la etapa llega a **239,30 MiB** durante ese proceso, incluida la copia de fuentes.
Perfiles, logs y temporales posteriores también quedan dentro del mismo límite.
El muestreo de disco no mide RAM ni impone una cuota instantánea.

IB02 conserva 20 GiB para builds completos y dependencias. IC-L está basada en
tres enlaces anteriores medidos y solo cubre esta reconstrucción de dos unidades;
no autoriza por sí sola el siguiente cambio de capacidad.

## Propuesta de capacidad y trabajo pendiente

Se propone evaluar **2.048 entradas**: primera potencia de dos que cubre el
máximo observado de 1.069 y deja 979 libres. Es una elección de ingeniería
para validar, no una demostración de suficiencia para todas las fases del juego.
Los 4.096 del censo son un límite de instrumentación y no se trasladan al producto.

Medición de `sizeof` mediante Clang x86_64, compilada con cabeceras originales y
una copia que cambia solo la constante; los archivos de producción se preservan:

| Estructura o suma de arrays declarados | 1.024 entradas (bytes) | 2.048 entradas (bytes) |
| --- | ---: | ---: |
| `ImageSnapshot` | 8.208 | 16.400 |
| `ImageLedger` | 8.216 | 16.408 |
| `MacOSPlatformOrigins` | 270.552 | 278.744 |
| Arrays de `InventoryGuard::sample` | 98.336 | 196.640 |
| Arrays de `PlatformInventoryGuard::sample` | 204.832 | 409.632 |

`MappedFile` ocupa 72 bytes e `ImageOrigin`, 176. Las sumas incluyen los dos
snapshots, índices y arrays de mappings/orígenes; **no son marcos de pila
medidos ni consumo máximo simultáneo**. Faltan padding del compilador,
temporales, llamadas anidadas y pilas concretas de los threads reales.
El catálogo de caché de 32.768 entradas no cambia.

RT-T3b.2 debe resolver conjuntamente:

1. Presupuesto de pila/almacenamiento para los arrays anteriores, su anidamiento
   y dueños. Verificar que el cierre no comparte estado mutable ni recupera
   automáticamente un registro invalidado.
2. Coste de búsquedas/ordenación y consultas de origen por muestra, con el plazo
   acumulado existente de 5 s y cancelación/cierre. Un `sizeof` no demuestra plazo.
3. Coherencia de `image_capacity`, normalizadores, inventarios y productor
   `platform_diagnostic.cpp`; el consumidor Python `platform_diagnostic.py`
   y [PD](../../schemas/platform-diagnostic-v1.md) aún exigen total ≤1.024.
   Definir transición de contrato antes de aceptar totales mayores.
4. Casos exactos del límite/exceso, altas duplicadas, bajas desconocidas,
   revisiones, cambios entre snapshots y corpus común C++/Python. Conservar
   rechazo ante objetos no cubiertos y verificar sanitizadores.
5. Fijar todos los objetos afectados por el cambio de ABI y su presupuesto de
   reconstrucción; no reutilizar consumidores compilados con el tamaño anterior.

Después, RT-T3b.3 deberá demostrar muestras positivas en un candidato nuevo.
**RT-T3b.2/RT-T3b.3, RT-T3c, RS-T3/RB-T3/DW-T3 y captura siguen abiertos.**
Este informe no valida JIT, caché de código, DMA ni ciclo de vida como escritores
admitidos. ISO, BIOS, perfiles, trazas y candidatos permanecen privados.
