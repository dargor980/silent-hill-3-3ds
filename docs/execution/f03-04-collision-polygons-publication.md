# F03.04 / CF-T7e — Publicación privada y reconstrucción A/B

2026-10-23. **CF-T7e completada; CF-T7 cerrado para el perfil estructural
poligonal CPI.** Cumple CPI01/CPI05–CPI12 del
[contrato](../../schemas/collision-polygons-intermediate-v1.md), después del
[oráculo y los gates CF-T7d](f03-04-collision-polygons-intermediate-verification.md).
F03.04 global, G02/G03 y la respuesta física permanecen abiertos.

## Publicaciones privadas

Dos invocaciones independientes del CLI existente crearon:

- A: `/Users/germancontreras/sh3-private-data/f03-04-collision-polygons-intermediate-v1-a`
- B: `/Users/germancontreras/sh3-private-data/f03-04-collision-polygons-intermediate-v1-b`

Cada invocación leyó su extracción F02.05 correspondiente (`copy-a` o
`copy-b`), el mismo catálogo, recibo de extracción y auditoría CF-T6 fijados.
Son conversiones de dos copias conservadas de la misma edición europea;
no son nuevas adquisiciones de PCSX2 ni fuentes de ediciones diferentes.

Los destinos no existían y el espacio disponible superaba el presupuesto
de 128 MiB utilizado por la comprobación local. El writer creó directorios
0700 y archivos regulares 0600, con el propietario esperado. Tras verificar
y reconstruir el conjunto enlazó el manifiesto final. La relectura independiente
comprobó permisos, propietario, inventario, identidades y ausencia de symlinks.

| Contenido por paquete | Archivos | Bytes |
|---|---:|---:|
| Buffers originales completos | 285 | 2.690.720 |
| Vistas de recursos aceptados | 233 | 11.599.669 |
| `intermediate.json` | 1 | 376.527 |
| Total lógico | **519** | **14.666.916** |
| `manifest.json` | 1 | 109.947 |

El auxiliar `.manifest.pending.json` permanece como segundo enlace al mismo
inode del manifiesto final, con bytes iguales. Hay 521 nombres físicos por
directorio; el auxiliar no es un archivo lógico adicional.

Los **519 archivos lógicos y los manifiestos A/B coinciden byte por byte**.
También coinciden con el inventario obtenido en memoria en CF-T7c.
Huellas compartidas:

- Intermedio: `7a2b1097e13368461c32e7e118e0dcdf3efe1543fb5e44f4e819c82b8606f640`.
- Manifiesto: `81e3d4bef0120629d23a8268809fc33db973a0e385f306f26d2ceea60fb03bee`.

Se reproducen **233 aceptados, 52 no soportados y cero rechazados** por
copia. Los 52 no soportados conservan el buffer íntegro, vista nula y primer
código `CP_NONPOLYGON_UNSUPPORTED`; no se infiere que el resto de sus campos
haya sido validado. No se elimina ningún recurso ni se cambia el perfil CP.

## Reconstrucción y fidelidad

Se comprobaron primero las 29 huellas de código, ejemplos, CI y documentación
del comprobante CF-T7d, su evidencia previa y las configuraciones A/B. No
cambió producción, oráculos, fixtures, tests ni CI durante esta tarea.
El auditor operativo local no utiliza la selección/proyección de la receta
de producción para obtener los valores esperados.

Después de publicar, se ejecutaron **ocho procesos independientes**:
paquetes A/B × lector de producción/oráculo × Python normal/`-O`.
Cada proceso cargó exclusivamente su paquete; el lector de producción
comprobó también la API de lectura de directorio. A continuación se bloqueó
el acceso externo mediante `sys.addaudithook` y se reconstruyó en memoria.

En cada proceso cuatro controles rechazaron apertura de archivos, listado
de directorios, creación de procesos y sockets. Durante la reconstrucción
hubo **cero intentos de acceso externo**, y los 519 archivos reconstruidos
fueron idénticos a los cargados. El proceso del oráculo también bloqueó
importaciones de `tools` y comprobó el guard con un intento explícito.
Los ocho inventarios y hashes reconstruidos coinciden. No fue necesario
mover, renombrar ni borrar las extracciones para demostrarlo.

El guard comprueba el comportamiento del código Python fijado; no constituye
aislamiento del sistema operativo frente a código arbitrario. La reconstrucción
sin fuentes demuestra coherencia. La fidelidad se verificó después, separadamente:

- Unión por ID de las 285 filas completas del catálogo, recibo y auditoría.
- Comparación exacta de cada buffer contra su extracción A o B, incluidos
  padding, bytes opacos y recursos no soportados.
- Procedencia externa, identidad europea y tres pins contrastados con las
  entradas originales, sin derivarlos del paquete que se estaba comprobando.
- Vistas completas regeneradas por el oráculo independiente y cotejadas
  además con los hashes históricos CF-T6, usando su codificación JSON original.
- Clasificación y primer código exactos de todos los recursos por copia.
- Los 30 enlaces históricos proyectados directamente desde la auditoría:
  control 02, segmento continuo 08–35 y diagnóstico restaurado 36. Se conservan
  fases, CPU, punteros, tamaños/hashes de estado y recibo; las rutas no se copian.

Se releyeron y verificaron las **575 entradas de conversión**: 570 CLD,
tres documentos compartidos y dos configuraciones. Sus bytes e identidades
permanecen iguales a los registrados antes de publicar. El recibo de preflight
incluye además 23 archivos de código/evidencia fijados; el cotejo final
reverifica esos 598 archivos y el propio preflight, 599 en total.
Los enlaces son referencias del informe fijado: no se abrieron estados
históricos ni se volvió a comprobar la RAM en esta tarea.

## Incidencias y reproducción

La primera invocación A usó una ruta relativa en `--inputs`. La custodia la
rechazó con `ProfileError` antes de crear el destino. Se comprobó su ausencia
y se repitió con ruta absoluta; A y B terminaron con `status=prepared`.
No fue un rechazo del decoder ni un fallo de integridad del corpus.

Comandos ejecutados; los IDs ya publicados no deben reutilizarse:

```sh
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_polygon_intermediate --inputs /Users/germancontreras/silent-hill-3-3ds/build/cld-intermediate-contract/cf-t7c-inputs-a.json --private-root /Users/germancontreras/sh3-private-data --run-id f03-04-collision-polygons-intermediate-v1-a
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_polygon_intermediate --inputs /Users/germancontreras/silent-hill-3-3ds/build/cld-intermediate-contract/cf-t7c-inputs-b.json --private-root /Users/germancontreras/sh3-private-data --run-id f03-04-collision-polygons-intermediate-v1-b
```

El auditor local conservado permite repetir una reconstrucción de solo lectura:

```sh
rtk proxy .venv/bin/python -B -O -c "import runpy; runpy.run_path('build/cld-intermediate-contract/cf-t7e/audit_private_ab.py', run_name='__main__')" source-free --copy a --reader oracle
```

Cambiar `a` por `b`, `oracle` por `production` y omitir `-O` reproduce los
otros casos. El comando emite metadatos a stdout. Para repetir el cotejo
externo, elegir un archivo de salida nuevo; el auditor usa creación exclusiva:

```sh
rtk proxy .venv/bin/python -B -c "import runpy; runpy.run_path('build/cld-intermediate-contract/cf-t7e/audit_private_ab.py', run_name='__main__')" compare --baseline build/cld-intermediate-contract/cf-t7e/preflight.json --output /ruta/a/un-recibo-nuevo.json
```

## Comprobantes y cierre

Comprobante principal local:
`reports/local/f03-04-collision-polygons-publication-v1.json`.
Vincula el código fijado, auditor, entradas, publicaciones y resultados.
Bajo `build/cld-intermediate-contract/cf-t7e/` se conservan:

- `preflight.json`: pins e identidades previas, destinos y capacidad.
- `publication-execution.json`: invocación rechazada y dos publicaciones aprobadas.
- `rebuild-execution.json`, ocho `rebuild-*.stdout` y sus `.stderr`:
  comandos, resultados completos de reconstrucción e inventarios.
- `publication-ab.json`: comparación por recurso, vistas, códigos y custodia final.
- `manifest-a.json` y `manifest-b.json`: copias comprobadas de los manifiestos.
- `publication-validation.json`: reconciliación de artefactos, sin depender
  de la implementación del paquete.

Los auxiliares locales pasan Ruff/formato. Las comprobaciones del repositorio,
enlaces documentales y `git diff --check` pasan. Las 8.829 pruebas y los gates
de CF-T7d son evidencia previa reutilizada sobre código intacto; no se
repitió esa suite ni CI remoto. La evidencia nueva son las dos publicaciones,
ocho reconstrucciones y el cotejo externo íntegro. No hubo build ni prueba de consola.

CF-T7 se cierra con `state=structural_observation` y `capabilities=[]`.
La variante de 48 bytes, listas dinámicas, transformaciones aplicadas al
solver y respuesta física necesitan contratos y evidencias posteriores.
Cámara/audio, SH3P, daño/muerte, F03.04 global y G02/G03 siguen pendientes.
