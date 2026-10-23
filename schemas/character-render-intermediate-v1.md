# IR-T5 — Intermedio de materiales, luces y colocaciones

2026-10-23. Perfil `ps2-character-0209-render-v1`, definido antes de implementar.
Extiende por composición el [perfil inicial](intermediate-v1.md), que permanece
inalterado. RF02.04/RF02.05; únicamente el caballo 0x0209 y las capturas CT/LI/GC
ya verificadas. No representa una escena completa ni cierra F03.04 global.

## Requisitos EARS

- **IR07** WHEN importa SHALL verificar hashes/tamaños de manifiestos,
  intermedio base, documentos CT/LI/GC y estado GC; SHALL comprobar identidad
  MDL/ANM y enlaces entre capturas antes de publicar.
- **IR08** WHEN serializa SHALL conservar todos los campos originales de
  materiales, referencias, preset y manifiestos, incluidos estados GS y
  desconocidos. SHALL conservar exactamente los 21 blobs: tres imágenes de
  índices, doce paletas, tres RGBA originales y tres PNG de inspección.
- **IR09** WHEN reconstruye SHALL regenerar SAN/SCM/SCT/SCL/SCW únicamente
  desde el JSON intermedio y sus blobs, sin ISO, estados PCSX2 ni entradas
  históricas. SHALL comprobar que índices y paleta 0 reproducen RGBA y que
  los datos regenerados coinciden con las entregas CT/LI/GC fijadas.
- **IR10** WHEN describe convenciones SHALL distinguir alpha PS2 conservado
  de PNG normalizado, material opaco de sus texeles alpha cero, preset fijo
  de selección de luces y colocaciones fijas de trayectoria. SHALL mantener
  iluminación y mundo como variantes separadas de inspección.
- **IR11** IF falta un blob, hay nombres extra/duplicados, hash/tamaño distinto,
  formato no soportado, referencia incoherente o transformación inválida
  SHALL rechazar antes de publicar. SHALL conservar las salidas anteriores.
- **IR12** WHEN verifica SHALL usar fixtures sintéticos en CI, cobertura de
  líneas/ramas ≥80 %, dos conversiones privadas independientes y comparación
  con las entregas físicas; SHALL distinguir igualdad de datos de una nueva
  prueba del renderer o de la consola.

## Diseño y límites

Raíz exacta: `schema_version=1`, `profile`, `converter`, `conventions`, `base`,
`documents`, `provenance`. `base` conserva el árbol íntegro del perfil inicial.
`documents` conserva `materials`, `material_reference`, `lighting_preset`,
`lighting_reference`, `world_reference` y `world_placements`. Este último
contiene las tres matrices extraídas del estado GC, identificadores y contador.
`provenance` contiene `base_manifest`, `materials_manifest` y `source_sha256`.
Los hashes de entrada describen los bytes históricos, no el JSON recodificado.
La integridad del conjunto publicado se comprueba con su manifiesto externo.

Los blobs llevan los nombres fijos de la extracción CT. Se mantienen fuera
del JSON para conservar bytes exactos sin ampliar los límites del codec ni
codificarlos como enormes listas/base64. El conjunto intermedio es JSON más
esos 21 blobs; un JSON aislado no contiene los texeles. Los PNG se conservan
por hash, sin recodificación dependiente de la versión de zlib. No se infiere
soporte de las paletas 1..3 en dibujo por conservarlas.

JSON mantiene el presupuesto de 8 MiB/profundidad 32/500.000 nodos del perfil
inicial. Cada imagen de índices mide 262.144 bytes, cada paleta 1.024, cada
RGBA 1.048.576 y cada PNG tiene como máximo 1 MiB. Inventario exacto de 22
entradas CT, incluido `materials.json`; no se admiten rutas arbitrarias.
Estado PCSX2 de entrada ≤64 MiB, leído solo durante importación; se conservan
su SHA y los metadatos del informe, no los 32 MiB de RAM ni el estado completo.
Salida de 27 archivos más manifiesto, presupuesto del writer ≤40 MiB.

El adaptador puro `character_render_intermediate` valida relaciones y aplica
las recetas SCT/SCL/SCW existentes. El lector/preparador separado verifica
entradas acotadas y extrae las matrices mediante el validador GC existente.
El writer privado publica con nombres permitidos y carpeta exclusiva. El
renderizador y los visores existentes no cambian.

La CLI recibe `--inputs` (JSON local ≤16 KiB) con siete pares `path/sha256`:
`base`, `materials` (directorios y SHA de manifiesto), `material_reference`,
`lighting_preset`, `lighting_reference`, `world_reference`, `world_state`
(archivos y SHA). Las rutas solo pertenecen al preparador, no al intermedio.
El perfil guarda convenciones y recetas explícitas para alpha, UV, filtros,
iluminación, base y espacio mundo; rechaza cambios en esos contratos.

## Tareas

- [x] **IR-T5a** (IR07/IR08/IR10/IR11): contrato, inventario acotado y adaptador
  puro; conservar metadatos, índices/paletas/RGBA/PNG y validar relaciones.
- [x] **IR-T5b** (IR07/IR09/IR11): preparador privado por entradas fijadas,
  extracción GC, reconstrucción independiente y publicación exclusiva.
- [x] **IR-T5c** (IR08/IR09/IR11/IR12): fixtures asimétricos, conservación de
  desconocidos, errores de enlaces/blobs/transformaciones, ausencia de fuentes,
  CLI y regresiones de los tres encoders; gate de líneas/ramas.
- [x] **IR-T5d** (IR07/IR09/IR12): convertir A/B, releer todo y comparar cinco
  formatos con entregas físicas fijadas. Documentar hashes y limitaciones;
  actualizar backlog sin cerrar F03.04 global.

[Ejecución y hashes](../docs/execution/f03-04-character-render-intermediate.md):
231 tests, cobertura combinada 98,46 %, 27 archivos A/B idénticos y cinco
formatos iguales a las entregas físicas. Sin nueva prueba de renderer/hardware.

Después de IR-T5 siguen perfiles de mapa, colisión, cámara y audio; el paquete
de escena SH3P requiere el contrato F03.05. La selección de luces entre escenas,
trayectoria, daño y muerte siguen pendientes.
