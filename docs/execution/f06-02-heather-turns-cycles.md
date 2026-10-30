# F06.02/heather-turns — HG-T2: ciclos y transiciones

2026-10-30. **HG-T2 completada** mediante nuevas capturas del original en
PCSX2 y reconstrucción independiente. Ambos ciclos y las cuatro transiciones
espera↔giro quedan verificados. Las pruebas adicionales de **HM-T5 siguen
aplazadas** por petición del usuario; se conserva la entrega `c3aae59d1a70`.

[Spec y secuencia HG](../specs/sh3-3ds/heather-turns.md).
[Fuentes y poses previas, HG-T1](f06-02-heather-turns-inventory.md).
No se cierra F06.02 global, G04/G05, movimiento general ni navegación de pared 60.

## Captura y custodia

La sesión privada `heather-turns-capture-v4`, PID 89573, contiene **70
actualizaciones únicas consecutivas**, ordinales 82020–82089, todas en el
retorno completo `0x001dd434`, `s0=0x004481d0`, sin delay slot y con ticks=2.
Se guardaron 71 estados: la ranura 2 es una segunda adquisición del mismo
ancla pausada, con RAM/CPU/ciclo idénticos; se excluye del conteo y del ciclo.
La secuencia aceptada es 1, 3–71. No se omitió ninguna actualización del juego.

Se restauró una sola vez el estado de espera `heather-transition-recovery-v2`,
ranura 82. SHA-256 del ancla:
`d4831eda82f522a2994551394558f590d684aefb76fc691925dfcd358dd559bb`.
RAM, PC, GPR y ciclo coinciden tras restaurar. Los internals tienen igual
longitud, 129962 bytes, y 42 bytes distintos: no se afirma igualdad del estado
completo del emulador. No hubo restauraciones entre las muestras aceptadas.

Se usó una copia privada de PCSX2 con identificador de aplicación exclusivo
para evitar la ambigüedad entre instalaciones. El ejecutable sigue siendo
idéntico al original, SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
El perfil privado activa un control sostenido de derecha con J y otro de
izquierda con K, mediante las macros nativas de un solo botón, presión 1 y
frecuencia 0, sin turbo. Se retiran únicamente las asignaciones directas
Keyboard/Right y Keyboard/Left del perfil de captura: su limpieza al perder
foco anulaba la dirección sostenida. La entrada pasa por el puerto normal;
no se inyecta memoria del juego ni se fabrica una grabación de entrada.

Cada avance se solicita desde el depurador. El observador de solo lectura
comprueba el retorno/ordinal/ciclo y encola el guardado PINE. Después se
releen los estados, se cotejan con ese punto de adquisición y se enlazan los
hashes de los recibos. Se verifican ambos canales, bits actuales/anteriores,
held/pressed/repeated/released, conexión del mando, recursos completos en
RAM, descriptores PAL y ocho ventanas de código contra el ELF original.
La extracción MDL522/ANM525 se vuelve a cotejar con la ISO autenticada.

PCSX2 cerró normalmente; los hashes del perfil original, BIOS y tarjetas
copiadas se conservaron. Los 71 estados ocupan 1065251146 bytes, fuera del
repositorio; quedaban aproximadamente 2,50 GiB libres al terminar.

Intentos anteriores conservados, sin sumar sus muestras a los ciclos:

- **v1:** identidad de aplicación ambigua y un salto de ordinal; incompleto.
- **v2:** preparación y comprobación de foco; sin ciclo aceptado.
- **v3:** direcciones liberadas al perder foco, con tramos estables cortos;
  no se acreditan como ciclos completos ni se empalman con v4.

## Ciclos completos

Se exige continuidad de ordinal y ciclo EE creciente, ambos canales iguales,
clip/incremento constantes y fase coherente. El avance acumulado debe cubrir
al menos un período. El contador devuelto se distingue de la fase evaluada.

| Dirección | Clip / cuadros | Ranuras estables | Poses | Avance Q12 / período |
|---|---|---|---:|---:|
| Derecha | 107 / 60–69 | 9–27 | 19 | 41472 / 40960 |
| Izquierda | 108 / 70–79 | 43–61 | 19 | 41472 / 40960 |

En ambos casos, velocidad PAL=1152, ticks=2 e incremento=2304. Las 18
separaciones entre poses cubren 10,125 cuadros del recurso. Se observan los
pares 69→60 y 79→70 con fracción no nula, el wrap del contador devuelto
39168→512 y el posterior wrap de la fase evaluada. Esto acredita ciclos de
animación; no supone una vuelta mundial de 360 grados ni resuelve el cruce ±pi.

## Cuatro transiciones completas

| Arco | Origen congelado | Muestras de mezcla | Primera pose estable |
|---|---:|---:|---:|
| 101→107 | 3 | 4–8 | 9 |
| 107→101 | 27 | 28–35 | 36 |
| 101→108 | 37 | 38–42 | 43 |
| 108→101 | 61 | 62–69 | 70 |

Las entradas a giro usan modo 3 y pesos Q12
`768, 1536, 2304, 3072, 3840`; la sexta actualización termina la mezcla.
Las salidas usan
`1024, 1434, 1844, 2254, 2664, 3074, 3484, 3894`; la novena termina la mezcla.
El primer incremento de salida es 1024; los siguientes son 410, con offset
de mezcla −307. No se reutiliza la progresión de caminar↔espera.

La fuente congelada es la **pose local ya interpolada de la actualización
anterior**, no el cuadro entero que señala el canal ni su contador posterior.
Las fracciones Q12 de origen son 1018 para entrar a derecha, 614 para entrar
a izquierda y 512 para ambas salidas. Se mezcla contra el primer cuadro del
destino mediante NLERP corto y LERP de traslación, y después se compone la
jerarquía. El contador permanece a cero en modo 3; el incremento de reloj
anterior se conserva hasta terminar. Al completar, la fase evaluada es cero
y el contador devuelto ya avanzó a 2304 en giro o 614 en espera.
El offset de mezcla puede persistir inactivo en espera; no altera su reloj.

## Oráculo, negativos y pruebas

Se reconstruyen las **36 matrices modelo de cada una de las 70 poses** desde
MDL522/ANM525, con los oráculos de pose y precisión existentes. Son 2520
matrices; error absoluto máximo **0,0004684641970698067**, inferior al límite
inalterado **0,001**. La mayor diferencia aparece al entrar a giro derecho.

Se evalúan 164 controles negativos: contador posterior, clip contrario,
wrap por clamp/cuadro adyacente, eliminación de la fracción de origen,
mezcla invertida y destino sin mezcla. **162 se rechazan** por superar 0,001.
Los dos restantes son el clip contrario en las ranuras 25 y 59: las poses
finales originales de ambos clips difieren como máximo en
`3,725290298461914e-09`, y no son discriminantes con esta tolerancia.
Se conservan explícitamente; cada ciclo y cada arco tiene controles
discriminantes de todas sus categorías. No se comprueba el wrap con fracción
cero porque en ese punto elegir un sucesor distinto no afecta a la pose.

El nuevo comprobador `tools/qa/steady_cycle_observation.py` rechaza tramos
cortos, huecos, tiempo repetido/invertido, cambios de clip/reloj, fase errónea,
mezclas y canales discordantes. Sus 19 pruebas son sintéticas. Las **214
pruebas relacionadas pasan**; cobertura nueva **29/29 sentencias y 16/16
ramas, 100/100**, con gate individual añadida a CI. También pasa el control
del repositorio. La auditoría normal y con Python `-O` produce bytes idénticos.

Informe local de metadatos: `reports/local/heather-turns-cycles-v1.json`
y repetición `heather-turns-cycles-v1-opt.json`. SHA-256 común:
`478d2c60ec9bcdc8d1f7b572847e72f9cd410a609fc61f108d4ed5fcd494567e`.
Los borradores de la auditoría se conservan aparte. La comprobación inicial
exigía que todo negativo discriminara en toda pose; se corrigió al observar
los finales coincidentes, manteniendo el límite numérico y registrando ambas
excepciones. No se modificaron los recursos para hacer pasar el cotejo.

Adaptador reproducible local: `build/heather-turns/audit_cycles.py`.
Adquisición: `launch_capture_v4.py`, `capture_v4.py`, `queue_v4.py` y
`decode_v4.py`, en la misma carpeta. El informe fija sus hashes. Los estados,
recibos y perfiles se conservan bajo el directorio privado externo.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/python/test_steady_cycle_observation.py tests/python/test_steady_clip_observation.py tests/python/test_animation_pose_oracle.py tests/python/test_animation_precision.py tests/python/test_animation_descriptors.py tests/python/test_animation_continuity.py --cov=tools.qa.steady_cycle_observation --cov=tools.qa.steady_clip_observation --cov-branch --cov-report=json:build/heather-turns/cycles-coverage.json
rtk proxy .venv/bin/python -m tools.qa.coverage_gate build/heather-turns/cycles-coverage.json --files tools/qa/steady_cycle_observation.py tools/qa/steady_clip_observation.py
rtk proxy .venv/bin/python build/heather-turns/audit_cycles.py /tmp/heather-turns-cycles-recheck.json
rtk proxy .venv/bin/python -O build/heather-turns/audit_cycles.py /tmp/heather-turns-cycles-recheck-opt.json
```

## Siguiente unidad

**HG-T3:** fijar contrato y vectores nativos a partir de estas observaciones.
HG-T2 no amplía HLC/SRI2, no integra todavía los giros en el runtime, no genera
un build ARM ni aporta una nueva prueba de consola. El giro en marcha y los
arcos directos derecha↔izquierda quedan fuera de esta captura. HM-T5 sigue
aplazada.
