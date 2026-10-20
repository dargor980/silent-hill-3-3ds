# F02.07 — Asociación de regiones con archivos y límite de Rosetta (SRC100)

VN-T1–3 implementa y valida [VN01–VN10](../../schemas/native-region-vnode-v1.md).
La sonda identifica el archivo de las **24/27 traducciones AOT** de arranque/salida,
incluido dyld. Sus rutas no pueden abrirse (EPERM) y no aparecen descriptores
retenibles en esas dos observaciones. La identidad puntual avanza; los bytes
de los archivos AOT y la integración CI-T4 siguen sin acreditar.

## Implementación y pruebas

`MacOSRegionVnodeSource` exige PID propio, respuesta completa, intervalo que
contenga el punto e identidad válida de archivo regular. Distingue asociación,
ausencia de vnode, submapa y error. Todos los resultados distintos de asociación
limpian la salida. Conserva el offset de región como metadato, sin convertirlo
en una prueba de offset del archivo. No devuelve rutas, no abre archivos ni
asigna memoria en la consulta.

El componente mantiene su responsabilidad separada del verificador de cabeceras
Mach-O, de los descriptores retenidos y de los verificadores de bytes/páginas.
La API inyectable permite probar errores del kernel sin debilitar el contrato.
El target CMake amplía automáticamente el pipeline host existente.

| Validación local macOS x86_64 | Resultado |
| --- | --- |
| Debug, Release, ASan+UBSan y cobertura | 228 escenarios × 4 = 912 ejecuciones correctas |
| Escenarios nuevos | Ocho; conserva los 220 anteriores |
| Adaptador | 26/26 líneas, 54/58 ramas (93,10%) |
| Regresiones compiladas | Cuatro detectadas |
| Compatibilidad Python | 122 pruebas correctas |

Los negativos aceptan una región posterior, omiten PID propietario, admiten un
directorio o confunden un submapa con archivo. Las fixtures reales cubren offset
no nulo, punto interior, sustitución de nombre, región anónima y fork. La prueba
COW modifica un byte de memoria de 17 a 39 mientras el archivo conserva 17 y el
vnode sigue siendo el mismo: asociación no significa igualdad de contenido.
CI remoto, Linux, arm64, SDK antiguos y detección de fugas no se ejecutaron.

## Censo y atribuciones incorrectas que se evitan

La primera sonda usa la copia diagnóstica conservada y testconfig. En el arranque
enumera 624 regiones y 556 imágenes; registra 3262 consultas puntuales, incluidas
tres del control. Cada punto conserva su hoja estructural antes/después de las
consultas. Esto no constituye una instantánea atómica ni prueba ausencia de ABA.

| Puntos del arranque | Asociados | Sin vnode | Submapa |
| --- | ---: | ---: | ---: |
| Inicios de las 624 regiones | 190 | 356 | 78 |
| Inicios de 2587 segmentos legibles | 91 | 990 | 1506 |
| Inicio y último byte de 24 registros AOT | 48 | 0 | 0 |

Los **1385 puntos** de datos limpios/externos sin referencia conocida se agrupan
en los mismos **14 objetos candidatos transformados**: 947 consultas sin vnode y
438 correspondientes a submapas. La API ensayada no demuestra su archivo de origen.
Las asociaciones de extremos AOT corresponden a 24 archivos distintos y al mismo
archivo en cada pareja; no verifican páginas interiores ni transformaciones.

El control real coloca una región anónima delante de otra respaldada por archivo.
`proc_regionfilename` devuelve para la primera el nombre de la segunda. También
devuelve `/Library/Apple/usr/libexec/oah/libRosettaRuntime` al consultar el heap
RWX de Rosetta de 134201344 bytes, aunque la consulta de vnode no lo asocia a ningún
archivo. Esas rutas no se usan como prueba de identidad.

El código [XNU consultado](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/bsd_vm.c#L1163)
explica que la búsqueda puede avanzar a otro mapping y que la consulta de vnode
solo atraviesa shadows hasta un pager de archivo, sin resolver aquí submapas ni
pagers transformadores. El [wrapper de la consulta](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/proc_info.c#L1137)
usa esa búsqueda. Esto es evidencia upstream; la conducta local se prueba aparte.

El censo completo tarda 9,14 s, de los cuales 251 ms corresponden al mapa de dos
pasadas. Incluye miles de consultas y salida diagnóstica, no hashing de archivos.
En la salida del proceso el mapa cambia durante la adquisición: se descarta,
sin publicar un prefijo. Se conserva el fallo del lanzador por ausencia del censo
final aunque PCSX2 termine testconfig con código cero. No se repite para ocultarlo.

## Acceso a los archivos AOT

La segunda sonda tiene otro objetivo: consultar solo AOT y los descriptores del
propio proceso. Copia dos veces los registros AOT, contrasta extremos y vuelve a
comprobar registros y lista de descriptores al terminar. La lista tiene capacidad
4096 y rechaza llenado/truncamiento; no escanea descriptores de otros procesos.

| Observación | Arranque | Salida |
| --- | ---: | ---: |
| Registros y parejas con el mismo archivo | 24 | 27 |
| Tamaño agregado de archivos según vnode | 75234821 | 76979382 |
| Intentos de apertura con EPERM | 24 | 27 |
| Descriptores enumerados del proceso | 3 | 3 |
| Descriptores asociados a esos AOT | 0 | 0 |
| Duración de la sonda | 2,05 ms | 1,77 ms |

Los conjuntos AOT y de descriptores permanecen iguales dentro de cada observación.
No se leen los bytes de esos archivos: sus tamaños proceden de metadatos y no
son cobertura validada. Apple [documenta el almacén protegido de Rosetta y la
entrega de descriptores](https://support.apple.com/es-es/guide/security/secebb113be1/web);
en las fases ensayadas no quedan descriptores ordinarios retenibles. No se cambia
ningún permiso ni se solicita acceso al servicio privilegiado.

## Custodia y siguiente decisión

Se conservan cuatro etapas privadas: builds, censo, acceso AOT y negativos.
Scripts, snapshots, perfiles y recibos están bajo `build/f02-07-region-vnode/`
y la carpeta privada autorizada. Cada comando supervisado exige 10 GiB libres,
piso 10 GiB y máximo 512 MiB por etapa; configure 45 s, build 120 s y tests/sondas
60 s. Se verifica la copia diagnóstica contra el manifiesto previo de 200 archivos.
No se modifica el candidato original, fuentes PCSX2, perfil productivo ni VM.

La siguiente tarea es resolver la [frontera de confianza de la plataforma](f02-07-platform-trust-decision.md):
perfil explícito que asuma macOS como base o mantener la garantía exhaustiva y
estudiar otro entorno. Ninguna opción está aplicada. El adaptador no concede
admisión y no completa el origen de datos transformados, AOT o heap JIT.
Observation, peer, captura y `read_ram` continúan cerrados.
