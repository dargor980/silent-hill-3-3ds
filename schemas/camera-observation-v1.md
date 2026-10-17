# Plan y captura privada de observación PS2 v1

F02.07/camera-runtime-observation-plan-eu. Infraestructura de investigación;
no identifica un formato, no ejecuta el juego y no acredita hardware.

## Requisitos EARS

- **CO01:** WHEN genera un plan THEN SHALL fijar ambas copias de `camera-boundary-v1`,
  cadena anterior y catálogo por SHA-256, regenerar las fronteras desde ISO/ejecutable
  verificados y exigir igualdad completa. SHALL comprobar identidad de origen del
  catálogo, sin afirmar que se releyeron sus payloads.
- **CO02:** WHEN define puntos THEN SHALL conservar PC, fase, GPR bajos de 32 bits,
  ventana de código con hash y relación de argumento soportada. SHALL separar antes,
  entrada después del slot, retorno y checkpoints opcionales. El plan SHALL indicar
  `not_performed`, sin valores ficticios ni hash supuesto de recurso.
- **CO03:** WHEN recibe una captura THEN SHALL exigir sesión, entorno/versiones/hashes,
  CPU EE, hash del plan, ISO, ejecutable y catálogo; cada evento SHALL pertenecer a
  esa sesión/entorno. SHALL rechazar campos extra, tipos ambiguos y claves duplicadas.
- **CO04:** WHEN valida eventos THEN SHALL exigir secuencia contigua, puntos del plan,
  PC/fase coincidentes y exactamente los registros previstos. Cada frontera SHALL
  declarar `observed` con antes → entrada → checkpoints opcionales → retorno, o
  `not_reached` sin eventos. Una sesión `incomplete` SHALL rechazarse sin recibo válido.
  Entrada JAL SHALL tener GPR31 bajo igual al PC de retorno. No mezclar invocaciones.
- **CO05:** WHEN verifica código THEN SHALL leer snapshots privados y contrastar
  tamaño/hash con las ventanas fijadas en el plan. WHEN observa datos THEN SHALL
  limitar rango a <=4096 bytes, sin desbordamiento de 32 bits, con dirección igual
  al GPR declarado en ese evento y SHA-256 calculado sobre el archivo completo.
  No inferir identidad de recurso de una dirección o igualdad de registros.
- **CO06:** WHEN lee capturas THEN SHALL usar raíz privada externa al checkout,
  archivos regulares privados sin enlaces y lecturas acotadas, comprobando estabilidad
  hasta el cierre. SHALL limitar JSON a 1 MiB, 16 fronteras, 128 puntos/eventos,
  32 snapshots de código y 16 muestras de datos; cada blob <=4096 bytes.
- **CO07:** WHEN emite recibo THEN SHALL excluir valores GPR, bytes, direcciones de datos
  y textos del entorno; SHALL registrar solo hashes/conteos y resultados igual/diferente/
  no observado. La validez SHALL limitarse a integridad y coherencia de evidencia
  aportada; no autentica una ejecución ni preservación universal. Campos 92/108,
  colas, capacidades y F02.07/Q05/G02 SHALL seguir pendientes.
- **CO08:** WHEN publica plan/recibo THEN SHALL hacerlo exclusivamente tras cierre
  estable. IF identidad, orden, presupuesto o I/O falla THEN SHALL rechazar sin
  publicar éxito. SHALL probar fixtures propios, memoria/archivos, errores tardíos,
  manipulación de metadatos, dos planes reales idénticos y quality sin originales.

## Modelo y diseño

`observation_plan` regenera evidencia y crea puntos/rangos; `observation_capture`
valida el contrato mediante un puerto de lectura; `capture_files` posee descriptores,
custodia y cierre estable; `camera_observation` compone CLI y publicación.
Los inspectores históricos permanecen sin cambios.

El plan tiene `schema_version`, `tool`, `source`, `executable`, `evidence`,
`catalog_sha256`, `boundaries`, `code_ranges`, `status`, `capabilities` y
`f02_07_status`. IDs son hashes derivados de metadatos canónicos, no nombres originales.
Se conserva el catálogo fijado solo como referencia de identidad; no es evidencia
de que el puntero observado apunte a una de sus entradas.

La captura externa `capture.json` tiene exactamente:

- `schema_version: 1`, `kind: sh3-runtime-capture`, `session_id`: 32 hex minúsculas,
  `status: complete|incomplete`; hashes `plan_sha256`, `image_sha256`,
  `executable_sha256`, `catalog_sha256`.
- `environment`: `emulator`, `version` (texto 1..128), `binary_sha256`, `bios_sha256`,
  `configuration_sha256`, `cpu: EE`, `method: manual-debugger-v1`. Sus hashes son
  declaraciones de la sesión; el validador no inspecciona esos binarios. Cada evento
  repite el SHA-256 del JSON canónico de `environment`.
- `outcomes`: un objeto por ID de frontera, valor `observed|not_reached`.
- `events`: objetos con `sequence` (1..N), `session_id`, `environment_sha256`,
  `boundary_id`, `point_id`, `pc`, `registers` (claves decimales y 8 hex minúsculas
  por GPR). Los puntos definen fase y rango; no se admite intercalado de invocaciones.
- `code_snapshots`: lista exacta de `{range_id, size, sha256}` para rangos utilizados
  por eventos. El archivo se llama `<sha256>.bin` dentro de la raíz privada.
- `data_samples`: hasta 16 objetos `{event_sequence, register, address, size, sha256}`;
  archivo `<sha256>.bin`, sin nombres/rutas arbitrarios. Muestras opcionales,
  contenido no decodificado. Solo se verifica su consistencia con lo declarado.

Un `not_reached` es una declaración de esa sesión, no prueba ausencia. Una captura
completa sin eventos no se presenta como observación. El recibo omite datos privados
y mantiene `execution_authentication: not_provided`.

## Secuencia de tareas

1. Inventariar entorno local y consultar documentación primaria del depurador/BIOS.
2. Implementar generación reproducible de plan sobre evidencia regenerada.
3. Implementar contrato y lectura privada, con fixtures adversos y cierre estable.
4. Probar CLI, calidad/cobertura y repetir el plan sobre la ISO real.
5. Documentar protocolo y entorno. Capturar solo cuando estén disponibles los
   insumos/depurador; ausencia de ellos no impide completar y probar el validador.
