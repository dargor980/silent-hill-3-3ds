# Contrato de evidencia de depuración — F01.05

Deriva de RF14.03 y RNF12.01. Criterios locales; no cambia la matriz global.

| Criterio EARS | Evidencia requerida |
|---|---|
| D01: WHEN termina un build 3DS THEN el pipeline SHALL conservar un manifiesto que vincule build ID, 3DSX y ELF por tamaño y SHA-256 | Manifiesto generado después de compilar y enlazar, junto a los artefactos |
| D02: WHEN se verifica una sesión THEN la herramienta SHALL comparar los artefactos contra el manifiesto registrado para esa sesión | Comprobación de contenido, sin depender de nombre o fecha |
| D03: IF falta un archivo, está alterado o procede de otro build THEN la herramienta SHALL rechazar la evidencia antes de recomendar cargar sus símbolos | Pruebas con ELF/3DSX distintos, truncamiento y manifiesto inválido |
| D04: WHEN se investiga el error sintético THEN el registro SHALL identificar dirección, función/línea, build y entorno | Resolución estática separada de breakpoint realmente alcanzado |
| D05: WHEN se declara ejecución en emulador o consola THEN el registro SHALL incluir versión/configuración, resultado observado y transcripción del depurador del mismo build | Un test host o breakpoint configurado no equivale a breakpoint alcanzado |
| D06: IF no está disponible un entorno requerido THEN la tarea SHALL mantener abierta su instancia y conservar la causa y el procedimiento pendiente | No se cierra G01 por preparación de herramientas |

## Diseño

La herramienta host genera/verifica metadatos de integridad, sin conectarse a un depurador ni ejecutar binarios. Solo admite nombres fijos `sh3_diagnostic.3dsx` y `sh3_diagnostic.elf`; el manifiesto no contiene rutas arbitrarias. El script de build registra el ID calculado por CMake y crea el manifiesto después del enlace. La verificación recibe el ID esperado de la sesión, además del manifiesto conservado; no regenera hashes para aprobar archivos ya mezclados.

El build ID es una etiqueta de fuentes/CMake, no una firma de autenticidad ni identidad completa del toolchain. SHA-256 vincula los bytes exactos dentro de una evidencia confiable; el manifiesto no protege frente a sustituir simultáneamente archivos y evidencia. El SDK/GDB comprueba símbolos y líneas por separado. No se implementa un lector ELF ni un cliente GDB nuevo.

Los fallos sintéticos se provocan mediante el fixture propio ausente/inválido o puntos de ruptura en la composición; no se corrompe memoria ni se induce un crash de consola. Conservar el ELF del mismo build y registrar cualquier desplazamiento de carga antes de simbolizar direcciones runtime.
