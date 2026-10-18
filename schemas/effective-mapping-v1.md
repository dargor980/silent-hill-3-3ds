# Contrato MP v1 — respaldo efectivo de RAM EE

F02.07/origin/effective-mapping. Observación host de PCSX2 v2.8.2 x86_64;
no es un formato del juego ni una interfaz del runtime 3DS. La implementación
inicial valida muestras sintéticas y comprueba la factibilidad de acceso host.
[SRC53](../docs/execution/f02-07-observer-live.md) aporta posteriormente las
cuatro capturas reales y su publicación para una invocación, mediante la
extensión interna OB y los contratos AC/OS. No demuestra procedencia de carga.

## Requisitos EARS

- **MP01 — Identidad.** CUANDO se examine un mapa, el validador DEBERÁ exigir
  sesión, entorno, identidad de proceso, secuencia y hash de estado iguales al
  contexto esperado, tanto antes como después de la lectura. Los hashes son
  SHA-256 minúsculos; sesión es UUID sin guiones; secuencia está entre 1 y 256.
  El adaptador real DEBERÁ fijar binario/ABI/símbolos e identidad del proceso
  antes de desreferenciar punteros. Una declaración no autentica la ejecución.
- **MP02 — Solo lectura.** MIENTRAS observe el proceso, el adaptador DEBERÁ usar
  únicamente un puerto de lectura y lecturas acotadas. SI macOS deniega ese
  puerto, el investigador DEBERÁ registrar el código y conservar el mapa como
  pendiente; no cambiará firma, entitlements ni protecciones del sistema.
  Para el build privado optativo, [OB01–OB10](pcsx2-observer-v1.md) sustituye
  el puerto externo por lectura interna acotada en el hilo CPU. Esta extensión
  no reintenta el puerto denegado ni modifica la aplicación oficial.
- **MP03 — Pausa y estabilidad.** CUANDO se valide una lectura, ambas muestras
  DEBERÁN declarar pausa y coincidir en identidad, base EE, tamaño expuesto,
  puntero vmap y todas las entradas utilizadas. SI difieren, el validador DEBERÁ
  rechazarla. Dos extremos iguales no demuestran ausencia de cambios intermedios.
- **MP04 — Rango y cobertura.** CUANDO se solicite un rango virtual de 1 a 4096
  bytes, el validador DEBERÁ cubrir exactamente sus páginas de 4096 bytes,
  ordenadas, sin duplicados ni páginas adicionales. DEBERÁ rechazar overflow
  de 32 bits, tipos booleanos usados como enteros y valores fuera de límites.
- **MP05 — Traducción.** CUANDO decodifique una entrada vmap de 64 bits, el
  validador DEBERÁ sumar la dirección virtual módulo 2^64 antes de comprobar
  el bit de signo. SI el resultado designa un handler, DEBERÁ rechazarlo.
  Un desplazamiento con bit alto por sí solo no indica handler.
- **MP06 — Respaldo.** CUANDO una página sea directa, el validador DEBERÁ
  verificar que el segmento completo pertenece a los 32 MiB expuestos de RAM
  EE y que todos los segmentos forman un respaldo contiguo. DEBERÁ distinguir
  un alias válido de la coincidencia con el offset físico esperado; no aplicará
  máscaras para normalizar alias ni identificará ppmap/fastmem con RAM EE.
- **MP07 — Custodia y publicación.** CUANDO produzca metadatos, el validador
  DEBERÁ omitir direcciones virtuales, offsets físicos absolutos, punteros host
  y bytes. La captura real DEBERÁ permanecer en raíz privada externa y el
  publicador DEBERÁ esperar al cierre verificado de todos los lectores.
- **MP08 — Alcance.** CUANDO se acepte una evidencia real de esta subetapa, el
  coordinador DEBERÁ verificar mapa y contenido en entrada, antes/después del
  par y retorno de una sesión nueva, vinculados a estados y lecturas PINE.
  DEBERÁ comparar también la continuidad del respaldo entre esas paradas.
  SI falta alguna evidencia, DEBERÁ conservar identidad física como pendiente.
  Igualdad de bytes, un fixture o un puerto host concedido no satisfacen MP08.

## Modelo de validación propio

`MappingContext` contiene `session_id`, `environment_sha256`, `process_sha256`,
`sequence`, `state_sha256`. `MappingSnapshot` añade `paused`, `ee_main`,
`exposed_ram_size`, `vmap` y una tupla ordenada de `PageEntry(virtual_page, bias)`.
Estos valores son privados; sus representaciones no incluyen campos.

`validate_mapping(before, after, expected, virtual_start, size, expected_offset)`
retorna respaldo privado y metadatos de coherencia. Solo acepta direcciones host
positivas menores que 2^63, punteros alineados y RAM expuesta de 32 MiB. Un
rango de 4096 bytes puede atravesar dos páginas. Los límites se aplican al
segmento solicitado, no a bytes ajenos al rango. Diferencia con `expected_offset`
se comunica como `matches_expected_backing: false`; no se transforma en igualdad.

El resultado no certifica que los valores procedan del emulador. La adquisición
host, la custodia y el coordinador real son responsabilidades separadas.

## Base técnica y decisión de implementación

[vtlb.h v2.8.2](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/vtlb.h)
define páginas de 4 KiB y entradas como desplazamientos respecto de la dirección
virtual. [MemoryTypes.h](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/MemoryTypes.h)
sitúa `Main` al inicio de `EEVM_MemoryAllocMess`. Los archivos consultados declaran
GPL-3.0+; se documentan hechos de ABI y se implementa validación propia, sin copiar
sus funciones ni añadir dependencia al port. No se afirma clean room.

En el ABI x86_64 observado, `vmap` sigue a 1280 punteros y 131072 entradas de ocho
bytes: offset 1058816. Este cálculo requiere validación ABI antes de emplearse
en adquisición real; no basta para aceptar un mapa. El build oficial es x86_64
y se ejecuta mediante Rosetta en este host ARM64. Si se requiere instrumentación,
se preparará un build separado con fuentes/dependencias/licencias fijadas.
