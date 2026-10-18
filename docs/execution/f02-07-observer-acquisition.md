# F02.07 — Coordinador de adquisición del observador

Unidad: `origin/effective-mapping/observer-acquisition-coordinator`.
Fecha: 2026-10-18. Estado: **implementación y pruebas sintéticas completas;
rechazo real sin VM verificado; adquisición positiva del juego pendiente**.
Contrato [AC01–AC10](../../schemas/observer-acquisition-v1.md),
[evidencia SRC52](../compatibility/observer-acquisition-evidence.json).

## Resultado y ABI

El coordinador vincula tres muestras del observador, un estado nuevo y las
lecturas PINE de la misma ventana. Rechaza discrepancias antes de publicar
metadatos. No incorpora código al runtime Nintendo ni modifica el binario
instrumentado de SRC51.

Un programa propio compilado con las cabeceras y opciones reales del adaptador
SRC51 confirma `sizeof(cpuRegisters)=1160`, PC en 680, delay slot en 676 y
ciclo u64 en 1088. Se contrastaron `R5900.h`, `SaveState.cpp`, `VMManager.cpp`
y `PINE.cpp` de la revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`.
La serialización guarda cpuRegs completo. El CRC del estado corresponde al
ELF activo; PINE/observador identifican el disco. La adquisición exige que
ambos coincidan con el esperado; no los trata como conceptos intercambiables.

[observer_state](../../tools/inspectors/observer_state.py) exige el bloque
completo y preserva ciclos de 64 bits. El lector PS histórico conserva su
prefijo y sus consumidores. Un estado truncado, con versión distinta, delay
slot, CRC inesperado o ventana fuera de RAM se rechaza.

## Responsabilidades y secuencia

La separación sigue SOLID: [el coordinador](../../tools/inspectors/observer_acquisition.py)
depende de puertos de canal, custodia, identidad, reloj y espera. El transporte
posee la conexión; el lector interpreta el estado; la custodia controla archivos;
el guard verifica proceso/perfil; el publicador confirma únicamente metadatos.
Las pruebas sustituyen esos puertos sin necesitar originales ni emulador.

1. Verificar ejecutable/perfil, PID e inicio del proceso, socket y contexto.
2. Tomar lock exclusivo en un directorio privado anclado y exigir estado/backup
   ausentes; conectar una vez y contrastar el PID del peer obtenido del kernel.
3. Comprobar pausa/CRC y obtener A; volver a comprobar ausencia y solicitar
   **un solo SaveState**. Consultar B hasta que no haya guardado pendiente.
4. Exigir A=B, un archivo nuevo regular 0600 y estable, su hash, RAM/PC/ciclo
   coherentes y lecturas PINE idénticas del rango virtual solicitado.
5. Obtener C, exigir A=B=C y releer el estado; conservar tres paquetes privados.
6. Cerrar conexión, lectores y lock; revalidar identidad y publicar el recibo.

El deadline lógico es de 30 segundos y B tiene un máximo de 256 consultas.
Solo `SAVE_PENDING` admite otra consulta; no hay reconexión ni otro SaveState.
Los sockets usan el tiempo restante y los procesos de identidad tienen timeout;
el I/O local regular no se interrumpe preventivamente, pero un presupuesto
agotado impide aceptar el resultado. El tamaño del estado se limita a 64 MiB
y la ventana a 4.096 bytes. Se conserva cualquier alias que difiera del
respaldo esperado, en vez de normalizarlo.

El resultado de SaveState indica encolado, no escritura exitosa. Una cola
vacía tampoco demuestra que exista el archivo. Las pruebas incluyen ambos
replies válidos seguidos de un archivo ausente y exigen rechazo.

## Custodia y publicación

[observer_files](../../tools/inspectors/observer_files.py) ancla directorios,
rechaza enlaces y cambios de identidad/permisos/contenido detectables, y
cierra cada descriptor poseído incluso cuando otro cierre falla. El lock
permanece como inode estable y se libera por cierre; coordina clientes
cooperantes, sin impedir todos los escritores del mismo usuario.

La publicación escribe un temporal exclusivo, hace flush/fsync y lo cierra
antes de enlazarlo sin sobrescribir el destino. Ese enlace es el punto de
commit. Si falla fsync/cierre del directorio después, devuelve
`ACQUIRE_PUBLISH_COMMITTED`: puede haber metadatos visibles y no se promete
rollback ni se reintenta automáticamente. Temporales y fallos se conservan.

[observer_identity](../../tools/inspectors/observer_identity.py) vincula el
recibo de lanzamiento con hashes del ejecutable y perfil, directorio explícito
de estados, PINE habilitado, proceso observado por ps/lsof y socket privado.
Esto detecta mezclas accidentales; no autentica una ejecución frente a un
proceso host adversario. El recibo usa `consistent_supplied_acquisition` y
`state_binding_verified=true` para coherencia entre entradas suministradas;
mantiene `live_acquisition_verified=false`, autenticación no provista y MP08
pendiente. La evidencia de sesión real debe registrarse por separado.

## Integración local real

Se revalidaron los 2.934 archivos del baseline, 2.941 de la fuente instrumentada
y el prefijo de 5.228 archivos/70 enlaces. El parche conserva SHA-256
`a4072fb169db8376a657b2e8c578d5cb9777ce361678f03cda92ecea205abbd0`.
El ejecutable probado conserva SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
No se recompilaron PCSX2 ni dependencias.

El candidato abrió con perfil aislado, TMPDIR corto 0700 y umask 077, sin
cargar BIOS ni juego. El primer guard rechazó `ACQUIRE_PROFILE`: Qt había
normalizado el INI al inicializar la UI. Se reconstruyó la entrada, se
comprobó su hash y se compararon las claves; la única diferencia semántica
fue `GameListTableView/HeaderState`. Se conservó el recibo inicial y se fijó
un nuevo hash después de esa inspección. No se relajó el guard ni se permite
actualizar el hash durante una adquisición fallida.

La integración posterior verificó PID del peer, tres consultas de estado
en una conexión, proceso/perfil/socket estables y rechazo `ACQUIRE_PAUSE`
del coordinador antes de solicitar SaveState. No apareció ningún estado,
paquete ni recibo de aceptación. Otra conexión pudo consultar el estado
después del rechazo, confirmando que el servidor seguía disponible.

El depurador se observó en español con controles de ejecución deshabilitados.
El cierre desde la UI terminó con código cero, grupo cerrado y socket
eliminado. La sesión supervisada duró 57,032 segundos; ese tiempo incluye
inspección e interacción y no mide latencia de adquisición. Se aplicaron
plazo de sesión de 180 segundos, presupuesto de etapa de 8 GiB y suelo de
10 GiB. No se aplicó una reserva de compilación porque no hubo build grande.

## Validación

Se añadieron **124 casos** respecto de SRC51; la regresión final pasa
**2.196 pruebas en 20,48 segundos**. Cubre ciclos altos, ABI truncada,
framing, identidad/peer cambiados, timeout y agotamiento de consultas,
pendientes, CRC/PC/mapa/contenido inconsistentes, estados previos/ausentes,
aliases, permisos/enlaces, cambios durante lectura/cierre, fallos de I/O y
publicación antes/después del commit. La integración positiva completa
combina productor sintético, filesystem real y publicación; su RAM es propia.

| Módulo | Líneas | Ramas |
|---|---:|---:|
| observer_acquisition | 109/109 | 8/8 |
| observer_state | 21/21 | Sin ramas |
| observer_transport | 109/109 | 38/38 |
| observer_identity | 55/55 | 2/2 |
| observer_files | 137/137 | 15/16 |
| Total herramientas | 4.216/4.261 (98,94 %) | 1.257/1.290 (97,44 %) |

El gate independiente 80/80, Ruff/formato y contratos del repositorio pasan.
El job Python existente descubre los nuevos tests y publica sus reportes sin
ISO, BIOS ni PCSX2; la CI remota no se ejecutó aquí. El peer macOS se probó
realmente; la variante Linux del transporte solo con dobles. No se repitieron
las suites C++/proveedor porque sus fuentes, parche y ejecutable no cambiaron.

Se conservan los resultados intermedios: el primer lote falló por comparar
el texto del error en vez de su código; se corrigieron esas aserciones. Una
pasada parcial aprobó sus tests pero no el gate global de cobertura al medir
solo el subconjunto; la pasada completa final supera ambos umbrales. Los
reportes no sustituyen esos fallos históricos por una supuesta primera pasada
sin incidencias.

## Próxima tarea

Sigue `origin/effective-mapping/observer-acquisition-live-session`. Preparar
la ISO europea y BIOS privadas con el candidato exacto; fijar perfil español,
acción Normal y acertijos Normal; verificar una primera adquisición positiva
antes de extenderla a entrada/pre-SW/post-SW/retorno. El
[ticket F02](../specs/sh3-3ds/tasks/F02.md) detalla custodia, puntos y criterios.

Esta entrega no capturó memoria del juego. Cuatro paradas MP08, continuidad
física, cargador/relación semántica de recurso, otros escritores, dos salas,
F02.07, Q05/G02 y pruebas en la New Nintendo 2DS XL permanecen abiertos.
