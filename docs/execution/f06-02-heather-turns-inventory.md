# F06.02/heather-turns — HG-T1: fuentes y poses de giro

2026-10-30. **HG-T1 completada** como investigación preparatoria de F06.02.
El usuario aplazó expresamente las mediciones y pruebas adicionales de HM-T5
después de confirmar `c3aae59d1a70`. Se conserva esa entrega en consola.
[Requisitos, diseño y secuencia HG](../specs/sh3-3ds/heather-turns.md).

## Objetivo y alcance

La siguiente unidad de F06.02 es incorporar giro a las animaciones originales
de Heather. HL ya integra espera, caminar y correr; el perfil HM gira al actor
sin seleccionar los clips originales de giro sobre el sitio. Esta unidad
contrasta sus fuentes y las poses disponibles antes de diseñar las nuevas
transiciones. No cierra F06.02 ni sus dependencias generales G04/G05/F06.01.
Requisitos RF04.03/RF04.04, HG01–05; preparación del caso T04. Incógnitas
Q05/Q06: formatos/corpus y lógica/tiempo, con límites explícitos de equivalencia.

Se releyeron MDL522 y ANM525 de la extracción privada y se cotejaron byte a
byte con una adquisición desde la ISO europea fijada. Se verificaron la
identidad completa de la imagen, XBG0.MFA, el par seleccionado y el ELF.
Son dos rutas de adquisición; no dos nuevas copias publicadas. Los recursos
completos también coinciden con los seis estados examinados.

## Descriptores y selección observada

| Acción | ID | Muestras fuente | Velocidad ELF → PAL | Incremento con ticks 2 | Período Q12 |
| --- | ---: | --- | --- | ---: | ---: |
| Giro derecho sobre el sitio | 107 | 60–69 | 960 → 1152 | 2304 | 40960 |
| Giro izquierdo sobre el sitio | 108 | 70–79 | 960 → 1152 | 2304 | 40960 |

Se conservan los doce bytes de cada descriptor y la conversión PAL del
inventario HL. Los veinte frames contienen los mismos 36 huesos activos y
una jerarquía cerrada. Ambos canales coinciden en las poses estables.
La ventana de caminar+izquierda usa 109; no se le asigna 108 por inferencia.

## Poses cotejadas

El comprobador puro exige modo estable, fuente igual a destino, offset y
mezcla cero, incremento coherente y dos canales completos. Recupera la fase
evaluada anterior al contador devuelto y envuelve cada clip en su propio rango.
Reutiliza el oráculo independiente de reloj y los oráculos de reconstrucción
de cuaterniones, NLERP corto y composición jerárquica, sin usar el renderer.

| Estado | ID | Contador devuelto | Fase evaluada | Frames | Error máximo |
| --- | ---: | ---: | ---: | --- | ---: |
| 57, derecha | 107 | 6912 | 4608 | 61 → 62 | 0,000339243 |
| 64, derecha con wrap | 107 | 512 | 39168 | 69 → 60 | 0,000283510 |
| 211, izquierda | 108 | 16128 | 13824 | 73 → 74 | 0,000342952 |
| 217, caminar+izquierda | 109 | 39920 | 35928 | 88 → 89 | 0,000200355 |
| 223, caminar recto con wrap | 109 | 2992 | 97304 | 103 → 80 | 0,000341403 |

Las **180 matrices / 2880 componentes** quedan por debajo del límite
absoluto previo **0,001**, sin ampliarlo. Los doce controles negativos usan
contador posterior, clip contrario, clamp o frame del clip contiguo. Todos
superan el límite; el menor error negativo es **12,63986**.

Los estados derechos pertenecen a PID histórico 18885, con restauración
adicional declarada en el estado 46. La otra serie pertenece a PID 4124,
con restauración inicial y de reproducción declaradas. Se verificaron hash
de estado/RAM, PC de retorno, registros, ordinal, ciclo, actor, recursos,
descriptores, índices de frame de ambos canales y 21 ventanas ELF/RAM.
No se afirma continuidad entre sesiones ni un ciclo completo desde muestras
separadas. No hubo nueva adquisición runtime ni escritura al juego.

El estado **71** conserva `107→101`, modo 3 y beta 2664, tras liberar el
giro derecho. Se rechaza como pose estable. Falta la pose local congelada
anterior y la secuencia completa: no acredita la transición ni su duración.

## Pruebas y evidencia reproducible

- 72 pruebas nuevas con un loop inventado de tres frames: wrap, fase previa,
  entradas inválidas, descriptores, divergencia de canales y mezcla rechazada.
- 195 pruebas relacionadas aprobadas, incluidos reloj/pose, precisión,
  descriptores y continuidad. Cobertura nueva: 35/35 sentencias y 22/22 ramas.
- Gate individual ≥80/80 añadido a CI. Lint y formato comprobados localmente.
- Auditoría privada normal y `python -O`: informes idénticos; el adaptador
  usa comprobaciones explícitas, no `assert` para aceptar las fuentes.
- Chequeos de dependencias, custodia y contratos del repositorio: PASS,
  cero errores. La ejecución remota de CI no se ha comprobado en esta unidad.

Implementación: `tools/qa/steady_clip_observation.py`.
Tests: `tests/python/test_steady_clip_observation.py`.
Adaptador local: `build/heather-turns/audit_existing.py`.
Informes ignorados, sin recursos ni matrices exportadas:
`reports/local/heather-turns-existing-v1.json` y
`reports/local/heather-turns-existing-v1-opt.json`.
Logs/cobertura: `build/heather-turns/tests.xml`, `coverage.json`.

El primer intento fue rechazado antes de publicar por una diferencia de
representación histórica: un informe guarda direcciones como texto hexadecimal
y otro como enteros. Se normalizó ese campo en el adaptador, conservando los
mismos hashes/rangos; `build/heather-turns/initial-attempt.txt` registra el fallo.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/python/test_steady_clip_observation.py tests/python/test_animation_pose_oracle.py tests/python/test_animation_precision.py tests/python/test_animation_descriptors.py tests/python/test_animation_continuity.py --cov=tools.qa.steady_clip_observation --cov-branch --cov-report=json:build/heather-turns/coverage.json
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-turns/coverage.json --files tools/qa/steady_clip_observation.py
rtk proxy .venv/bin/python build/heather-turns/audit_existing.py /tmp/heather-turns-recheck.json
rtk proxy .venv/bin/python -O build/heather-turns/audit_existing.py /tmp/heather-turns-recheck-opt.json
```

Cada auditoría requiere un destino nuevo y fuentes privadas disponibles.
CI solo ejecuta los fixtures propios; no requiere originales.

## Siguiente unidad

**HG-T2:** capturar ciclos continuos y transiciones espera↔giro en ambos
sentidos con controles normales, separar las restauraciones y cotejar origen
congelado, wrap y salida. Después se fijará el contrato nativo antes de ampliar
el núcleo y el formato. No se genera un build ARM porque esta unidad no cambia
el runtime. Las mediciones y pruebas adicionales de HM-T5 siguen aplazadas.

## Continuación verificada

[HG-T2 completada](f06-02-heather-turns-cycles.md): nuevas capturas continuas
de ambos ciclos y las cuatro transiciones. Las muestras aisladas de este
inventario conservan su alcance original; no se reinterpretan como ciclos.
La siguiente unidad es HG-T3, contrato y vectores nativos. HM-T5 sigue aplazada.
