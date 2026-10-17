# F02.06 — robustez de extracción por variante

17 de octubre de 2026. **Completada para los contratos B8/D8 y el exportador POSIX actual**. La batería llega a **828/828 pruebas Python aprobadas**, con **142 nuevas**, e incluye SIGKILL real de procesos sintéticos. Se corrigieron errores de propiedad/cierre de descriptores y de estado de la CLI después de publicar un recibo. [Ticket](../specs/sh3-3ds/tasks/F02.md#f0206), [matriz y EARS H01-H07](../../schemas/extraction-hardening-v1.md).

No se añadieron formatos ni se relajaron rangos, nombres, hashes o identidad. XBG0, AFS, semántica de recursos y selección del corpus siguen pendientes. G02 permanece abierto.

## Hallazgos y correcciones

| Frontera | Fallo reproducido antes del cambio | Comportamiento corregido |
|---|---|---|
| Descriptor → stream de payload, relectura o recibo | `fdopen` fallaba y el descriptor recién abierto quedaba sin propietario ni cierre | `_owned_stream` conserva la propiedad hasta que `fdopen` acepta el descriptor; si falla, intenta cerrarlo |
| Liberación del conjunto de directorios | El primer error de `close` interrumpía los cierres restantes; podía sustituir el error de la operación | Se intentan todos los cierres, se consumen los identificadores del adaptador y se conserva el error principal con una nota de limpieza |
| Recorrido de componentes de raíz | Un error al cerrar el directorio anterior dejaba abierto el nuevo y podía provocar un segundo cierre del anterior | La propiedad pasa al descriptor nuevo antes de cerrar el anterior; la recuperación libera el descriptor que todavía posee |
| Fallo doble al abrir stream y limpiar | El error de limpieza ocultaba el error primario | Se conserva el error inicial y se añade nota; no se reintenta un número de descriptor ambiguo |
| Limpieza después de publicación final | La CLI informaba `rejected` aunque ya existía un `verified.json` válido | Conserva `verified`, exit 0 y añade `cleanup_warning=OUTPUT_CLOSE_ERROR` |

Se conservan ocho casos de regresión observados fallando antes de su corrección: cinco en `build/f02-06/regression-before-complete.log`, dos en `regression-before-walk.log` y uno en `regression-before-commit-status.log`. El primer diagnóstico de las tres fugas también está en `regression-before.log` y su comando en `regression-before.json`. Los casos corregidos forman parte de la suite final; no se eliminaron sus aserciones.

La publicación exclusiva del recibo final es el punto de confirmación. Antes de ella, los fallos siguen rechazados y no producen aceptación. Una limpieza fallida después no deshace lo verificado ni borra el recibo. Si el kernel informa un error de cierre, no se presume que el descriptor siga abierto: no se reintenta porque su número puede reutilizarse. Los tests de esa frontera liberan el descriptor y luego notifican error; prueban propiedad, orden e intentos de cierre, no garantías universales del kernel.

## Matriz ejecutada

| Familia nueva | Casos | Evidencia |
|---|---:|---|
| Mutaciones estructurales | 80 | Dos semillas × B8/D8 × primer/segundo bloque × diez mutaciones; código exacto, lecturas confinadas y ningún hash/entrada parcial del contenedor rechazado |
| Controles y fronteras | 11 | Cuatro cadenas originales válidas, cuatro límites de bloques/entradas, límite global del catálogo y dos fronteras exactas de carga JSON |
| Filesystem y limpieza | 47 | Ocho regresiones; 33 combinaciones operación × EACCES/ENOSPC/EIO; seis fallos de write/flush/fsync en payload/recibo |
| Interrupciones de proceso | 4 | SIGKILL tras reserva, durante payload, después de copiar y antes de publicar el recibo final |
| **Total nuevo** | **142** | Suite focalizada y completa aprobadas |

Las mutaciones usan semillas **1706** y **51434**, sectores de bytes propios y códigos esperados explícitos: tabla vacía/máxima, tamaño de bloque extremo, nombre dentro de tabla, offset máximo, suma offset+tamaño que excedería 32 bits, traversal, colisión de mayúsculas, solapamiento y nombre no ASCII. Los controles sin mutación prueban que las cadenas base son válidas. No se usa un oráculo que acepte cualquier excepción ni se denomina esto exploración exhaustiva del formato.

`build/f02-06/mutation-manifest.json`: 80 casos, 21.328 bytes, SHA-256 `ad0d3ce6b0153c000577d06f4f0cca3873d18c03dc8b115d59aede4d09bdbbfc`. Registra semilla, layout, bloque, mutación, código y hash del MFA sintético de 8192 bytes. No contiene bytes del juego. Los presupuestos se prueban con límites reducidos temporalmente y fixtures pequeños; no se escriben archivos gigantes.

La matriz de I/O inyecta fallos en creación de sesión/copias, apertura de directorios/payload/recibo/relectura, listado, publicación, escritura y sincronización. Los tests comprueban ausencia de aceptación, códigos, intentos de cierre y preservación de archivos anteriores. Los 104 casos de F02.05 siguen pasando, incluidos enlaces, archivos especiales, corrupción, sustitución de destinos y concordancia con el catálogo.

## Interrupciones y pipeline

`tests/python/helpers/extraction_worker.py` introduce puntos de parada solo en el proceso de prueba. El padre espera una señal por stdout, comprueba el estado alcanzado y aplica SIGKILL. Los cuatro estados quedan sin `verified.json`; tampoco se fabrica `failed.json` porque SIGKILL no ejecuta limpieza Python. Reutilizar la sesión devuelve `OUTPUT_EXISTS` y conserva sus bytes; una sesión nueva completa dos copias sintéticas iguales.

Los tests usan un máximo de 15 segundos para alcanzar el punto sincronizado, 5 para recolectar el proceso terminado y 15 por reintento CLI. Un bloque `finally` termina y recolecta hijos aun ante fallo del test. No hay esperas temporales usadas como prueba de haber alcanzado una etapa. Estos hooks no se importan desde producción ni añaden flags a la CLI real.

El job `quality` existente descubre las nuevas suites y aplica Ruff al helper bajo `tests/python`. No cambian workflows, dependencias, SDK ni runtime C++/ARM. La verificación ejecutada fue local en macOS 26.5 ARM64; GitHub Actions y hardware siguen pendientes. SIGKILL no equivale a pérdida física de energía y no acredita durabilidad del dispositivo.

## Cobertura, arquitectura y custodia

Cobertura Python: **1531/1563 líneas (97,95 %)** y **531/550 ramas (96,55 %)**. `private_output.py`, parser MFA y transferencia: 100 % en ambas. El gate independiente sigue exigiendo ≥80 % por métrica; no se disminuyeron umbrales. Ruff detectó separación de imports en un test nuevo; se corrigieron únicamente dos líneas en blanco y se repitieron check/format. El intento inicial se conserva en `initial-quality.log`. Los controles Ruff y de arquitectura/custodia/trazabilidad constan en `build/f02-06/verification.json` y `quality.log`.

La corrección se concentra en el adaptador que posee descriptores y la composición CLI que informa el resultado. Parser, política de rangos, identidad y copia de bytes no adquirieron dependencias de filesystem ni puntos de fallo. Se mantienen los puertos existentes. El resultado ordinario y el esquema de recibos siguen siendo v1; el aviso de limpieza es un campo opcional de stdout, documentado en H07 y [X08](../../schemas/extraction-v1.md).

Entorno: Python 3.14.6, pytest 9.1.1, pycdlib 1.22.0, Ruff 0.17.1, pytest-cov 7.1.0 y coverage 7.16.2. Se conservan comandos, logs, JUnit y cobertura JSON/XML bajo `build/f02-06`.

## Relación con la extracción real

No se repitió la extracción ni se escribieron nuevos originales. Se compararon hashes de nueve módulos de interpretación/identidad/transferencia contra el manifiesto de fuentes de F02.05: permanecen idénticos. También se verificó que los cuatro recibos privados de la ejecución real conservan tamaño/hash; detalle en `build/f02-06/historical-evidence-check.json`.

Las dos copias reales de 1740 recursos siguen siendo evidencia **de F02.05**. La comprobación de recibos no es una nueva relectura de todos los payloads ni atribuye la versión corregida a aquella ejecución. Los tests sintéticos de copia/repetición pasan con el adaptador corregido. Como no cambió la interpretación o transferencia de bytes, no fue necesario consumir espacio ni sobrescribir artefactos para repetir originales.

## Siguiente tarea

[F02.07](../specs/sh3-3ds/tasks/F02.md#f0207): seleccionar el conjunto mínimo de recursos para `slice-es-normal-v1`. El ticket detalla instancias de inventario de candidatos, identificación por formato, dependencias y selección de dos salas realmente conectadas. La primera instancia debe registrar candidatos y bloqueos con IDs/hashes, sin convertir nombres o extensiones en identificación semántica. XBG0/AFS y cualquier tipo aún sin evidencia permanecen pendientes; no se anuncia una habitación jugable por haber extraído bytes.

## Identidad de fuentes

`build/f02-06/source-manifest.json`: 69 archivos, SHA-256 `19f9035096136e77a316a092f4b62c68d586a777c1b7d4475986eb60e40b45a1`. Registra fuentes propias, pruebas, contratos y configuración; excluye este informe para evitar autorreferencia y no incluye recursos privados. Los cambios permanecen sin commit.
