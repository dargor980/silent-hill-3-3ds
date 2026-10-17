# Comparación de un recurso completo entre estados EE

F02.07/camera-resource-link-eu/origin · OR01–OR08.

## Requisitos EARS

- **OR01:** CUANDO se compare un candidato, el coordinador DEBERÁ fijar por SHA-256
  ambos informes RL, todas sus entradas y un plan de comparación; DEBERÁ reproducir
  RL y exigir igualdad antes de aceptar el candidato. El plan DEBERÁ identificar
  sesión, captura, recurso, evento base, registro y eventos destino explícitos.
- **OR02:** CUANDO se derive la base, el lector DEBERÁ importar PC y todos los GPR
  registrados del estado fuente y exigir igualdad con su evento de entrada. La base
  DEBERÁ conservarse para los demás estados aunque el registro destino cambie.
- **OR03:** SI un destino pertenece a otra sesión/entorno, precede al evento fuente,
  no coincide con su estado o presenta delay slot, el lector DEBERÁ rechazar.
  La pertenencia es declarada por la captura validada; no autentica la ejecución.
- **OR04:** CUANDO lea RAM, el lector DEBERÁ aceptar solo 32 MiB con CRC ZIP completo,
  rangos de 1–4096 bytes y base física hipotética baja sin alias ni cruce del límite.
  El coordinador DEBERÁ comparar el recurso entero, máximo 16 estados, y exigir un
  hit RL de 256 bytes del evento fuente en offset cero del recurso elegido.
- **OR05:** CUANDO compare, DEBERÁ informar hashes, igualdad, número de bytes distintos
  y rangos contiguos `[inicio, fin)` relativos al recurso, sin bytes ni direcciones.
  DEBERÁ comparar cada estado contra el recurso y contra el estado anterior; igualdad
  entre extremos no DEBERÁ interpretarse como ausencia de escrituras intermedias.
- **OR06:** CUANDO use extracciones, DEBERÁ comprobar tamaño/hash completo y estabilidad
  del candidato en ambas copias, exigir igualdad y releer los estados antes del cierre.
  SI falla una lectura/cierre, DEBERÁ impedir publicación. No sobrescribir informes.
- **OR07:** MIENTRAS no haya evidencia de traducción efectiva y de carga/escritor,
  el informe DEBERÁ conservar `mapping_verified: false`, `origin_status: pending`,
  `resource_links: []` y `capabilities: []`, incluso con igualdad completa.
- **OR08:** CUANDO localice una divergencia, el plan posterior DEBERÁ acotar el intervalo
  entre observaciones y los offsets candidatos; una nueva ejecución DEBERÁ tener
  sesión propia. Una escritura solo será evidencia si se demuestra solapamiento con
  el rango, traducción y cambio antes/después; no asignar semántica a campos 92/108.

## Diseño

`origin_memory` deriva una base inmutable de CPU validada y extrae rangos del destino.
`origin_compare` compara bytes propios/privados en memoria y devuelve solo metadatos.
`resource_origin` coordina RL, plan, capturas, lectores privados y publicación. Un
adaptador del lector existente verifica el candidato y conserva su identidad hasta
el cierre. RL v1 y sus límites de 64/256 bytes no cambian.

El plan JSON v1 contiene exactamente `schema_version`, `session_id`,
`capture_sha256`, `link_sha256`, `resource_id`, `source_event_sequence`,
`base_register`, `target_event_sequences`. Los destinos son crecientes, únicos,
incluyen primero la fuente y al menos un destino posterior. El tamaño proviene del
catálogo, nunca de una longitud arbitraria indicada por el usuario. Solo se aceptan
recursos completos de 256–4096 bytes con hit fuente de 256 bytes en offset cero.

El lector conserva un ZIP ≤64 MiB y RAM ≤32 MiB por vez; los 16 rangos suman ≤64 KiB.
Cada comparación puede emitir hasta 2048 intervalos, sin truncarlos. No se exporta
RAM ni se carga un estado en PCSX2 en esta etapa de comparación.

## Tareas y aceptación

1. Contrato OR, ancla de base y comparación pura; fixtures de límites, cambio del
   registro de retorno, sesión/entorno/orden, fragmentación y tamaños incompatibles.
2. CLI con plan fijado, reproducción RL, dos copias, rechazo de candidato no demostrado,
   fallos tardíos y dos informes sintéticos idénticos; integrar suite/quality existentes.
3. Comparar entrada/retorno A y B1/B2 reales; conservar informes repetidos e identidad
   de insumos. Registrar primera divergencia observada sin inferir el escritor.
4. Investigar evidencia de mapeo disponible y preparar observación de traducción y
   escritor/cargador. Mantener origen pendiente hasta cadena reproducible completa.

## Estado de ejecución

Pasos 1–3 completados: 66 casos nuevos, 1.649 pruebas aprobadas y dos informes
idénticos sobre ocho estados reales. El paso 4 tiene investigación de fuentes y
plan de observación `not_performed`; traducción efectiva, escritor y cargador
pendientes. [Resultado y siguiente ejecución](../docs/execution/f02-07-camera-origin.md).
