# Asociación puntual de región y vnode — v1

Parte de CI-T4. Historia: como consumidor del inventario, necesito distinguir
una asociación del kernel con un archivo de una ruta orientativa o de evidencia
sobre los bytes residentes, para no acreditar una región ajena.

## Requisitos EARS

- **VN01:** CUANDO se consulte una dirección propia, el adaptador DEBERÁ exigir
  la respuesta completa y un intervalo no vacío, sin overflow, que la contenga.
- **VN02:** SI la API devuelve otra región, un error o un formato incompleto,
  el adaptador DEBERÁ devolver unavailable y limpiar la salida.
- **VN03:** CUANDO se devuelva un vnode, el adaptador DEBERÁ exigir archivo
  regular e identidad válida y conservar dirección, tamaño y offset de región.
  El offset SHALL NOT interpretarse automáticamente como offset de bytes del archivo.
- **VN04:** SI la respuesta corresponde a un submapa o no contiene vnode,
  el adaptador DEBERÁ distinguir esos resultados de una asociación válida.
  Una ruta, un tag o una clave AOT SHALL NOT sustituir el vnode.
- **VN05:** CUANDO se consulte, el adaptador DEBERÁ comprobar el PID propietario
  antes/después y rechazar reutilización tras fork, sin asignar memoria ni abrir rutas.
- **VN06:** CUANDO exista asociación, el consumidor DEBERÁ mantener separadas
  identidad del archivo, transformación/COW y contenido residente. La asociación
  SHALL NOT conceder admisión ni afirmar que la región conserva los bytes del archivo.
- **VN07:** CUANDO se investigue el candidato, la sonda DEBERÁ contrastar consultas
  sobre regiones, segmentos transformados, registros AOT individuales y heap de
  Rosetta; conservar respuestas ausentes y cambios como resultados pendientes.
- **VN08:** CUANDO se ensaye, DEBERÁ incluir offset no nulo, punto interior,
  sustitución de archivo, COW real, región anónima, respuesta adelantada, límites,
  identidad malformada, truncamiento y cambio de PID.
- **VN09:** CUANDO se ejecute el candidato, DEBERÁ usar la copia diagnóstica
  conservada y perfil nuevo en testconfig, con límites supervisados y sin VM.
- **VN10:** CUANDO se publique, DEBERÁ preservar fuentes, recibos y resultados;
  distinguir observación local de comportamiento del código XNU consultado.

## Diseño y decisión

`MacOSRegionVnodeSource` es un adaptador independiente con llamadas inyectables
para tests. Usa exclusivamente `PROC_PIDREGIONPATHINFO` del SDK. Devuelve
`RegionVnode` y `VnodeQuery` (found/no_vnode/submap/unavailable). Solo found entrega
datos; los otros estados dejan salida vacía. Es una consulta puntual sin estado
de confianza: el consumidor debe componer estabilidad y nacimiento del proceso.
El adaptador conserva el PID de construcción; no acepta PID/task externos.

`RegionVnode` no implementa `MappingSource`: ese puerto tiene el contrato más
estricto de cabecera Mach-O en offset cero. Tampoco expone rutas ni suma al offset
la distancia al punto. El vínculo con un descriptor retenido se compara mediante
`FileObject`; digest, páginas y transformaciones pertenecen a otros componentes.
Esto conserva responsabilidades y evita ampliar implícitamente el contrato previo.

El XNU consultado recorre shadows hasta un pager vnode; no atraviesa aquí el
pager transformador ni submapas. `proc_regionfilename` usa una búsqueda que puede
avanzar a otro mapping con archivo y descarta su intervalo al devolver el nombre.
Por ello solo se recoge como dato diagnóstico, nunca como asociación acreditada.
Referencias: [bsd_vm.c](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/osfmk/vm/bsd_vm.c#L1163),
[proc_info.c](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/proc_info.c#L1137).
Ese código upstream no identifica por sí solo el kernel instalado.

## Tareas

- [x] **VN-T1 / VN01–06:** implementar el adaptador y sus estados; conservar el
  contrato previo y añadir su target al pipeline host existente.
- [x] **VN-T2 / VN08:** probar fixtures reales y respuestas inyectadas en Debug,
  Release, ASan/UBSan y cobertura; detectar regresiones de intervalo, PID e identidad.
- [x] **VN-T3 / VN07,09,10:** sondear el candidato, clasificar el origen que estas
  APIs permiten o no demostrar, auditar y publicar resultados y siguiente decisión.

El cierre de estas tareas no cierra CI-T4. Si las APIs no exponen el origen de
las transformaciones, habrá que definir otra prueba verificable; no convertir
ausencia de evidencia en una excepción de confianza.
