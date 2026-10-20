# F02.07 / LP-C — Productores DMA, segundo lote LG-I1

Fecha: 2026-10-18. Fuente: SRC67. Contrato:
[DW01–DW07](../../schemas/dma-write-probe-v1.md). Evidencia:
[metadatos públicos](../compatibility/dma-write-probe-evidence.json).

## Resultado

Se incorporan diez puntos de aviso para copias directas y un rechazo conservador
antes de solicitar el retorno GS desde VIF1. El parche modifica seis archivos de
una copia privada nueva del PCSX2 fijado en
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Reutiliza el puente y la guardia de
SRC65/SRC66 sin modificar sus fuentes, contratos ni evidencia histórica.

**El lote acredita funciones, no continuidad real en una VM.** LG-I1 permanece
parcial; LG-I2–I4 siguen abiertos. No se añade armado, no se enlaza ni ejecuta la
aplicación completa y no se cambia el ejecutable PCSX2 instalado. No hay nuevos
eventos `Read`, semántica del recurso ni validación en consola.

## Inventario de destinos y ejecución

| Ruta y función | Destino y longitud observados | Contexto y sincronización |
|---|---|---|
| SPR: `memcpy_from_spr`, llamado desde cadena e interleave SPR0 | Puntero host `dst`; cada fragmento real de `end`, `size-end` o `size` bytes | Llamador del controlador SPR; copia síncrona. Las esperas VU del resolutor siguen intactas |
| MFIFO: `hwMFIFOWrite` → `MemCopy_WrappedDest` | Base obtenida por `PSM`; destino y bytes de cada `memcpy`, después de resolver el wrap | Llamador SPR; callback opcional antes de cada efecto, sin dependencia de `common` hacia el observador |
| SIF: `sifFifo::read`, usado por SIF0/SIF2 hacia EE y SIF1 hacia IOP | `to` y `to+wP0`; longitudes `wP0*4`, `wP1*4` | Llamador de transferencia EE/IOP emulada; copia síncrona. Temporales e IOP se filtran por destino host |
| IPU: `IPU_Fifo_Output::read` | `value` antes/después de avanzar el puntero; `first_words*4`, `second_words*4` | Llamador DMA IPU0 o lectura FIFO; copia síncrona. Contadores OFC/readpos originales |
| VIF1 → `MTGS::InitAndReadFIFO` | Solicitud de `min(GSLastDownloadSize,qwc)` quadwords; no se acredita el efecto | Invalida con `lost` antes de delegar si el tamaño es positivo. El consumidor puede usar hilo GS, descarga sin sincronizar o relleno |

El contexto indicado procede del grafo estático del proveedor. **No se acredita
afinidad de hilo ni exclusión global en ejecución.** El mutex protege callbacks,
no el intervalo entre aviso y escritura. El envío al hilo GS y su `WaitGS`
original no constituyen aquí una prueba de finalización. Otras entradas MTGS
(lectura FIFO y replay) y sus efectos necesitan revisión antes de admitir modos.

Los resolutores DMA pueden devolver RAM EE, scratchpad, VU o buffers de descarte;
por eso se observa el puntero host final, no una máscara del registro de dirección.
Los fragmentos vacíos no generan avisos. Un rechazo de la guardia nunca cancela
la copia original. Los accesos con parámetros inválidos siguen siendo responsabilidad
del proveedor; el parche no pretende reparar su emulación.

MFIFO tiene una particularidad: el helper fijado realiza como máximo dos copias,
también cuando la longitud supera el tamaño del anillo. La instrumentación sigue
esas copias exactamente. No reemplaza ese comportamiento por un bucle circular
que pudiera escribir bytes diferentes.

## Diseño y SOLID

Los productores solo comunican destino, cantidad y ciclo a `PhysicalWrites`.
`LifetimeGuard` conserva la responsabilidad de invalidación; no conoce DMA,
archivos, transporte ni sockets. El helper común recibe un callback opcional
exclusivamente bajo `SH3_ENABLE_OBSERVER`; `hwMFIFOWrite` lo inyecta. Los otros
consumidores del helper no incorporan referencias al puente. Sin observador se
compilan las llamadas originales; sin conexión los hooks son inertes.

El arnés propio público está en
[harness.cpp](../../tests/fixtures/pcsx2-dma-probe/harness.cpp). Incluye ocho cuerpos
del proveedor copiados literalmente a archivos privados, con hashes. Los dobles
de resolución, registros, logs, interrupciones y planificación GS son explícitos.
No simulan una VM completa ni se presentan como prueba del hilo GS real.

## Compilación y batería de pruebas

- **26 unidades reales**: 13 ON y 13 OFF, con las opciones generadas de PCSX2,
  Apple Clang 21, x86_64, C++20, ThinLTO y SDK explícito. Incluyen los productores
  y consumidores directos de los headers modificados; no equivalen a reconstruir
  todos los consumidores transitivos ni a enlazar PCSX2.
- **54 casos por modalidad**, aprobados en ON, OFF y ASan/UBSan con `-Werror`.
  Comprueban el aviso y, para destinos protegidos, la invalidación antes del efecto;
  además de bytes, límites, retornos y registros posteriores.
- Casos: tamaños y wrap SPR; MFIFO normal, fin exacto, cero, anillo excedido,
  dirección rechazada y consumidor sin callback; SIF0/SIF2 con FIFO fragmentado,
  capacidad parcial y rechazo del siguiente bloque; salida IPU con wrap y OFC;
  retorno GS normal, diferido, vacío, dirección fallida y tamaño parcial.
- Todos los productores con efecto sobre RAM se prueban con el mismo valor o con
  una modificación seguida de restauración. Destinos ajenos no consumen eventos.
  La copia continúa después del fallo. Un escenario SPR desconecta el puente.
- Los tres modos producen el mismo resumen de efectos (`340a8a44d900a0cc`, FNV-1a
  de 64 bits), acompañado por oráculos explícitos de bytes y registros. Los logs
  y binarios se identifican adicionalmente mediante SHA-256.

La primera variante compiló con las opciones del proveedor, pero el harness la
rechazó por `-Wint-in-bool-context` bajo `-Werror`. Se conservaron fuente, recibos,
log y fixture inicial; una copia nueva usa comparaciones explícitas contra cero.
Se repitieron las 26 compilaciones y las tres modalidades sin relajar flags.

La primera regresión Python se ejecutó dentro del sandbox: 3.090 aprobadas y seis
fallos del supervisor al no poder ejecutar `/bin/ps`. Se conservaron JUnit y
cobertura de ese intento. La repetición completa usa permiso para inspeccionar
los grupos de procesos sintéticos; no se cambian tests ni criterios de aceptación.

La etapa privada usa supervisión con 180 s por compilación, 30 s por ensayo,
suelo de 10 GiB y límite de etapa de 1 GiB. Los procesos finales cerraron sus
grupos. Se reverifican 2.934 archivos baseline, 2.941 del observador anterior,
2.945 de SRC66 y 2.945 de cada copia DMA. Los scripts operativos, objetos y cuerpos
GPL permanecen privados; se publican hashes y el fixture propio.

## Pipeline y trazabilidad

DW-T1–T3 quedan completadas para este inventario acotado. DW-T4 se cierra con la
regresión y los controles registrados en la evidencia. El pipeline local privado
ejecuta: preparar copia → compilar unidades ON/OFF → extraer cuerpos exactos →
compilar/ejecutar harness ON/OFF/sanitizadores → auditar fuentes, objetos y efectos
dos veces → regresión host/Python y controles del repositorio.

Los recibos de auditoría coinciden: 18.428 bytes, SHA-256
`40a058bd83aca0eda32b0ad4f6768689e14f9cf2ff9d9eb84695122a8bf6eeaf`.
Las tres configuraciones host aprobaron **67/67 pruebas** cada una. Ruff/formato
(137 archivos), controles de repositorio y diff pasan. La repetición Python
aprobó **3.096/3.096 pruebas**, sin omisiones, con cobertura total del 98,86 % y
gate de líneas/ramas 80/80 aprobado. Los metadatos conservan ambos intentos.

La CI pública existente sigue ejecutando los tests del núcleo/puente y los gates
host/Python/3DS. **El harness DMA requiere los cuerpos privados y no se ejecuta
automáticamente en esa CI.** No se ejecutó CI remota, cobertura GCC, build 3DS ni
una compilación completa del proveedor en esta unidad. La evidencia separa esos
límites de los resultados locales y conserva el rechazo preparatorio.

## Siguiente tarea: LG-I1 / JIT y caché

1. Inventariar stores constantes/dinámicos, fastmem, fallbacks y caminos de caché:
   destino, tamaño, modo habilitado y relación con bloques ya compilados.
   Entregable: matriz con hashes y decisión explícita de qué modos pueden cubrirse.
2. Integrar avisos antes del efecto o rechazo conservador donde no pueda probarse
   cobertura; invalidar/recompilar bloques cuando corresponda. Evitar duplicar
   avisos en fallbacks que ya atraviesan VTLB. No habilitar armado todavía.
3. Probar stores, aliases, cambios transitorios y escrituras iguales; caché con
   hits/misses, expulsión y transferencia a RAM. Comparar efectos ON/OFF y, donde
   corresponda, intérprete/JIT; registrar el coste sin inventar resultados de VM.
4. Compilar unidades reales y repetir gates. Mantener abiertos escritores host,
   cierre efectivo GS, época/reset/restore, concurrencia global, extremos,
   transporte y pruebas en la aplicación completa.

LP-D, procedencia real, F02.07/Q05/G02, semántica de cámara, dos salas conectadas y
New Nintendo 2DS XL siguen pendientes. La captura posterior conserva el perfil
español/Normal/Normal y sus límites, sin restauraciones entre puntos.
