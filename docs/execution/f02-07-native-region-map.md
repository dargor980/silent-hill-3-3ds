# F02.07 — Mapa virtual y cobertura AOT pendiente (SRC99)

NV-T1–3 implementa y prueba la enumeración estructural bajo
[NV01–NV10](../../schemas/native-region-map-v1.md). El recorrido completo descubre
regiones fuera del inventario Mach-O: **6.076.268.544 bytes de caché AOT** y hasta
**77.910.016 bytes de traducciones AOT individuales** en las observaciones válidas.
Son direcciones virtuales; no representan RAM física ni páginas acreditadas.

## Implementación y alcance

El núcleo portable recibe un puerto de regiones y compara dos recorridos desde
cero hasta fin explícito. Reserva y prepara sus 65536 entradas antes de consultar;
no asigna memoria durante las pasadas. Rechaza submapas sin resolver, errores,
retrocesos, overflow, capacidad agotada y cambios. Devuelve salida vacía al fallar.
El adaptador macOS comprueba PID y formato v2, pide hojas hasta profundidad 64 y
conserva campos estructurales, excluyendo contadores volátiles de páginas.

La [implementación publicada de XNU](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/vm_map.c#L14191)
describe el descenso según profundidad y la devolución de la siguiente región
cuando la dirección cae en un hueco. Se usa como referencia; no identifica la
versión instalada. El ID de región no se sustituye por el objeto de una página.
Dos pasadas iguales no son un snapshot atómico ni descartan cambios ABA.

La sonda copia dos veces los registros AOT del loader y comprueba sus metadatos
de cambio. Contrasta sus rangos con las hojas del kernel. La lectura AOT de esta
sonda es diagnóstica; aún no es un proveedor integrado de identidad del runtime.
Las claves AOT publicadas por el loader no se aceptan como hashes de archivos
verificados. Los tags y flags tampoco se convierten en una lista de confianza.

## Censos de la copia diagnóstica

| Medida | Sonda 1: inicio | Sonda 1: salida | Sonda 2: inicio |
| --- | ---: | ---: | ---: |
| Regiones | 619 | 779 | 623 |
| Bytes virtuales totales, incluidas reservas | 448445767680 | 449418924032 | 448730980352 |
| Imágenes Mach-O | 556 | 644 | 556 |
| Tiempo de enumeración de dos pasadas | 231,28 ms | 253,57 ms | 228,24 ms |
| Registros AOT individuales | 24 | 27 | 24 |
| Bytes AOT individuales | 76058624 | 77910016 | 76058624 |
| Regiones anidadas con punto asociado a caché AOT | 14 | 14 | 14 |
| Bytes de esas regiones | 6076268544 | 6076268544 | 6076268544 |

Las regiones anidadas contienen dos mappings por cada una de las siete partes
AOT. Sus primeros puntos se asocian a los objetos de referencias retenidas; no se
recorren sus páginas interiores. Sus intervalos y los registros AOT individuales
son disjuntos y quedan fuera de los segmentos Mach-O censados. El análisis
independiente comprueba cobertura y sumas: en la salida válida son **6154178560
bytes virtuales adicionales**. Los segmentos Mach-O activos sí están cubiertos
estructuralmente por las regiones enumeradas en esas observaciones.

Un registro AOT no tenía imagen x86 en la lista del loader. La segunda sonda
comprobó que su dirección coincide con `dyldImageLoadAddress`: es el propio dyld.
Eso identifica la dependencia omitida, sin demostrar aún su origen de archivo.

En los tres mapas válidos hay una región con tag `VM_MEMORY_ROSETTA_EXECUTABLE_HEAP`,
flag JIT, permisos RWX y **134201344 bytes**. Es cobertura del runtime de traducción
del host que requiere tratamiento explícito; no demuestra el estado del JIT de
EE/VU/IOP del juego. Describir solamente los mappings de caché AOT sería insuficiente.

La salida de la segunda sonda devolvió **changed** durante la adquisición del
mapa y se descartó: no publicó hojas ni un prefijo como mapa válido. El proceso
terminó testconfig con código cero, pero el lanzador registró la ausencia del
censo final. Se conserva ese fallo; no se repitió hasta obtener un resultado verde.

Estos costes no deben trasladarse a cada diagnóstico del hilo CPU. Tampoco
incluyen hashing completo de caché ni verificación exhaustiva de páginas.
Las referencias conservadas y la revisión del loader permanecieron estables en
las observaciones válidas; su continuidad posterior sigue siendo otra obligación.

## Pruebas y custodia

| Verificación final | Resultado |
| --- | --- |
| Debug / Release / ASan+UBSan / cobertura, macOS x86_64 | 220 escenarios × 4 = 880 ejecuciones correctas |
| Escenarios añadidos | 11 portables y 4 nativos; conserva los 205 anteriores |
| Núcleo portable | 100% líneas (44/44), 98,57% ramas (69/70) |
| Adaptador macOS | 100% líneas (26/26), 100% ramas (24/24) |
| Controles de regresión | Cuatro detectados, repetidos con el snapshot final |
| Compatibilidad Python | 122 pruebas correctas |
| Ruff / repositorio / enlaces | Sin errores |

Los controles omiten una pasada, truncan el mapa, ignoran permisos o confunden
un error con fin. La primera etapa falló por una cabecera faltante; se conservó
y corrigió el include. En la segunda, dos expectativas de tests fallaron bajo
ASan: una sonda aislada confirmó más de 65536 regiones, con rechazo tras 65537
consultas. Se mantuvo el límite. El test final verifica ese rechazo completo
bajo ASan y prueba el cambio real de permisos en un fixture nativo acotado.
Debug/Release/cobertura comprueban además un mapa completo del proceso de test.
La etapa intermedia retiene sus 660 ejecuciones, dos fallidas; no se suman a las
880 ejecuciones correctas finales. No hubo informe de corrupción de ASan/UBSan.

Se conservaron tres etapas de build, dos sondas testconfig, dos etapas de
regresiones y el diagnóstico de capacidad en la carpeta privada autorizada.
Scripts/recibos: `build/f02-07-region-map/`. Límites supervisados: 10 GiB libres
iniciales/piso, 512 MiB por etapa, hasta 120 s de compilación y 60 s por suite/sonda.
El CMake host amplía el pipeline existente. CI remoto, Linux, arm64, SDK antiguos
y detección de fugas no se ejecutaron. Los 200 archivos de la copia diagnóstica
se contrastan con sus hashes previos. Se usan perfiles nuevos y solo testconfig,
sin pedir ISO/BIOS/VM ni modificar el candidato original.

## Siguiente trabajo de CI-T4

1. Acreditar el origen de los 14 objetos de datos transformados de SRC97/98 y
   de las traducciones AOT individuales, incluido dyld; las referencias actuales
   solo vinculan puntos de las partes de caché.
2. Definir evidencia de origen y ciclo de vida para el heap ejecutable de Rosetta,
   sin una excepción general por tag, ruta, flag o pertenencia al sistema.
3. Integrar las regiones requeridas y las dependencias AOT con el planificador,
   sin inventar una longitud inicializada/zero-fill que estos metadatos no prueban.
4. Componer verificación completa de páginas con nacimiento, revisiones,
   archivos y una estrategia acotada de revalidación fuera del camino crítico.

NV-T1–3 cierra la enumeración y su diagnóstico, no CI-T4. Observation, peer,
admisión y captura permanecen sin habilitar.
