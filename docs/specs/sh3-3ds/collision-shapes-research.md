# CF — Investigación de formas y listas de colisión

2026-10-23. Investigación posterior a IR-T7, sin cambiar su contrato de
registros ni habilitar capacidades físicas del runtime.
[CF-T1–T3 completadas y evidencias](../../execution/f03-04-collision-shapes-research.md).

## Requisitos EARS

Como implementador del port, necesito distinguir los registros, las listas
y las primitivas que consume el juego para diseñar un decoder acotado.

- **CF01:** CUANDO se atribuya un campo a una forma, el informe DEBERÁ
  vincularlo con instrucciones del productor o consumidor de la edición
  europea fijada y separar interpretación demostrada de hipótesis.
- **CF02:** CUANDO se recorra una lista, el auditor DEBERÁ comprobar su límite,
  paso y terminación, conservando alias y solapamientos observados sin
  deducir la longitud de la distancia al siguiente puntero.
- **CF03:** CUANDO se relacione un recurso con el escenario, el auditor
  DEBERÁ comprobar su identidad completa y su enlace desde las tablas usadas
  por el consumidor; un nombre o sufijo no bastará.
- **CF04:** CUANDO se contraste una transformación, el informe DEBERÁ indicar
  origen, destino, selección de banco, componentes comprobados, tolerancia y
  muestras; los valores deducidos de la salida no serán una referencia independiente.
- **CF05:** SI una variante, campo o enlace carece de evidencia, el informe
  DEBERÁ mantenerlo pendiente y no convertirlo en semántica física pública.
- **CF06:** MIENTRAS se investiguen las capturas conservadas, el auditor
  DEBERÁ verificar los pins de entrada, preservar los originales y emitir
  solo metadatos; distinguirá control, continuidad y diagnóstico restaurado.
- **CF07:** CUANDO se publique el resultado, el auditor DEBERÁ incluir
  controles negativos en copias de memoria y una reproducción de solo lectura.

## Diseño y verificación

La investigación separa tres responsabilidades: lectura y custodia de fuentes,
comprobaciones estructurales puras y reconciliación de evidencias. El auxiliar
local de investigación no es un decoder de producción ni forma parte de CI.
Usará estados fijados, ELF/overlay de la ISO privada y las extracciones A/B.
Solo las conclusiones y metadatos se documentarán en el repositorio.

Primero se sigue productor → registro → consumidor. Después se contrasta
recurso completo → tabla de recursos → sublista de índices → primitiva.
Las formas dinámicas y el recurso estático se estudian por separado. No se
presupone equivalencia con la malla visual, daño, activadores o solver.

Los futuros lectores de producción deberán tener contratos propios, errores
tipados, fixtures sintéticos y verificación independiente antes de integrarse
al formato intermedio. Este trabajo conserva IR-T7 y sus paquetes existentes.

## Tareas

- [x] **CF-T1 — Productor y consumidor de listas dinámicas.** Fijar ventanas de
  código; seguir los doce enlaces del overlay, tamaños, campos y terminadores;
  examinar los dos bancos y el control de la fase anterior. CF01/CF02/CF06.
- [x] **CF-T2 — Recurso estático y listas del escenario.** Identificar por
  bytes el recurso consultado, cotejar copias A/B, tablas y referencias;
  registrar variantes y enlaces todavía no observados. CF01/CF03/CF05/CF06.
- [x] **CF-T3 — Reconciliación y límites.** Contrastar capturas, transformaciones
  demostrables y solapamientos; ejecutar controles negativos, publicar el
  comprobante de metadatos y precisar el siguiente experimento. CF02/CF04/CF07.
- [x] **CF-T4 — Contrato del primer decoder de formas.**
  [CP01–CP15](../../../schemas/ps2-cld-polygons-v1.md): perfil poligonal
  indexado, límites, API, errores, conservación opaca, diseño de oráculo y
  gate de cobertura. Dos fixtures propios y 50 vectores materializados,
  comprobados por un auditor local independiente del constructor.
  [Ejecución y límites](../../execution/f03-04-collision-polygons-contract.md).
  RF02.04/RF02.05, CF01–CF07; sin decoder de producción, respuesta física ni G02/G03.
- [ ] **CF-T5a — Decoder poligonal puro.** Implementar la API CP y errores
  explícitos; probar estructura, coordenadas, terminadores e índices usando
  los vectores propios, sin importar I/O ni datos privados. CP01–CP09/CP12/CP13.
- [ ] **CF-T5b — Batería y oráculo público.** Añadir fronteras, barridos,
  alias, aislamiento, precedencia, sensibilidad y `-O`; oráculo stdlib
  independiente del decoder y del constructor. CP10–CP14.
- [ ] **CF-T5c — Integración de calidad.** Añadir oráculo a Ruff/formato y
  módulo al gate individual ≥80 % líneas/ramas, conservar gates actuales y
  ejecutar regresión pertinente. No depender de fuentes privadas en CI.
- [ ] **CF-T6 — Cotejo privado del decoder.** Aplicar a copias A/B fijadas,
  conservar aceptados/no soportados/errores y comparar los dos recursos
  enlazados al escenario sin relajar reglas para aceptar todo. CP15.
- [ ] **CF-T7 — Extensión intermedia de formas.** Definir primero contrato
  separado, buffer completo/vista, procedencia y reconstrucción; después
  implementar y comparar publicaciones A/B. No modificar el perfil IR-T7.
