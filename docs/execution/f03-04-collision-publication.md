# F03.04 / IR-T7f — Publicación privada A/B y reconstrucción

2026-10-23. **IR-T7f completada; IR-T7 cerrado para registros observados.**
Cumple la publicación y comparación privada de IR19/IR22/IR23/IR26 del
[contrato](../../schemas/collision-intermediate-v1.md). F03.04 global,
G02/G03 y las formas/respuesta física de colisión permanecen pendientes.

## Entregas

Se publicaron con el CLI existente, en dos invocaciones independientes y
sin reutilizar directorios:

- A: `/Users/germancontreras/sh3-private-data/f03-04-collision-intermediate-v1-a`
- B: `/Users/germancontreras/sh3-private-data/f03-04-collision-intermediate-v1-b`

Ambas conversiones leen las **mismas 30 capturas históricas** fijadas por el
inventario IR-T7a; son repeticiones de conversión, no adquisiciones diferentes
de PCSX2. Conservan control 02, segmento continuo 08–35 y diagnóstico
restaurado 36 con sus etiquetas y recibos completos.

Cada entrega contiene **242 archivos de contenido** y `manifest.json`.
El writer conserva además `.manifest.pending.json`, comprobado como enlace
al mismo inode y con los mismos bytes del manifiesto final. Los dos directorios
usan permisos 0700; los archivos regulares, 0600 y el propietario esperado.
Se rechazaron symlinks al releer y se comprobó el inventario exacto.

| Contenido por entrega | Archivos | Bytes |
|---|---:|---:|
| Ocho rangos × 30 capturas | 240 | 1.571.670 |
| `intermediate.json` | 1 | 325.863 |
| `collision-observations.json` | 1 | 104.283 |
| Total de contenido | 242 | 2.001.816 |
| Manifiesto final | 1 | 62.242 |

Los **242 archivos y los manifiestos A/B son iguales byte por byte**.
No se compararon solo resúmenes o hashes. Huellas principales compartidas:

- Intermedio: `333685a96773eec513ebcd7960cba2688dfb61b9663ac87544b45a8665766cf7`.
- Vista: `6ab28c1247c12d9fc23f2a4645b4e6e898cd912a1a31103391ea94f1ed135a2d`.
- Manifiesto: `c4bc795d3c7cccb203304d1375d78b715d4d2f48da37a3edc9a3de1d627e4f18`.

El intermedio mantiene el hash obtenido en memoria en IR-T7d/e.

## Verificación contra las fuentes

Antes de publicar se verificaron los hashes del código operativo y del oráculo
contra el comprobante IR-T7e, y los pins de configuración, inventario e informes.
Los destinos no existían; había margen suficiente para las dos entregas.
La configuración local ignorada sigue en
`build/collision-intermediate/inputs-v1.json` (13.566 bytes); no se copiaron sus
rutas del host al intermedio.

Después de publicar se releyeron archivos y manifiestos desde disco. Para cada
entrega se ejecutó el [oráculo independiente](../../tests/collision_wire_oracle.py)
contra sus fuentes fijadas: los 240 bloques completos, los 30 recibos, los tres
informes, inventario y CPU del estado. Después se comprobaron nuevamente los
**64 inputs** por tamaño/SHA-256: 30 estados, 30 recibos, tres informes y un
inventario. Las fuentes permanecen iguales a los pins y no fueron modificadas.

## Reconstrucción sin consultar fuentes

Se ejecutaron **dos procesos separados con Python `-O`**, uno por paquete.
Cada proceso recibió solo la ruta de su paquete y el hash fijado del manifiesto.
Tras cargar y verificar ese paquete, se instaló un `sys.addaudithook` que
rechaza aperturas de archivos, listados de directorios, creación de procesos,
sockets y carga dinámica mediante ctypes durante el cálculo.

Cuatro controles comprobaron el bloqueo de `open`, `listdir`, `Popen` y socket
antes de la reconstrucción. Luego se reinició el contador de accesos:

| Resultado | A | B |
|---|---:|---:|
| Controles rechazados por el guard | 4 | 4 |
| Intentos de acceso externo durante reconstrucción | 0 | 0 |
| Archivos reconstruidos idénticos a los cargados | 242 | 242 |
| Comprobación independiente de vista, bloques y manifiesto | Aprobada | Aprobada |

Se reconstruyó en memoria mediante `export_collision`, se comparó cada byte
con el paquete cargado y se aplicó de nuevo el oráculo independiente. Los
hashes de los 242 resultados reconstruidos coinciden con ambos manifiestos.
No se movieron ni borraron estados originales para efectuar esta prueba.
El guard es una comprobación de acceso de Python sobre el código fijado,
no una afirmación de aislamiento del sistema operativo ante código arbitrario.
El modo sin fuentes acredita reconstrucción/coherencia; la correspondencia
con los originales la establece el cotejo anterior.

## Comprobantes y reproducción local

Todos los comprobantes siguientes contienen metadatos, no buffers originales:

| Archivo bajo `build/collision-intermediate/` | SHA-256 |
|---|---|
| `publication-validation-v1.json` | `d953654f110c7362cb8e4129fa8c5a9046b3a9b4567a087501efdce5219192e1` |
| `publication-ab-v1.json` | `b8eeaa0a8f15d03f428665ef07e8098c079f03f4708fa264ffd927a0d5a2f88e` |
| `publication-rebuild-a-v1.json` | `8d2c30373efadcfb85e4d7f354cb103e94d129fcde6ee110f187c989a099dd5e` |
| `publication-rebuild-b-v1.json` | `867ce77d6e0991adfc2488d43fc4e755d9d63caac86431491cd280837af8e37d` |

El comprobante principal vincula código, contrato, auditor y resultados.
El auditor operativo local `build/collision-intermediate/audit_private_ab.py`
tiene SHA-256 `800167f6d57507c41585b695650f1d029491e97f81c2b628739fafd1936efc8d`.
No es una dependencia del preparador ni se incorpora a CI.

Publicaciones ejecutadas (no volver a usar los IDs ya publicados):

```sh
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_intermediate --inputs build/collision-intermediate/inputs-v1.json --private-root /Users/germancontreras/sh3-private-data --run-id f03-04-collision-intermediate-v1-a
rtk proxy .venv/bin/python -m tools.pipeline.prepare_collision_intermediate --inputs build/collision-intermediate/inputs-v1.json --private-root /Users/germancontreras/sh3-private-data --run-id f03-04-collision-intermediate-v1-b
```

Auditoría de lectura; para repetir la comparación elegir un comprobante de
salida nuevo, porque el auditor también lo crea de forma exclusiva:

```sh
rtk proxy .venv/bin/python -c "import runpy; runpy.run_path('build/collision-intermediate/audit_private_ab.py', run_name='__main__')" compare --inputs build/collision-intermediate/inputs-v1.json --root /Users/germancontreras/sh3-private-data --output build/collision-intermediate/publication-ab-v1.json
rtk proxy .venv/bin/python -O -c "import runpy; runpy.run_path('build/collision-intermediate/audit_private_ab.py', run_name='__main__')" source-free --package /Users/germancontreras/sh3-private-data/f03-04-collision-intermediate-v1-a --manifest-sha256 c4bc795d3c7cccb203304d1375d78b715d4d2f48da37a3edc9a3de1d627e4f18
```

El mismo comando de reconstrucción se ejecutó con el paquete B. Los JSON de
reconstrucción se capturaron desde stdout a sus archivos de evidencia nuevos.

## Validación y alcance del cierre

No cambió el código de producción ni el oráculo fijados en IR-T7e. Sus
**257 pruebas del perfil** y cobertura 99,71 % de líneas / 98,94 % de ramas
son evidencia previa reutilizada, no una nueva ejecución de esa suite en
IR-T7f. Esta tarea aporta dos publicaciones reales, relectura, comparación
independiente con origen, igualdad A/B y dos reconstrucciones aisladas del
acceso externo. El auditor local pasa Ruff; las comprobaciones de repositorio
y `git diff --check` pasan tras actualizar la documentación.

El estado continúa siendo `observed_registry`, con `capabilities=[]`.
No se reconstruye un savestate completo, no se incluyen las listas apuntadas
como formas físicas y no se acredita respuesta de colisión ni daño/muerte.
No hubo ejecución de PCSX2 o consola ni un nuevo build para la SD.

La investigación posterior descrita en el contrato debe identificar el
formato de las formas de colisión y su vínculo con las listas de escenario,
antes de un decoder de superficies o un solver. Cámara/audio también siguen
pendientes; cerrar este perfil no cierra F03.04 global ni G02/G03.
