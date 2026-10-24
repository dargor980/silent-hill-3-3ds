# F03.04 / CF-T7c — Preparador privado y publicación exclusiva

2026-10-23. **CF-T7c completada**, con trazabilidad a CPI01/CPI07/CPI08/CPI10
del [contrato CPI01–CPI14](../../schemas/collision-polygons-intermediate-v1.md).
Se integra el [adaptador puro CF-T7b](f03-04-collision-polygons-intermediate.md)
sin cambiar decoder CP, ejemplos del contrato ni paquetes IR-T7.

## Implementación y responsabilidad

- [`collision_polygon_recipe`](../../tools/pipeline/collision_polygon_recipe.py)
  fija tamaño/hash de catálogo F02.04, recibo F02.05 y auditoría CF-T6. Une
  por ID sus 285 recursos, verifica metadatos y ambas tablas de copias del
  recibo, conserva filas completas del catálogo y proyecta los 30 enlaces.
  La configuración solo elige ubicaciones; no hay opción CLI para sustituir
  la receta por otra auditoría. La comparación de vistas históricas respeta
  el JSON con sangría usado por CF-T6; los archivos lógicos siguen siendo
  JSON compacto canónico CPI.
- [`collision_polygon_inputs`](../../tools/pipeline/collision_polygon_inputs.py)
  mantiene la custodia: abre padres mediante descriptores sin seguir symlinks,
  exige archivos regulares y limita tamaño antes de leer. Comprueba identidad
  del descriptor, nombre y directorio padre, además de tamaño/hash. Al releer
  detecta también sustituciones con bytes iguales. No retiene todas las
  fuentes en el registro de custodia, solo sus pins e identidades.
- [`prepare_collision_polygon_intermediate`](../../tools/pipeline/prepare_collision_polygon_intermediate.py)
  valida la configuración ≤32 KiB, lee todos los CLD fijados antes de invocar
  el decoder, construye el intermedio, coteja clasificación/código y hash de
  vista con CF-T6 y relee las entradas. `prepare_files` devuelve bytes y
  metadatos en memoria. `prepare_and_write` conserva la custodia durante
  escritura y la verifica otra vez antes de publicar, incluida la configuración.
- [`collision_polygon_output`](../../tools/pipeline/collision_polygon_output.py)
  valida/reconstruye antes de crear el destino. Impone 40 MiB lógicos y
  manifiesto ≤256 KiB. Reutiliza el writer exclusivo compartido, con un
  callback opcional anterior al enlace de `manifest.json`; el valor por
  defecto conserva el comportamiento de los perfiles previos.

El directorio de ejecución se crea fuera del repositorio, con modo `0700`;
archivos `0600`, creación exclusiva y sin seguir symlinks. Cada escritura
se sincroniza y relee. Antes de enlazar el manifiesto final se vuelve a
leer el conjunto completo, se reconstruyen todos los archivos desde esos
bytes, se cotejan inventario/identidades y se confirma que la ruta siga
señalando al directorio creado. Un fallo conserva el parcial sin entrega
final; no sobrescribe ni reanuda una ejecución existente.

`read_collision_polygon_bundle(path)` abre un paquete completado y devuelve
manifiesto más archivos lógicos verificados. Solo admite el auxiliar
`.manifest.pending.json` si es regular y tiene exactamente los bytes del
manifiesto final. Un auxiliar solo no constituye una publicación. No abre
catálogo, extracciones, estados, recibos históricos ni direcciones EE.

La etapa histórica `0x23` procede de la receta CF-T6. El resto de campos,
incluidos PC/ciclo, punteros y pins de estado/recibo, se conserva del informe
fijado sin copiar sus rutas. Esto no vuelve a verificar la RAM.

## Pruebas propias y regresión

**104 pruebas de integración aprobadas**, con fuentes construidas por
[`collision_polygon_recipe_fixtures`](../../tests/collision_polygon_recipe_fixtures.py)
y el oráculo CP independiente. El corpus de prueba contiene 285 recursos:
2 aceptados, 282 no soportados y 1 truncado rechazado; reproduce las tres
rutas sin incluir datos del juego. Las identidades europeas de sus metadatos
son sintéticas. Los pins de receta se sustituyen solo dentro de las pruebas,
nunca mediante una opción de la CLI de producción.

Se verifica:

- A/B sintéticos iguales; filas y extensiones conservadas, recursos íntegros
  de las tres clases, 30 enlaces proyectados sin rutas y nombres derivados.
- Rechazo previo al decoder ante pins, fuentes o vínculos de catálogo/recibo
  alterados; duplicados, traversal, discrepancias de copias/oráculo y cambios
  de clasificación, código, vista o conteos.
- Archivos vacíos, excedidos, ausentes, FIFO, directorios, symlinks de archivo
  y padres; sustitución del archivo/padre durante lectura o después de preparar.
- Errores inyectados de apertura, escritura parcial, espacio, sincronización,
  relectura, manifiesto provisional y enlace final. Archivos extra, cambios
  tardíos, sustitución del destino y creación concurrente no producen una
  nueva entrega declarada completa.
- Dos escritores con igual `run-id`: exactamente uno publica y el otro
  recibe `FileExistsError`; las ejecuciones existentes permanecen intactas.
- Lector con inventario/manifiesto modificado, auxiliar distinto o symlink,
  límites físicos y cambios durante reconstrucción. El presupuesto restante se
  vuelve a aplicar antes de leer cada archivo, incluso si crece tras inventariarlo.
  Presupuestos del writer
  comprobados antes de crear el directorio.
- Configuración o fuente alterada durante escritura: falla la custodia final.
  CLI sin rutas/payloads en sus errores. Subprocesos normal y `-O` preparan y
  publican sintéticos, retiran las fuentes y reconstruyen el mismo paquete;
  también comprueban rechazo de entradas ausentes sin crear destino.

Cobertura local de los cuatro módulos nuevos, con gate individual ≥80 %:

| Módulo | Líneas | Ramas |
|---|---:|---:|
| Custodia de entradas | 53/53 | 8/8 |
| Receta y vínculos | 101/101 | 16/16 |
| Writer/lector de directorio | 64/64 | 8/8 |
| Preparador y CLI | 53/54 | 7/8 |

La línea de arranque `__main__` se ejecuta en los subprocesos pero no se
agrega a la medición del proceso principal. No se excluye del cálculo.
**3.896 pruebas de regresión aprobadas**: CP, adaptador CPI, registros IR-T7
y los consumidores del writer compartido de textura, geometría, mapa y material.
No se repitió la suite global ni CI remoto. El gate permanente y el oráculo
independiente del paquete completo corresponden a CF-T7d.
Ruff, formato, reglas de custodia/arquitectura/EARS, enlaces documentales y
`git diff --check` pasan. No se modifican los workflows en esta tarea.

## Preparación privada sin publicación

Se ejecutó `prepare_files` una vez por copia privada fijada A/B. Cada ejecución
verificó los tres documentos y los 285 CLD, los reconstruyó en memoria,
cotejó clasificación/código y hash de vista histórico y releyó las 288 entradas.
Las dos preparaciones reproducen:

| Medida | Copia A | Copia B |
|---|---:|---:|
| Recursos aceptados / no soportados / rechazados | 233 / 52 / 0 | 233 / 52 / 0 |
| Archivos lógicos | 519 | 519 |
| Bytes lógicos | 14.666.916 | 14.666.916 |
| Bytes de manifiesto previsto | 109.947 | 109.947 |

Todos los tamaños y hashes de archivos lógicos coinciden. El SHA-256 del
manifiesto previsto en ambas es
`81e3d4bef0120629d23a8268809fc33db973a0e385f306f26d2ceea60fb03bee`.
Solo se guardaron configuraciones y metadatos del cotejo en `build/`,
ignorado por Git; no se escribieron paquetes ni payloads privados nuevos.
La comparación de publicaciones físicas y reconstrucción independiente A/B
queda pendiente de CF-T7e.

Artefactos locales:

- `build/cld-intermediate-contract/cf-t7c-inputs-a.json` y `cf-t7c-inputs-b.json`:
  configuración con ubicaciones/pins para cada copia.
- `build/cld-intermediate-contract/cf-t7c-private-dry-run.json`: inventario de
  tamaños/hashes y resumen de las preparaciones, sin buffers ni vistas.
- `build/cld-intermediate-contract/cf-t7c-coverage.json`, `cf-t7c-pytest.xml`
  y `cf-t7c-regression.xml`: medición y resultados locales.
- `reports/local/f03-04-collision-polygons-preparation-v1.json`: comprobante
  con pins de implementación, pruebas, documentación y evidencia anterior.

## Reproducción y continuación

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_collision_polygon_preparation.py -q
```

La CLI implementada para la futura publicación de una copia es:

```sh
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_polygon_intermediate \
  --inputs /ruta/privada/inputs-a.json \
  --private-root /ruta/privada/directorio-existente \
  --run-id nombre-nuevo
```

Los archivos de entrada deben coincidir con los tres pins de receta; el
directorio padre de salida ya debe existir. La CLI rechaza destinos del
repositorio y ejecuciones existentes. `status=prepared` significa que el
manifiesto final fue enlazado tras los controles, no que exista respuesta física.

**Siguiente: CF-T7d**, oráculo independiente de paquete, batería ampliada y
gates permanentes por módulo en CI. Después, CF-T7e publica y reconstruye A/B.
Esta tarea no añade solver, formas de 48 bytes, listas dinámicas, daño/muerte,
SH3P, un build de 2DS XL ni nueva ejecución de PCSX2. F03.04 y G02/G03 siguen abiertos.
