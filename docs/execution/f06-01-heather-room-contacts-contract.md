# HM-T4b.1 — Contrato numérico y vectores de contactos

2026-10-29. **HM-T4b.1 completada.** [HRC v1](../../schemas/heather-room-contacts-v1.md)
fija la evaluación numérica del perfil `static-xz-aabb-stop-v1`, sus límites,
errores, publicación y vectores propios antes de implementar el núcleo.
**Actualización:** [HM-T4b.2](f06-01-heather-room-contacts.md) y
[HM-T4b.3](f06-01-heather-room-preparation.md) completadas; HM-T4b queda cerrada
y sigue **HM-T4c.1**. El informe conserva la evidencia de contrato previa
a la implementación.

## Decisión numérica

Se conservan las reglas de [HM-T4a](f06-01-heather-room-profile.md): huella
175 + guarda 1, cajas cerradas, suelo erosionado abierto, validación del
estado inicial y bloqueo de toda la traslación. La salida copia los bits de
un extremo completo; bloquear es éxito del puerto y permite seguir animando.

El predicado se define sobre los valores exactos binary32, sin redondear
expansiones, cocientes ni posiciones locales. Un subnormal positivo menos
176 es estrictamente mayor que −176; en binary64 esa resta se redondea a
−176 y puede rechazar un estado libre. El vector `no_round_expansion`
distingue ambas reglas. La tangencia de esquina en t=81/137 y sus vecinos
también fijan la frontera cerrada sin epsilon ni tolerancia de penetración.

La implementación prevista compara intervalos racionales mediante productos
cruzados de enteros acotados: magnitudes de 192 bits para diferencias y
352 para productos bastan bajo ±1000000 unidades. Se demuestra la cota y
se comprueba la conversión exacta de normales/subnormales en las pruebas.
No se ha implementado aún la aritmética C++ ni medido su coste en ARM.
El presupuesto residente + scratch simultáneo sigue siendo ≤4096 bytes;
se exige contabilizar padding, preparación provisional y pila de helpers.

Se opera en mundo; el origen de escena es metadato y no se vuelve a sumar
al CLD. No se toca el perfil JSON seleccionado ni sus identidades. El
contrato permite contrastar los mismos bits host/ARM; no promete que la
trigonometría del planificador genere idénticos bits entre plataformas.

## Artefactos y alcance de la comprobación

- [Contrato HRC01–07](../../schemas/heather-room-contacts-v1.md): barrido,
  orden de validación, errores del núcleo y traducción al puerto existente,
  signo de cero, aliasing, repetición y memoria.
- [126 vectores propios](../../tests/fixtures/synthetic/heather-room-contacts-v1.json):
  **96 consultas y 30 preparaciones**, expectativas literales y centinela.
  Incluyen extremos libres con cruce, esquina, tangencia ±1 ULP, guarda,
  cajas línea/punto, consulta nula, origen grande, subnormales, Y/NaN/Inf,
  32/33 cajas, 4095/4096/4097 bytes y suma de presupuesto sin wrap.
- [Oráculo independiente](../../tests/python/helpers/heather_room_contact_oracle.py):
  `Fraction` e intersección con lados por orientación. No usa el algoritmo
  de intervalos previsto ni importa módulos de producción.
- [Pruebas de contrato](../../tests/python/test_heather_room_contacts_contract.py):
  literales, prioridad, simetría, permutación X/Z y de cajas, traslación,
  ordinales, bits de cero, cotas de enteros y controles elementales del oráculo.

Las geometrías son inventadas y los presupuestos de las fixtures son
sondas sintéticas, no tamaños medidos de objetos C++. No se leen ni exportan
recursos privados, ni se atribuye este resultado al recorrido real de hp34.
La atomicidad del runtime queda **especificada**, todavía sin ejecución
del núcleo/puerto: las pruebas actuales validan las expectativas y el oráculo.

## Validación local

- **264 pruebas de contrato** y **35 de políticas/regresión de repositorio**:
  299 aprobadas. JUnit: `build/heather-room/contacts-contract-pytest.xml`.
- Ruff de los dos módulos nuevos: lint y formato aprobados.
- Políticas de arquitectura, custodia y EARS: PASS; enlaces locales de los
  documentos cambiados y `git diff --check` verificados.
- Un pase intermedio de políticas detectó el enlace al presente informe
  mientras aún faltaba crearlo. Se completó el documento y se repitió el gate.
- No hay cambios de producción, CMake o CI en esta tarea. La batería Python
  existente descubre las pruebas nuevas; no se ejecutó CI remoto ni se
  compiló ARM, y no se generó un nuevo `.3dsx`.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/python/test_heather_room_contacts_contract.py tests/python/test_repository.py --junitxml=build/heather-room/contacts-contract-pytest.xml
rtk proxy .venv/bin/python -m ruff check tests/python/helpers/heather_room_contact_oracle.py tests/python/test_heather_room_contacts_contract.py
rtk proxy .venv/bin/python -m ruff format --check tests/python/helpers/heather_room_contact_oracle.py tests/python/test_heather_room_contacts_contract.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

## Continuación

**HM-T4b.2:** implementar consulta pura y adaptador `IMovementContacts`,
alimentar estos vectores al C++ y comprobar salida intacta/aliasing, escena
anterior ante fallos, repetición, memoria real y ausencia de heap. Integrar
fallos con HM-T3c/d, ejecutar Release/sanitizadores y gate ≥80/80 por módulo.
El contrato exacto se debe sostener también con compilación ARM; la medida
de tiempo y la navegación en consola siguen siendo aceptación posterior.

**HM-T4b.3:** preparar y cotejar fuentes privadas A/B, 32 cajas, suelo y
cinco tramos con el oráculo independiente. **HM-T4c/d/HM-T5:** integración,
build y prueba física. Se conservan C148 y HM-T2 pospuesto; no se reanuda
PCSX2 ni se declara resuelta la física original.
