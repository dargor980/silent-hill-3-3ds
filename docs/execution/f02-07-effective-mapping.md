# F02.07 — Factibilidad y contrato del mapa efectivo

2026-10-17 · `camera-resource-link-eu/origin/effective-mapping` ·
[MP01–MP08](../../schemas/effective-mapping-v1.md) ·
[evidencia SRC30](../compatibility/effective-mapping-evidence.json).

**Contrato, validador puro y sondeo de acceso completados; captura real pendiente.**
El proceso oficial de PCSX2 rechaza `task_read_for_pid`: retorno `-1`, errno
`EPERM` (1), puerto nulo. La prueba se realizó fuera del sandbox de trabajo con
un perfil aislado y sin cargar el juego. No se observó ningún mapa de RAM EE.

## Resultado comprobado

Primero se comprobó el mecanismo sobre un buffer sintético del propio proceso:
puerto de lectura concedido, 15 bytes correctos mediante
`mach_vm_read_overwrite`, puerto liberado con código cero. La comprobación
inicial tenía una comparación incorrecta contra el terminador NUL del buffer;
se corrigió la longitud esperada y se repitió antes de probar PCSX2.

Para el proceso externo se fijaron ruta de ejecutable, comando del perfil nuevo
y SHA-256 del binario oficial, que sigue siendo
`10e7cc1b3180b5a9f48923f3dfc3900019cc8c0df7e280a0ea61190b86961390`.
La sesión de factibilidad es `4b97d02583cd4f55a409f9b71df342f4`.
La denegación procede de macOS, no de una revisión automática de aprobación.
El sondeo solo solicitó el puerto: no llamó a APIs de escritura, suspensión,
cambio de registros ni modificación de mapas. No se alteró firma ni protección
del binario instalado. La causa precisa de la política de macOS no se atribuye
solo a su firma; el resultado observado es la denegación de este método/contexto.

PCSX2 quedó cerrado. Se verificaron IPC desactivado, ausencia de socket,
permisos privados 0700/0600 y hashes intactos del INI, breakpoints y ambas tarjetas
del perfil habitual. El juego no llegó a cargarse en esta sesión.

## Diseño e implementación SOLID

`tools/inspectors/effective_mapping.py` implementa valores inmutables y funciones
puras. Recibe contexto esperado y dos muestras; no abre procesos, archivos ni
sockets. La futura adquisición y publicación estarán en adaptadores/coordinador
separados, aprovechando la custodia existente. No se añade una dependencia del
runtime 3DS respecto del emulador.

El validador exige cobertura exacta de una o dos páginas para hasta 4096 bytes.
Suma la dirección virtual al desplazamiento de 64 bits antes de distinguir
handler y puntero directo. Rechaza respaldo externo a los 32 MiB expuestos de
RAM EE, segmentos no contiguos, contexto mezclado y cambios entre muestras.
Un alias coherente puede ser válido como mapa y diferir del offset esperado;
esa diferencia se conserva explícita.

El offset resultante permanece en un objeto privado. `metadata()` devuelve solo
tamaño, cobertura, coherencia y coincidencia; siempre declara
`live_acquisition_verified: false` y `execution_authentication: not_provided`.
Es consistencia de valores suministrados, sin autenticación de su procedencia.
No cambia los recibos históricos, ni convierte igualdad de bytes en traducción.

**91 casos nuevos y 1.849 pruebas Python aprobadas.** Casos de borde: suma con
wrap de 64 bits, bit alto antes/después de sumar, alias, dos páginas, límite de
RAM, cobertura duplicada/incompleta, contexto de otra sesión/proceso/estado,
pausa ausente, tipos inválidos y cambio de punteros/entradas.

Cobertura del módulo: **62/62 líneas y 10/10 ramas**. Global: **3602/3647 líneas
(98,77 %) y 1144/1176 ramas (97,28 %)**. Ruff, formato y gates de cobertura y
repositorio aprobados. Artefactos JUnit/cobertura en
`build/f02-07-effective-mapping`. El job `quality` existente descubre estos
fixtures sin emulador ni originales. CI remota, build de PCSX2 y build 3DS no
se ejecutaron en esta etapa; no hay un nuevo binario de consola.

## Decisión de build y siguiente tarea detallada

Se selecciona **instrumentación dentro de un build separado**, porque el lector
externo no obtuvo acceso. El punto de partida es PCSX2 v2.8.2, commit oficial
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`. Ocho archivos de ABI, CMake, receta
de dependencias, workflow y licencia están fijados por hash en SRC30. Se
consultaron y guardaron; no se ejecutaron ni incorporaron sus fuentes al port.

El host es ARM64, pero el binario de referencia es x86_64 bajo Rosetta. La
[configuración oficial fijada](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/CMakeLists.txt)
advierte que ARM64 carece de recompiladores EE/VU/IOP. Se prioriza x86_64 para
preservar el entorno de referencia; un cambio a intérprete requeriría ensayar
de nuevo compatibilidad y tiempos, sin asumir equivalencia de ejecución.

Preflight local: CMake 4.2.3, Apple Clang 15.0.0 y Command Line Tools; `xcrun
--find metal` termina con código 72. No se encontró Qt en `/usr/local/opt/qt`;
el Qt observado en Homebrew ARM64 no acredita dependencias x86_64. La
[receta oficial](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/.github/workflows/macos_build.yml)
utiliza Xcode 26.2 y Metal Toolchain. Esto es un inventario de requisitos,
no una compilación fallida ni una incompatibilidad global demostrada.

Sigue **`origin/effective-mapping/instrumented-build`**:

1. **Entorno aislado y reproducible.** Obtener checkout del commit fijado en raíz
   privada separada; conservar licencia/avisos y hashes de fuentes, parches y
   dependencias. Revisar la receta antes de ejecutarla, fijar prefijo x86_64 y
   resolver toolchain Metal o una alternativa soportada por el CMake concreto.
   No usar `latest`, reemplazar la app habitual ni modificar su firma.
2. **Build base.** Compilar primero sin cambios, registrar compilador, SDK,
   arquitectura, flags y manifiesto del bundle. Ejecutar sus tests y arrancar
   con perfil aislado. Verificar compatibilidad del estado de entrada por hash,
   PC/GPR y contenido antes de añadir instrumentación.
3. **Exportador acotado.** Añadir observación interna de `vmap` y base EE solo
   durante pausa, sincronizada con el hilo de CPU. Límite de 4096 bytes y dos
   páginas; no ejecutar handlers ni escribir memoria. Protocolo local privado,
   desactivado por defecto, con versión/identidad y rechazo de rangos inválidos.
   Conservar punteros únicamente en la captura privada. No ampliar acceso global.
4. **Contrato del adaptador.** Ensayar pausa/cierre fallidos, tamaños/identidades
   incorrectos, cambio de mapa y captura incompleta; conectar las muestras con
   MP y el lector privado existente. Verificar layout en el build real, no solo
   por aritmética del offset de estructuras. Publicar únicamente tras cierres.
5. **Observación y aceptación.** Nueva sesión de juego con entrada, par BEQ+SW
   y retorno; verificar mapa y contenido de cada parada y estabilidad del
   respaldo entre paradas. Contrastar PINE y RAM del estado usando el offset
   demostrado. Dos análisis idénticos y gates aprobados antes de aceptar MP08.

El cargador anterior a A y los otros escritores continúan después de esta
observación. F02.07/Q05/G02, semántica de campos y salas siguen pendientes.
