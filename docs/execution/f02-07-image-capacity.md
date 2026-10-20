# F02.07 — Capacidad y almacenamiento del inventario

Fecha: 2026-10-19. [LC01–LC08](../../schemas/image-capacity-v2.md) y
[PD v2](../../schemas/platform-diagnostic-v2.md). Evidencia:
[SRC120](../compatibility/image-capacity-evidence.json).

## Resultado y alcance

**RT-T3b.2 y LC-T1–LC-T3 completos en las fuentes y pruebas del repositorio.**
El límite del registro pasa a **2.048 imágenes**, con 979 entradas respecto
del pico de 1.069 observado en SRC119. Se conserva el rechazo terminal ante
exceso, duplicados, bajas desconocidas, revisiones inválidas o imágenes no
cubiertas. No se recupera un registro fallido ni se omiten eventos.

Se cambia coordinadamente almacenamiento y protocolo. El candidato PCSX2 de
SRC119 conserva sus bytes y el límite anterior: **no se reenlaza ni ejecuta una
VM en esta etapa**. RT-T3b.3 debe demostrar el arranque, los plazos nativos y las
muestras positivas con el nuevo ABI. Captura y admisión permanecen pendientes.

## Memoria y responsabilidad de cada componente

`InventoryGuard` y `PlatformInventoryGuard` poseen un espacio fijo `Scratch`
privado mediante `unique_ptr`. Solo sus constructores válidos reservan con
`nothrow`; si falla, devuelven `storage` sin consultar puertos ni reintentar.
El destructor libera el espacio. `sample()` reutiliza la reserva y conserva
dobles pasadas, canonización, hashes, comprobación de cambios y línea base.
Las instancias no comparten almacenamiento mutable.

El trabajo nativo ya crea su composición en heap dentro del trabajador DW y
la destruye antes de confirmar cierre. No se reserva desde los callbacks del
loader ni se amplía la pila por configuración del thread.

| Medición x86_64 | Estricto | Plataforma |
| --- | ---: | ---: |
| Objeto guardia | 208 bytes | 424 bytes |
| Espacio de trabajo propio | 196.640 bytes | 409.632 bytes |
| Marco de `sample()` en Clang Release | 41.288 bytes | 41.656 bytes |

Las aserciones limitan cada guardia a 512 bytes y los espacios a 256/512 KiB.
Los marcos compilados adicionales medidos son: `ManifestGuard::sample`, 41.128
bytes; `AnchoredDigest::sample`, 65.816; preflight nativo, 32.904; estabilidad
de orígenes, 16.440. **No son una medida del máximo de toda la pila ni de RSS**:
faltan biblioteca estándar, SO y anidamientos que solo el candidato real puede
ejercitar. El catálogo de caché sigue con 32.768 entradas y se aloja en el dueño
nativo ya existente; no se cambia su política.

Un hilo creado con pila solicitada y comprobada de **512 KiB** ejecuta dos
muestras estrictas y dos de plataforma a 2.048 imágenes, sin nuevas reservas
durante el muestreo. La secuencia tarda 1.173 microsegundos en Release local,
4.189 en Debug, 9.637 con ASan/UBSan y 38.861 con TSan. Son dobles de puertos y
hash, sin IO nativo, y no representan rendimiento de PCSX2 ni del juego.

Se conservan el plazo acumulado de cinco segundos iniciales y dos de
revalidación, los checkpoints y el descarte de resultados tardíos. Pasan las
pruebas existentes de coste acumulado, reloj real, cancelación y entrega; esto
comprueba su semántica, no garantiza que el inventario real llegue a tiempo.

## Contrato y pruebas

PD v2 conserva tamaños (32/294 bytes), offsets, perfil PT v2 y campos de
identidad, pero exige `SH3PDQ02`/`SH3PDR02` y total ≤2.048. Productor C++,
consumidor Python y canal se actualizan juntos. Se rechaza v1 sin negociación.
Los vectores v1 y su evidencia permanecen intactos. Los nuevos vectores comunes
comprueban totales 1.025, 1.069, 2.048 y las comprobaciones de exceso/overflow.
No cambia el significado de las evidencias ni se conceden capacidades.

- **2.224 ejecuciones nativas:** 556 en Debug, Release, ASan/UBSan y cobertura.
  Incluyen ledger, inventarios, orígenes, codecs, trabajadores, sesiones y servicio.
- **48 TSan arm64:** almacenamiento, trabajador, reloj real y entrega.
- **6 con GCC local:** reserva, fallo de reserva, aislamiento y pila limitada.
- **304 pruebas Python:** codec v2, correlación, versiones, sesiones, transporte
  y presupuesto acumulado. Los seis escenarios nuevos de almacenamiento y
  vectores v2 quedan integrados en el pipeline existente.
- Cobertura de líneas: inventario estricto 100%, plataforma 99,37% y codec
  100%; cobertura de ramas 92,26%, 94,59% y 98,15%, respectivamente. No se
  atribuye cobertura total de ramas a estos porcentajes de líneas.
- Se comprueban arquitectura, custodia, enlaces y supervisor al publicar.
  No se ejecutan CI remota, Linux ni compilación para 3DS.

Se conservan los intentos fallidos: un control Python seguía alterando el magic
a `2`, ahora válido, y dos controles de layout fijaban 1.024. Se actualizan al
contrato nuevo y se repiten las suites correspondientes. El primer selector
TSan omitía compilar el ejecutable de reloj real aunque CTest lo seleccionaba;
se añade el target y los 48 casos pasan. Ninguno de estos fallos se presenta
como una ejecución aprobada.

## Reenlace pendiente

Se inspeccionaron los archivos de dependencias del compilador para todos los
objetos del enlace anterior, sin dependencias faltantes: **128 objetos** incluyen
las cabeceras afectadas; el resto suma 342 entradas de enlace. Los 128 objetos
anteriores suman 18.165.200 bytes. Esta es una matriz conservadora de impacto,
no una autorización para reutilizar automáticamente las otras entradas:
el siguiente build debe verificar sus fuentes, archivos estáticos y hashes,
regenerar MOC cuando corresponda y confirmar su nueva base de compilación.

RT-T3b.3 debe crear una copia nueva, incorporar estos cambios y retirar o adaptar
los hooks diagnósticos del censo histórico que fijan su borde en 1.024. Debe
presupuestar las 128 unidades, reenlazar, firmar, fijar manifiesto y consumidor
PD v2, y repetir arranques y cierre. La excepción IC-L de dos unidades no aplica.
El compilador de pruebas mide marcos sin ThinLTO; el reenlace real debe validar
la combinación final y no mezclar objetos con distintos tamaños de snapshot.

**RT-T3b.3, RT-T3c, RS-T3/RB-T3/DW-T3 y captura continúan abiertos.** Los candidatos,
ISO, BIOS y datos de ejecución previos permanecen privados e inalterados.
