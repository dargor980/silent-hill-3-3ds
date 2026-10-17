# F02.07 — Escritura repetida y retorno capturado

2026-10-17 · `camera-resource-link-eu/origin/runtime-writer/repeat-return` ·
[RR01–RR07](../../schemas/camera-return-v1.md) ·
[evidencia SRC29](../compatibility/camera-return-evidence.json).

**Subetapa completada:** una segunda sesión reproduce el par BEQ+SW de SRC28,
con el mismo código, offset 84 y cambio de tres bytes `[85,88)`. También alcanza
el retorno de A: los 1.536 bytes coinciden íntegramente con el retorno histórico
de SRC27. Respecto de la entrada siguen difiriendo los mismos 40 bytes en 16
intervalos. Mapeo efectivo, cargador, otros escritores y F02.07/Q05/G02 siguen pendientes.

## Evidencia de ejecución

Se usó perfil privado nuevo, copia verificada de la entrada histórica, tarjetas
copiadas y watchpoint de cuatro bytes `[84,88)` configurado antes del arranque.
El breakpoint de retorno también estaba preparado. No fue necesario desactivar
la casilla del watchpoint durante la ejecución.

| Secuencia nueva | Parada | Resultado |
|---|---|---|
| 1 | Entrada A restaurada | PC/GPR y rango completo coinciden con la referencia |
| 2 | Antes de BEQ+SW | Rango completo igual al candidato |
| 3 | Después del paso | Solo tres bytes diferentes, `[85,88)` |
| 4 | Retorno A | 40 bytes distintos de entrada; cero diferencias con retorno histórico |

El PC final coincide con GPR31 de la entrada y con el PC del estado histórico de
retorno; no está en delay slot. La base de memoria se conserva desde entrada:
el cambio de GPR4 al retornar no desplaza el rango examinado. Todas las lecturas
virtuales coinciden con el rango físico hipotético de su estado correspondiente.

La sesión nueva es `3890d08bb2814358988090f3f32effcb`; SRC28 conserva
`71797d5333e44b15861b1eb22fa0bbe6`. No se mezclan sus secuencias. La comparación
del par excluye números de secuencia y exige igualdad de clase, flujo, hash del
código, offset/ancho, hashes del rango y diferencias. SRC28 se reproduce desde
su captura privada y debe coincidir exactamente con su recibo fijado.

El retorno histórico se relee desde una copia con SHA-256
`72acdb38cb937425d5639e2c62a4ef505a3b67f9974ea549700c2fb18455e632`.
El rango de retorno, histórico y nuevo, tiene SHA-256
`4826f98efad530eb84f1f04b4bed7879d6143b1c4fc2ef1044244317a6656d52`.
Es una repetición de la escritura y del contenido final, no observación de todas
las instrucciones que explican los otros 37 bytes modificados.

Las tres reanudaciones quedaron entre lecturas del reloj UTC `20:07:38` y
`20:08:36`, con estados pausados antes y después. Esa ventana de pared incluye
capturas y control de UI; no mide tiempo de CPU ni rendimiento. Se observó un hit
del watchpoint seleccionado y el retorno. El subrango no cubre todas las escrituras.

PCSX2 se cerró; se comprobaron ausencia de proceso y socket, IPC desactivado,
permisos privados y hashes intactos del INI, breakpoints y ambas tarjetas del
perfil habitual. No se modificaron originales, capturas ni recibos históricos.

## Implementación y pruebas

`camera_writer` comparte validación y custodia mediante un modo explícito de
retorno. El modo parcial mantiene exactamente el recibo histórico de SRC28.
Sus hashes de código anteriores se conservan como procedencia de aquella versión;
SRC29 registra los hashes de la extensión actual.

`return_compare` valida punto/orden/referencia y compara rangos y pares sin I/O.
`camera_return` reproduce SRC28 y coordina la captura nueva. Una discrepancia
coherente se publica como diferencia; identidad errónea, captura parcial o fallos
de archivo/cierre impiden publicar un recibo de retorno observado.

**38 pruebas nuevas; 1.758 pruebas Python aprobadas.** Incluyen retorno temprano,
PC/delay slot erróneos, sesión reutilizada, GPR4 de retorno cambiado, referencia
histórica alterada, pares/retornos distintos y fallos tardíos. Ruff, formato,
gate de cobertura y controles del repositorio aprobados. Cobertura global:
**3540/3585 líneas (98,74 %)** y **1134/1166 ramas (97,26 %)**.
JUnit y cobertura están en `build/f02-07-camera-return`.

El job `quality` existente descubre estos fixtures propios; CI remota y compilación
C++/3DS no se ejecutaron en esta etapa de herramientas Python.

## Reproducción y alcance

Informes `reports/local/f02-07-camera-return-v1.json` y
`reports/local/f02-07-camera-return-v1-repeat.json`: **9.478 bytes**, SHA-256
`3d5bd69b282de39eb17b633e9558f111ebf731cdee7b5b532925b99cecf96914`.
Son dos análisis de la misma captura nueva, además de la comparación entre dos
sesiones reales. CLI: `rtk proxy .venv/bin/python -m tools.inspectors.camera_return --help`.
Argumentos fijados: `build/f02-07-camera-return/inputs.json`.

Captura nueva SHA-256
`593b73a75f5a4d33f1ed688b91a9d9836c1346d891d76962b6852aa5718b6f3d`.
Estados, instrucciones, registros y lecturas originales permanecen en la raíz
privada externa. El recibo publica solo metadatos. La declaración de sesión/pausa
no es autenticación independiente: `execution_authentication: not_provided`.
No se emiten `resource_links` ni capacidades.

## Siguiente tarea: observar el mapa efectivo

`F02.07/camera-resource-link-eu/origin/effective-mapping`:

1. Fijar EARS para relacionar cada página virtual del candidato con su respaldo
   de RAM EE en una sesión pausada. Exigir identidad de estado/entorno y rango
   completo; no aceptar igualdad de contenido como traducción.
2. Evaluar un observador local de solo lectura del mapa interno `vmap`, diferenciando
   páginas directas, handlers y regiones ajenas a RAM EE. PINE v2.8.2 no incluye
   una operación de traducción en su enumeración de comandos; las lecturas actuales
   no cubren esa evidencia. Si se necesita instrumentación, preparar build separado
   y revisión de versión/licencia antes de usarlo con datos privados.
3. Implementar fixtures propios para alias, páginas no contiguas, handlers, límites,
   cambio de mapa entre paradas y captura de otra sesión. No publicar punteros host.
4. Capturar mapa y contenido en entrada/par/retorno de una sesión nueva. Publicar
   identidad física solo si todas las páginas están demostradas; después continuar
   con otros escritores y la carga anterior a A. Restaurar entrada no prueba carga.

Base técnica consultada: [PINE.cpp v2.8.2](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/PINE.cpp)
y [vtlb.cpp v2.8.2](https://raw.githubusercontent.com/PCSX2/pcsx2/v2.8.2/pcsx2/vtlb.cpp).
El mapa efectivo traduce a respaldo host; no debe confundirse un offset de memoria
compartida del emulador con dirección física EE. Esta observación aún no se ejecutó.
