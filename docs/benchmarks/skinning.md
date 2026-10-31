# F06.03 / HS-T1: carga de skinning de Heather

2026-10-30. **HS-T1 completada: inventario estructural y contrato.**
No se ha ejecutado skinning GPU ni medido una mejora de rendimiento.
Sigue [HS-T2, paletas y vectores del prototipo](../specs/sh3-3ds/heather-skinning.md).
El build de consola continúa siendo `0188790baedd`; HM-T5 adicional y pared
60 permanecen aplazadas.

Actualización de continuidad: [HS-T2 completada](../execution/f06-03-heather-skinning-contract.md)
el mismo día; contrato de 30 matrices, sonda SDK y vectores fijados.
[HS-T3 completada en host](../execution/f06-03-heather-skinning-prototype.md):
prototipo, fallback, recursos e intervalos comprobados. **Sigue HS-T4**.
Las capacidades de la tabla HS-T1 siguen siendo parámetros
analíticos; no se reinterpretan como límites de rendimiento de la consola.

## Entradas y cotejo

Las fuentes privadas `heather-turns-a-v1` y `heather-turns-b-v1` conservan
14 archivos cada una: SRI2 y 13 texturas. Se autentican contra el manifiesto
SHA-256 `a33d89733b506a286e11c00d3f8553f7a2c179f10bc2d08e5baebadfb9f0ca30`.
El SRI2 tiene 310356 bytes y SHA-256
`c275f3bbfc7cc5dcb45af738460b2c71b184aad4f90973e5f0b22e7725b24865`.
Lectura regular sin seguir enlaces, límites explícitos y relectura de
contenido/identidades de archivos y padres antes de publicar el informe.

El reconstructor independiente valida SRI2, texturas y CRC; el lector C++
de producción abre ambos bundles. Se cotejan **todos** los campos emitidos:
perfil, encuadre, huesos, clips, muestras, auxiliares, vértices, índices y
materiales. Coinciden bit a bit los flotantes reconstruidos y los enteros.
Las particiones se cotejan además contra índices/materiales del volcado
nativo. A/B tienen archivos, volcados y resultados idénticos.

Perfil 2: clips 101/109/113/107/108, 78 muestras y 36 huesos activos.
Este inventario usa la geometría compartida; no sustituye los cotejos de
poses y transiciones de HG ni mide el coste de sus cuadros.

## Carga observada

| Magnitud | Resultado |
| --- | ---: |
| Vértices almacenados / referenciados | 6943 / 6924 |
| Vértices sin índices | 19 |
| Índices / triángulos | 16566 / 5522 |
| Materiales opacos / mezclados | 12 / 1 |
| Matrices preparadas: huesos + auxiliares | 36 + 49 = 85 |
| Matrices usadas por dibujo | 34 + 49 = 83 |
| Evaluaciones de influencia CPU actuales | 9901 por preparación |
| Evaluaciones sobre vértices referenciados únicos | 9874 |
| Evaluaciones si se repitieran por índice | 24035 |

Las tres últimas filas son conteos estructurales, **no operaciones de GPU,
ciclos ni tiempos**. El núcleo actual recorre también los 19 vértices sin
índices. Los auxiliares ocupan `73 + id` en `RigPalette`, aunque haya 36
huesos activos; usar `36 + id` cambiaría el resultado. El almacenamiento
fijo admite 73+128 entradas, pero eso no es un límite de uniforms GPU.

| Grupo de vértices referenciados | 1 influencia | 2 | 3 | Total |
| --- | ---: | ---: | ---: | ---: |
| Opacos | 4079 | 1998 | 476 | 6553 |
| Cabello | 371 | 0 | 0 | 371 |
| Ambos grupos | 4450 | 1998 | 476 | 6924 |

No comparten vértices. Los 371 del cabello usan solo la matriz primaria 9,
con W=1; forman 240 triángulos/720 índices. Por ello el primer candidato
será híbrido: opacos en GPU y cabello en CPU, conservando la mezcla con
vidrio. Esta selección de prototipo no acredita una mejora.

Las sumas Q12 de los vértices referenciados son **4094: 276; 4095: 2014;
4096: 4634**. No hay influencias activas con peso cero en este recurso.
Los 2290 casos deficientes pertenecen a opacos: normalizarlos o sustituir
W por 1 cambiaría la posición y la traslación. Los ensayos sintéticos
incluyen también peso activo cero para no eliminar ese caso válido.

## Particiones analíticas

El planificador conserva el orden original de triángulos y las fronteras
de material. Cada lote es el prefijo contiguo máximo cuya unión de matrices
cabe en la capacidad elegida. No divide triángulos ni fusiona matrices
auxiliares por tener el mismo target. Si un triángulo no cabe, no publica
ningún plan parcial. Minimiza el número de lotes bajo esas restricciones;
no optimiza reordenación, transferencias persistentes ni coste de GPU.

| Capacidad hipotética de matrices | Lotes opacos | Suma de matrices por lote | Vértices si se duplican por lote |
| --- | ---: | ---: | ---: |
| 8 | 150 | 1053 | 6781 |
| 12 | 68 | 713 | 6665 |
| 16 | 41 | 534 | 6598 |
| 24 | 21 | 317 | 6563 |
| 32 | 12 | 123 | 6553 |
| 48 | 12 | 123 | 6553 |
| 64 | 12 | 123 | 6553 |
| 96 | 12 | 123 | 6553 |

Son parámetros del análisis, **no capacidades verificadas de PICA200**.
El material opaco más exigente usa 31 matrices; el triángulo más exigente
usa 8. La suma por lote supone enviar su paleta completa cada vez, sin
deducir reutilización. Los lotes tampoco equivalen al total de draw calls:
faltan habitación, cabello y vidrio. Aumentarlos puede compensar cualquier
ahorro de deformación CPU; eso requiere medición.

## Fronteras del baseline y del ensayo pendiente

`PreparedRoomScene::frame` prepara la paleta, deforma todos los vértices,
transforma/valida posiciones, ordena conjuntamente cabello y vidrio, y
expande índices. `RoomRenderer::present` espera después en `C3D_FrameBegin`,
copia/flush del VBO y envía rangos. El shader actual solo aplica la matriz
de vista/proyección a posiciones ya deformadas; no hace skinning.

Por tanto, `prepare_ms` mezcla paleta, deformación, ordenación y expansión;
`submit_ms` mezcla espera, transferencia y envío. HS-T3 separará esos
intervalos y los enlazará con el cuadro correspondiente antes de medir.
La pose y los contactos ocurren fuera de esos intervalos. El presupuesto
[HG de 49,42/64 MiB](../execution/f06-02-heather-turns-resources.md) es la
referencia anterior, no una medición nueva ni la memoria de un prototipo GPU.
La mejora histórica [HP](../execution/f03-02-heather-performance.md) fue una
optimización CPU del visor; no constituye una comparación CPU/GPU de hp34.

## Validación y reproducción

La herramienta pura `tools/qa/skinning_workload.py` valida SRI2 antes de
contar y devuelve agregados/planes sin modificar datos. Las pruebas usan
SRI2 inventado: perfiles 1/2, 1/2/3 influencias, los tres valores de W,
auxiliares separados, capacidad exacta/insuficiente, fronteras de material,
ausencia de opacos, vértices sin índices y rechazo sin salida parcial.
Una búsqueda exhaustiva independiente de cortes valida el mínimo de lotes
para 32 secuencias pequeñas reproducibles; se comprueban cobertura, orden
y paletas exactas. Gate individual incorporado a CI.

**400 pruebas Python aprobadas**, incluidas las 18 nuevas y las regresiones
del reconstructor SRI2/HL/HG; cobertura individual de la herramienta
**100 % líneas / 100 % ramas**. Ruff/formato, contratos del repositorio
(0 errores) y `git diff --check` aprobados. Entorno host: Python 3.14.6 y
pytest 9.1.1. El cotejo privado reutiliza el lector Release existente,
identificado por hash y con target CMake al día; su configuración registra
Apple Clang 15. Las regresiones SRI2 recompilan su lector con el `c++`
actual, Apple Clang 21. No se confunden ambas compilaciones.

Comandos desde la raíz, con el entorno Python del proyecto:

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_skinning_workload.py tests/python/test_locomotion_rig_reconstruction.py tests/python/test_heather_turns_sri2.py --cov=tools.qa.skinning_workload --cov-report=json:build/heather-skinning/coverage.json --junitxml=build/heather-skinning/pytest.xml
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-skinning/coverage.json --files tools/qa/skinning_workload.py
rtk proxy cmake --build build/host-release --target test_inspection_locomotion -j 2
rtk proxy .venv/bin/python build/heather-skinning/audit.py
```

El último comando requiere las copias privadas autenticadas y permanece
en el área local ignorada. Informe:
`reports/local/heather-skinning-workload-v1.json`, con hashes de entradas,
fuentes del recorrido y ejecutable nativo. Los datos originales no se
publican. La compilación y el cotejo son host; no se cambió código de la
consola ni se generó un nuevo build ARM en HS-T1.
