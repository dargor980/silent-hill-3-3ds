# HM-T4b.2 — Núcleo exacto y puerto de contactos

2026-10-29. **HM-T4b.2 completada** conforme a
[HRC v1](../../schemas/heather-room-contacts-v1.md). Se implementan el núcleo
C++ y el adaptador `IMovementContacts`, con vectores, atomicidad, memoria,
sanitizadores, cobertura y compilación ARM comprobados.
**Actualización:** [HM-T4b.3 completada](f06-01-heather-room-preparation.md),
con preparación y cotejo privado A/B. Sigue **HM-T4c.1**. La habitación no está
integrada y no se publica un nuevo `.3dsx`.

## Implementación

- [RoomContactScene](../../engine/domain/room_contacts.cpp) posee los datos
  validados. La preparación comprueba perfil, capacidad, presupuesto y toda
  la geometría antes de publicar; un fallo conserva cada byte anterior.
  Los arrays de entrada pueden liberarse o cambiar después de preparar.
- [RoomMovementContacts](../../engine/platform/common/room_movement_contacts.cpp)
  posee una escena y traduce `ok/unavailable/otros` a los tres estados del
  puerto existente. No guarda el último contacto ni consume el ordinal.
- El barrido usa intervalos racionales cerrados. Interpreta bits binary32
  sin aritmética flotante geométrica, expande exactamente 176 unidades y
  conserva el suelo abierto. Valida todos los solapamientos iniciales incluso
  después de encontrar una barrera que bloquea el destino.
- Las magnitudes usan seis limbs uint32. La multiplicación completa 6×6 usa
  doce limbs por simplicidad; el último es cero por la cota `<2^340` de HRC.
  No hay truncación, epsilon, división flotante ni dependencia de `__int128`.
- El resolvedor copia XYZ completos desde `from` o `requested`, preservando
  bits y ceros con signo. Ambos alias son seguros; los errores no escriben
  salida. No hay heap, I/O, SDK ni recursos privados en el núcleo.

El [API](../../engine/domain/include/sh3/domain/room_contacts.hpp) recibe
geometría mundial, perfil tipado, radio/guarda y un span de 0–32 cajas.
`RoomContactMemory` admite reservas contables mayores; nunca permite reducir
las cotas incorporadas. La suma se verifica por resta, sin wrap de `size_t`.
Un puntero nulo con conteo no nulo es `invalid_geometry`; un conteo >32 se
rechaza antes de leer el puntero. Los requisitos específicos de los 34
registros hp34 pertenecen al preparador HM-T4b.3.

Para validar el spawn, el dueño de la escena consulta `from=requested=spawn`
antes de inicializar el actor, como exige HMN11. El adaptador rechaza un
spawn sobre la frontera. `InspectionActor::reset` conserva su contrato;
el bucle de habitación incorporará esta prevalidación durante HM-T4c.

## Vectores, transacción y regresiones

[Puente de oráculo](../../tests/room_contacts_oracle.py): **894 casos**,
los **126 literales fijados** (96 consultas + 30 preparaciones) y **768
consultas generadas con semilla fija**. Las expectativas usan el oráculo
racional por intersección con lados, independiente del barrido C++.
Se transmiten bits uint32, incluidos subnormales y NaN señalizantes; se
comparan estados y bits XYZ con tolerancia cero.

El [ejecutable de prueba](../../tests/cpp/test_room_contacts.cpp) verifica
núcleo y puerto, centinela de salida, repetición, ambos alias, ausencia de
mutaciones al consultar y escena anterior utilizable tras preparación fallida.
También comprueba entrada nula, capacidad extrema, propiedad de buffers y
un solapamiento inicial en una caja posterior a otra que ya bloquea.
`operator new/new[]` aborta si se invoca durante las operaciones comprobadas.
El objeto ARM del núcleo solo importa `memcpy/memset`, sin asignadores.

Con el controlador y animación reales, una pared conserva la posición mientras
avanzan giro, ordinal y mezcla HL; la raíz sigue en espacio de modelo. Un
fallo posterior del lector conserva la instantánea byte a byte y pausa.
Una escena con Y incompatible produce `contacts_unsupported`, sin leer
animación ni publicar estado mixto; una escena no preparada produce
`contacts_unavailable`. Ambos caminos y la recuperación explícita se prueban.

| Comprobación local | Resultado |
| --- | --- |
| CTest de contactos + movimiento/actor/HL/colocación, Release | 16/16 |
| Mismo conjunto, ASan/UBSan | 16/16 |
| Mismo conjunto, GCC con cobertura | 16/16 |
| Gate de pila Release, separado | 1/1 |
| `room_contacts.cpp` | 154/154 líneas; 187/194 ramas (96,4 %) |
| `room_movement_contacts.cpp` | 7/7 líneas; 4/4 ramas |
| Python de contrato/repositorio + controles del gate de memoria | 299 + 12 aprobadas |
| Bibliotecas dominio, aplicación y adaptadores con devkitARM | Compiladas |

CI incorpora ambos gates ≥80/80, sus XML, el contraste de vectores, lint y
el gate de pila en host Release y ARM. Se preservan los gates anteriores.
Se ejecutó el contenedor local fijado, sin red, con fuentes de solo lectura;
no se ejecutó GitHub Actions remoto ni código ARM en consola.

## Memoria comprobada

La escena ocupa **552 bytes**; el adaptador, **560 en host y 556 en ARM**.
La reserva residente es **576 bytes**, incluido padding. Se reservan **2560
bytes de scratch/pila**: **3136 bytes conjuntos**, bajo el límite de 4096.
La preparación provisional vive en la pila y está incluida en las medidas.

El [gate](../../tests/room_contacts_stack.py) suma conservadoramente **todos**
los frames emitidos en ambos módulos, incluso los que nunca coinciden, y
añade 128 bytes para las rutinas externas de copia/relleno. Rechaza informes
vacíos, ambiguos o dinámicos. GCC verifica además que el grafo alcanzable
desde preparar/resolver no tiene recursión, llamadas indirectas ni externos
distintos de `memcpy/memset`; Clang aporta `.su` y comparte el código cuyo
grafo se verifica con GCC. Son cotas para los builds **Release optimizados**;
los frames añadidos por sanitizadores no representan memoria del build 3DS.

| Compilador/plataforma | Suma de frames | + reserva externa | + residente 576 |
| --- | ---: | ---: | ---: |
| Clang host | 2368 | 2496 | 3072 |
| GCC host en contenedor | 2240 | 2368 | 2944 |
| devkitARM | 1988 | 2116 | 2692 |

Se inspeccionaron los objetos `memcpy` y `memset` del multilib ARM fijado:
son hojas sin llamadas, con máximos de pila 16 y 12 bytes respectivamente;
caben en la reserva de 128. La eliminación virtual del adaptador no es
alcanzable desde preparar/resolver y no forma parte de una consulta.
No hay buffers estáticos mutables: objetos ARM con datos/BSS propios cero;
texto del núcleo 3932 bytes y del adaptador 272. Estas cifras no son el
tamaño del ejecutable ni una medición de rendimiento físico.

## Evidencia reproducible y siguiente tarea

`build/heather-room/contacts-v1/` conserva receta y argumentos del contenedor,
JUnit GCC/Python, cobertura JSON/XML, bibliotecas ARM, comandos de compilación,
cabeceras/tamaños/imports, layout ARM, informes `.su/.ci`, desensamblado de
las rutinas de memoria y `memory-audit.json`. Los dos JUnit host están en
`build/host-{release,sanitize}/room-contacts-tests.xml`; el gate separado en
`build/host-release/room-contacts-stack.xml`. Solo son evidencia local ignorada.

```sh
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_room_contacts --parallel 2
rtk proxy ctest --preset host-release -R '^room_contacts' --output-on-failure
rtk proxy .venv/bin/python tests/room_contacts_stack.py build/heather-room/contacts-v1/arm-stack
rtk proxy .venv/bin/python -m pytest -q tests/python/test_heather_room_contacts_contract.py tests/python/test_room_contacts_stack.py tests/python/test_repository.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

**HM-T4b.3**, completada después de esta entrega, verifica el CLD completo,
sus 32 cajas/suelo y recorrido A/B con fuentes fijadas y el oráculo separado.
HM-T4c conectará bucle, cámara y
render; HM-T4d/HM-T5 entregarán y validarán físicamente. Se conserva C148 y
la investigación HM-T2 pospuesta. No se atribuye este solver nativo a PS2.
