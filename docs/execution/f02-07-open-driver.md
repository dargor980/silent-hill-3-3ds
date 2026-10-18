# F02.07 — Apertura y objeto del driver

Fecha: 2026-10-18. Unidad SRC60 de `camera-resource-link-eu/origin/load-provenance/LP-C`.
Continúa [SRC59](f02-07-driver-transfer.md). Contrato [OD01–OD09](../../schemas/open-driver-v1.md)
y [evidencia](../compatibility/open-driver-evidence.json).

## Resultado

Se implementó [open_driver](../../tools/inspectors/open_driver.py), un adaptador
puro que relaciona el retorno de apertura con el objeto y la pareja de lectura
de SRC59. Comprueba ruta, rango, descriptor reservado, handle, contador, estado
inicial, mapas y campos invariantes. Usa tres pausas de ocho rangos: **24
solicitudes regionales**, sin contar descubrimiento auxiliar.

**La continuidad no está demostrada.** El modo predeterminado rechaza con
`OPEN_DRIVER_LIFETIME_UNPROVEN`. Solo `require_continuity=False` permite obtener
un diagnóstico de consistencia; produce cero `Read`, vínculos y capacidades.
El diagnóstico no certifica la ejecución de los perfiles suministrados.

Se reutilizan las entradas y el ABI de SRC58, pero no se compone su reconciliación
completa de selección de catálogo. Concatenar sus cinco rangos con los cuatro
del objeto excedería el límite. La pausa nueva conserva ruta/rango/descriptor,
sin configuración ni selección del catálogo. La composición completa requiere
un perfil conjunto; no se trata un recibo JSON previo como prueba.

No hubo nueva sesión ni captura en PCSX2, compilación C++/3DS, CI remota o prueba
en consola. LP-C sigue parcial y LP-D pendiente.

## Investigación y diseño

Cuatro ventanas de **1.712 bytes** coinciden entre ELF y estado: envoltorio de
apertura, apertura del driver, asignación y liberación. Dieciocho instrucciones
fijan el retorno y la inicialización. Se revalidan además las 14 ventanas de
SRC59 y las identidades de ISO, ELF, catálogo, contenedor y payload.

El punto elegido precede al delay slot que copia el handle: r2 contiene el
resultado mientras el registro conservado aún contiene el modo. En el objeto
se inicializan posición a cero, caché inválida y bandera asíncrona según los
argumentos. Los valores concretos y el código original permanecen privados.

Los informes repetidos son idénticos: **2.265 bytes**, SHA-256
`c379aaf05597986a8df64b24651b5f333d51d0d2d06eebe16ee080d0c50763a7`.
El plan se crea sin sobrescritura, directorio 0700/archivo 0600. Las fuentes
anteriores quedan intactas y los lectores cierran antes de publicar. El estado
posterior a la carga no se usa como inicio válido ni como objeto activo.

La interpretación del objeto permanece en `driver_object`; la pareja de lectura
se delega a `driver_transfer`; el módulo nuevo concentra apertura y comparación.
No introduce I/O, dependencias ni cambios en los módulos históricos o el runtime.
Comprueba mapas incluso cuando una página aparece con etiquetas distintas.

Un cambio visible de generación, cierre, backend o buffer se rechaza. Extremos
iguales no excluyen restauración, reinicialización o ABA entre muestras. Por
eso no existe un modo de éxito de continuidad en esta versión; tampoco se
acepta una declaración suministrada como certificado de historia completa.

## Validación

**63 pruebas propias** cubren entradas, ABI, rutas de igual tamaño, cierre,
reciclado, contador, estado inicial, caché previa, payload preexistente, identidad,
mapas compartidos, secuencia regional 256 y presupuesto global de ciclos.

Los ensayos iniciales conservaron un error de sintaxis del test y después dos
errores de fixture/oráculo: ciclo negativo no representable y rechazo de mapa
detectado antes por `PAUSE_PAGE`. Se corrigieron los tests sin relajar producción;
se añadieron casos de presupuesto total y página compartida entre etiquetas.
Resultado específico final: **63/63**. Regresión: **2.794 aprobadas**, sin fallos,
errores ni omisiones; 65,905 segundos según JUnit.

| Cobertura | Líneas | Ramas |
|---|---:|---:|
| open_driver | 56/56 (100 %) | 10/10 (100 %) |
| Todas las herramientas | 4.960/5.005 (99,10 %) | 1.379/1.412 (97,66 %) |

Gate 80/80 y Ruff/formato aprobados en 129 archivos Python. El job existente
descubre los tests propios sin originales; no requiere cambios de pipeline.
Los controles finales de repositorio, enlaces, hashes y custodia constan en
SRC60. Los informes operativos se publicaron antes de la regresión.

## Tareas

- [x] **OD-T1 / OD01–03:** contrato, ABI, ruta/rango y objeto inicial; pruebas de
  retorno erróneo, cierre y estado incompatible.
- [x] **OD-T2 / OD04–07:** composición con DT, comparación y rechazo predeterminado
  de continuidad; diagnóstico explícito con cero eventos de lectura.
- [x] **OD-T3 / OD08:** perfil privado, fuentes revalidadas y dos análisis iguales.
- [x] **OD-T4 / OD09:** pruebas, regresión, cobertura y trazabilidad.

## Siguiente trabajo ejecutable

1. **Backend y sector:** seguir la referencia desde apertura hasta descriptor
   backend, archivo y sector. Fijar ventanas privadas y modelar las unidades de
   posición/tamaño. Aceptación: rechazar archivo ajeno del mismo tamaño y sector
   antiguo; un puntero o hash coincidente no basta para atribuir origen.
2. **Copia y finalización:** observar argumentos y retorno de la copia desde
   caché, o finalización/cantidad del backend. Probar error, retorno corto y
   caché no llenada por el archivo esperado; conservar cero `Read` sin la cadena.
3. **Perfil conjunto de catálogo y continuidad:** unir selección, apertura y
   objeto sin superar ocho rangos por pausa; definir observación de cierre,
   reasignación/reinicialización y restauraciones. Contar también descubrimiento
   bajo guardia. Aceptación: evidencia completa o rechazo explícito.
4. **LP-D:** solo con el perfil completo, iniciar antes de la carga con español,
   acción Normal y acertijos Normal. Presupuesto: ≤48 estados, ≤256 solicitudes
   regionales/hits, 60 segundos activos, 3.600 de pared, 8 GiB de etapa y 10 GiB
   libres mínimos. Conservar rechazos y obtener dos reimportaciones iguales.

Procedencia real, semántica de cámara, F02.07/Q05/G02, dos salas conectadas y
pruebas físicas en New Nintendo 2DS XL siguen pendientes.
