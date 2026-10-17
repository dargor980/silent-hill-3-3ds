# Robustez de extracción v1 — F02.06

Extiende [X01-X11](extraction-v1.md), [A01-A11](asset-catalog-v1.md) y los contratos MFA [M01-M08](mfa-probe-v1.md)/[MV01-MV08](mfa-probe-v2.md). Padres: RNF06.01/RNF06.04/RNF06.07, RNF07.06-RNF07.09, RNF11.05-RNF11.09; V20/T02. Datos exclusivamente propios.

## EARS

- **H01** WHEN se ejecuta el corpus determinista B8/D8 THEN cada mutación SHALL conservar semilla, ubicación, código esperado y límites de lectura; un fallo tardío SHALL no entregar entradas ni hashes parciales del contenedor rechazado.
- **H02** WHEN una entrada alcanza exactamente un presupuesto THEN el sistema SHALL admitirla si cumple los demás contratos. IF excede el presupuesto THEN SHALL rechazar antes de la lectura/reserva prohibida.
- **H03** IF falla reserva, apertura, transferencia de propiedad a stream, escritura, flush, fsync, relectura o publicación THEN la operación SHALL conservar el fallo y los datos anteriores, intentar cerrar todos los descriptores adquiridos sin reintentar un cierre ambiguo y no publicar aceptación del par antes de su verificación completa.
- **H04** WHEN se interrumpe por SIGKILL un proceso sintético antes de publicar el recibo final THEN la sesión SHALL quedar incompleta sin `verified.json`, SHALL rechazarse su reutilización y SHALL poder completarse un reintento con nueva sesión.
- **H05** WHEN CI ejecuta casos de interrupción THEN SHALL sincronizar por señal explícita del proceso, aplicar tiempos máximos y terminar/recolectar sus procesos hijos incluso ante fallo del test. Los puntos de interrupción SHALL existir solo en código de pruebas.
- **H06** WHEN cambia la robustez del adaptador sin cambiar parser, identidad ni transferencia de bytes THEN la evidencia real histórica SHALL conservar su versión; la regresión nueva SHALL demostrar igualdad con datos propios y no atribuir nueva ejecución real a artefactos antiguos.
- **H07** IF ocurre un error de cierre de directorios después de publicar `verified.json` y retornar el resultado verificado THEN la CLI SHALL conservar `status=verified`, emitir `cleanup_warning=OUTPUT_CLOSE_ERROR` y retornar 0. Un fallo anterior a esa publicación SHALL continuar rechazado, sin fabricar ni borrar recibos de aceptación.

## Matriz de evidencia y ampliación

| Área | Base F02.05 | Ampliación F02.06 | Oráculo |
|---|---|---|---|
| Estructura B8/D8 | Tablas/rangos/nombres/ambigüedad, bloques posteriores | Mutaciones deterministas en primer/segundo bloque, valores uint32 extremos y sumas que exceden el rango | Código MFA exacto; llamadas solo a sectores permitidos; ningún hash del contenedor rechazado |
| Presupuestos | Rechazo de límites y lecturas acotadas | Exactamente N frente a N+1 en bloques/entradas/catálogo/selección | Aceptar frontera válida; rechazo antes de trabajo fuera del límite |
| Descriptor → stream | Casos normales y errores de copia | Fallo al envolver descriptor de payload/lectura/recibo | Descriptor cerrado aun si el stream nunca obtuvo propiedad |
| Cierre y error primario | Cierre normal de directorios | Fallo del cierre anterior durante recorrido, cierre del conjunto y fallo doble | Intentar todos los cierres una vez; conservar error primario y añadir nota de limpieza |
| Filesystem | ENOSPC en copia, corrupción, enlaces y destino sustituido | Matriz por operación y fase, flush/fsync/publicación, reserva parcial y permisos inyectados | Sin recibo final; código estable; previos intactos y descriptores cerrados |
| Proceso | Excepciones recuperables | SIGKILL tras reserva, durante payload, tras copia y antes del recibo final | Sin aceptación; destino ocupado conservado; reintento nuevo válido |
| Pipeline | pytest/quality sintético | Nuevas pruebas descubiertas por el mismo job, timeouts de hijos | No ISO privada, red, dependencias nuevas ni puntos de fallo en CLI productiva |
| Publicación final | Recibo exclusivo después de verificar | Cierre de directorios fallido después de publicación | Recibo válido conservado; éxito con advertencia explícita de limpieza |

Los fallos de permisos y espacio se inyectan en llamadas concretas para que el resultado no dependa del usuario efectivo o del disco del runner. Los tests de proceso sí lanzan y terminan procesos POSIX reales con fixtures propios. Se distingue SIGKILL de pérdida de energía: no se prueba caché/controlador de almacenamiento ni durabilidad física.

La publicación exclusiva de `verified.json` es el punto de confirmación. Un error de limpieza posterior no invalida los hashes ya verificados; se informa sin convertirlo en un rechazo de extracción. Cuando falla `close`, su efecto puede depender del host; no se reintenta el mismo número de descriptor, que podría haber sido reutilizado. Los dobles que prueban esta frontera liberan primero el descriptor y luego notifican el error; la garantía es intentar todos los cierres y conservar el error principal, no asegurar que un kernel que falla haya liberado un recurso.

Los límites numéricos se ejercitan con fixtures pequeños y presupuestos reducidos temporalmente; no se crean archivos gigantes. Las mutaciones tienen códigos esperados explícitos, no un oráculo que acepte cualquier excepción. Los controles existentes no se relajan para formatos desconocidos.

La política de directorios sigue requiriendo un árbol bajo control del operador. Los descriptores anclados evitan seguir enlaces al escribir; una comprobación finita no garantiza inmutabilidad frente a otro escritor concurrente después de verificar. No se presentan pruebas adversas como cobertura de formatos ni corpus jugable.
