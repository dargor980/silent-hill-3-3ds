# F06.02/heather-turns — HG-T3: contrato y vectores nativos

2026-10-30. **HG-T3 completada**. Se fija el contrato del perfil de giros y
sus resultados esperados antes de implementar el núcleo ampliado. Estado
**`specified_not_integrated`**. Las mediciones y pruebas adicionales de
**HM-T5 siguen aplazadas**; se conserva la entrega `c3aae59d1a70`.

- [Contrato HGT01–12](../../schemas/heather-turns-native-v1.md).
- [Vectores sintéticos](../../tests/fixtures/synthetic/heather-turns-native-v1.json).
- [Comprobaciones independientes](../../tests/python/test_heather_turns_contract.py).
- [Secuencia y siguientes tareas](../specs/sh3-3ds/heather-turns.md).

## Evidencia utilizada y decisiones

Se releyeron el contrato HL, el coordinador HM, sus rutas reales de reloj,
actor/controlador, productor SRI2, lector y almacenamiento. Se autenticó
el informe de HG-T2 con SHA-256
`478d2c60ec9bcdc8d1f7b572847e72f9cd410a609fc61f108d4ed5fcd494567e`:
dos ciclos, cuatro transiciones, 70 actualizaciones/2520 matrices, error
máximo `0.0004684641970698067` frente a `0.001`. No hubo nuevas capturas
ni nueva reconstrucción de estados privados durante HG-T3.

Perfil **2**, `heather-original-pal-525-turns-v1`: clips en orden
101,109,113,107,108, con 78 muestras. Los tres primeros descriptores y sus
índices se conservan. Los giros agregan los rangos 60–69 y 70–79 de ANM525,
incremento Q12 2304 y período 40960. Se fijan fase consumida y contador
devuelto por separado, incluido el wrap fraccionario al primer cuadro.

Las cuatro transiciones congelan la última pose local **interpolada** de
ambos canales. Entrada a giro: beta inicial 768, suma 768, salida en el sexto
paso. Retorno a espera: beta inicial 1024, suma 410, salida en el noveno.
Las tasas son por arco: no sustituyen el 1280/360 de caminar/correr→espera.
Los dos avances al salir de modo 5 siguen siendo exclusivos de caminar↔correr.

La selección directa queda cerrada en nueve arcos, cinco continuaciones y
once rechazos. La aplicación conservará una última **acción** que distinga
derecha/izquierda, completará mezclas y recorrerá los arcos por espera cuando
no exista transición directa. Espera→correr conserva el puente por caminar.
El yaw usa los botones actuales; avance tiene prioridad para elegir clip.
Estas rutas y prioridades son políticas nativas, no observaciones nuevas
de PS2. No se habilitan interrupciones, giro directo entre sentidos ni giro
en marcha mediante un clip 107/108.

## Formato y memoria

SRI2 conserva layout, magic y cabecera de 96 bytes; ID 2 selecciona cinco
descriptores/78 muestras. ID 1 sigue aceptando exactamente tres/58. El lector
antiguo rechaza el perfil nuevo. Se fijan rechazos de cruces de perfil,
conteos, orden, reservados y datos corruptos; nunca truncado o fallback.

El límite actual de almacenamiento de **64 muestras es insuficiente**.
HG-T4 deberá usar capacidad 80, separada del máximo admitido por SRI1 (64)
y de las cantidades exactas SRI2 (58/78). Aumentar una constante global sin
separar esas validaciones ampliaría indebidamente el formato legado.

| Magnitud calculada | Perfil 2 / cambio |
|---|---:|
| Archivo SRI2 | 310356 bytes |
| Incremento del archivo | 20200 bytes |
| TR activas, 36 huesos × 78 muestras | 78624 bytes |
| Capacidad TR, 73 huesos × 80 muestras | 163520 bytes |
| Aumento por rig decodificado | 32704 bytes |

Estas cantidades son aritmética del formato/almacenamiento. El pico real,
copias de carga, pila y memoria ARM se medirán al integrar. Los presupuestos
de estado+scratch y coordinadores permanecen en 32 KiB cada uno según sus
límites existentes; no se permiten asignaciones por paso. No cambian mallas,
materiales, texturas, contactos ni orden de dibujo de hp34. Su transformación
compartida no podrá sustituirse por el encuadre del visor aislado.

## Vectores y validación realizada

El JSON contiene cinco descriptores, dos máscaras, 14 límites de fase,
dos ciclos de 19 filas, cuatro arcos con 26 poses mezcladas ficticias,
25 selecciones directas, 32 entradas de botones, 25 rutas y 36 pasos de replay.
Añade 34 continuaciones sin solicitud/mismo destino, 76 rechazos, nueve
combinaciones wire, nueve escenarios de ciclo de vida y 19 puntos de
inyección de fallos para la futura integración.

Los TR son inventados; las fracciones de caché 1018/512/614/512 son metadatos
observados aplicados a esos TR sintéticos. Las comprobaciones usan Decimal,
fracciones racionales y un grafo independiente. No importan el evaluador
C++, el productor ni recursos privados. La regresión compara literalmente
el prefijo de clips y las máscaras contra los vectores HL existentes.

Resultado: **248 pruebas nuevas; 492 relacionadas pasan**. Ruff y formato
del test pasan; control del repositorio con **0 errores**, diff sin errores
de espacios. JUnit local: `build/heather-turns-contract/contract-tests.xml`.
Informe local de metadatos: `reports/local/heather-turns-contract-v1.json`.
No se incorpora módulo productivo nuevo ni se atribuye cobertura C++ a
estas comprobaciones del contrato.

SHA-256 de los vectores:
`433811f29a1687bb5bd357d73234f7290a0cbef407df18a6dba1575c62c833ae`.
El JSON fijado es la entrada de las futuras pruebas nativas; no debe
regenerarse a partir del resultado del código bajo prueba.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/python/test_heather_turns_contract.py tests/python/test_heather_locomotion_contract.py tests/python/test_steady_cycle_observation.py tests/python/test_steady_clip_observation.py tests/python/test_animation_pose_oracle.py tests/python/test_animation_precision.py tests/python/test_animation_descriptors.py tests/python/test_animation_continuity.py --junitxml=build/heather-turns-contract/contract-tests.xml
rtk proxy .venv/bin/python -m ruff check tests/python/test_heather_turns_contract.py
rtk proxy .venv/bin/python -m ruff format --check tests/python/test_heather_turns_contract.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk git diff --check
```

## Cierre de esta unidad y continuación

HG-T3 define y verifica consistencia numérica. La inyección real de fallos,
publicación conjunta byte a byte, carga del perfil 2, cero asignaciones y
replays C++ siguen pendientes en **HG-T4**. Se ha desglosado en núcleo,
productor/lector SRI2 y fuentes A/B, coordinación con HM, y validación de
memoria/gates/ARM. La fidelidad de esa futura implementación deberá cotejarse
contra las 70 referencias privadas HG-T2 con tolerancias sin ampliar.

No se modificó runtime ni se generó/cargó un build nuevo. HG-T5 empaquetará
la entrega una vez integrada. No se cierra F06.02 global, G04/G05, movimiento
general ni pared 60. Las pruebas adicionales de HM-T5 permanecen aplazadas.
