# HRM01–HRM07 — Inventario candidato de materiales hp34

HM-T4c.3.1, 2026-10-30. Primera parte de HM-T4c.3; HR09–10/12.
Este inventario prepara la investigación de las 29 formas diagnósticas.
No constituye una asociación original aceptada ni cambia el build de consola.

## Requisitos EARS

- **HRM01** WHEN se analiza el MAP THEN el inspector SHALL validar la
  estructura y las raíces delimitadas por contador antes de asociar grupos.
  SHALL exigir un grupo externo en slot 1 y todos los grupos internos en slot 2.
- **HRM02** WHEN se propone la correspondencia THEN el inspector SHALL
  identificarla como hipótesis explícita: grupo externo `(word16,word20)=(2,0)`
  a bloque externo 0; grupos internos `(3,n)` a bloque interno `n-1`.
  SHALL exigir índices completos, únicos y contiguos y no inferirlos del nombre
  o del campo `texture_id`. La hipótesis SHALL permanecer sin verificar en runtime.
- **HRM03** WHEN una malla selecciona CLUT THEN el inspector SHALL interpretar
  el campo como selector candidato CSM1, conservando los restantes halfwords
  sin atribuirles mezcla/alpha. Para cuatro unidades SHALL admitir `0,1,4,5`,
  no los ordinales `0,1,2,3`; para ocho/dieciséis, `0..7`/`0..15`.
- **HRM04** WHEN decodifica los bloques THEN el inspector SHALL conservar alpha
  PS2 sin normalizar, calcular hashes de índices/paletas/RGBA y estadísticas,
  y no devolver píxeles, vértices ni bytes fuente en el informe.
- **HRM05** WHEN calcula memoria THEN el inspector SHALL separar variantes
  declaradas, combinaciones candidatas y RGBA únicos por dimensiones/contenido
  exacto. SHALL contar cada combinación una vez aunque varias formas la usen.
  Las cifras SHALL ser estimaciones para la futura carga, no RAM física medida.
- **HRM06** IF estructura, ubicación de la sección, formato de transferencia,
  selector o alcance de las raíces no pertenece al subperfil THEN el inspector
  SHALL rechazar el conjunto sin devolver aceptación parcial.
- **HRM07** WHEN se auditan fuentes privadas THEN el auditor SHALL verificar
  catálogo/recibo y hashes A/B, cotejar índices y paletas con el modelo GS
  independiente y publicar solo metadatos después de releer las fuentes.
  La ejecución normal y `-O` SHALL producir el mismo informe.

## Diseño y límites

`tools.inspectors.map_material_candidates.inspect_candidates` recibe los dos
recursos en memoria y un offset explícito de sección interna. Reutiliza los
lectores MAP/TEX y `ps2_indexed`, sin filesystem ni SDK. El informe mantiene
`material_binding=unverified`, `runtime_comparison=pending`, `capabilities=[]`.
La sección debe comenzar después de todos los grupos y terminar con el MAP.
El subperfil admite PSMT8, ocho grupos como máximo y dieciséis paletas por bloque.
El trabajo de expansión se limita a 64 MiB para todas las variantes y 32 MiB
para combinaciones candidatas; se conserva como máximo un RGBA por variante
candidata única durante el análisis host.

Cada grupo enumera formas, mallas, selector y bloque candidato. Cada bloque
conserva offsets y hashes, dimensiones y variantes de paleta. Las imágenes
candidatas se deduplican comparando bytes y dimensiones, no solo sus hashes.
El alpha estadístico no se usa para decidir opacidad, descarte o transparencia.
La iluminación, niebla, TEX0/CLAMP/TEST/ALPHA/ZBUF y visibilidad original
requieren evidencia de consumo antes de reemplazar el material diagnóstico.

## Secuencia

- HM-T4c.3.1: inventario, decodificación, deduplicación y presupuesto candidatos.
- HM-T4c.3.2: selección/estados de material y consumo original contrastados.
- HM-T4c.3.3: datos y render de materiales verificados, host/ARM y entrega.

HM-T5 queda aplazado por indicación del usuario. Su evidencia previa se conserva.
