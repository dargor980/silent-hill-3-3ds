# HM-T3c — Contactos y publicación conjunta con HL

Fecha: 2026-10-29. **Completada en el alcance nativo de inspección.**
Conecta la propuesta HM-T3b con una consulta de contactos y el núcleo HL,
preservando el estado completo ante errores. No modifica ni reanuda PCSX2,
no retoma la búsqueda pospuesta de pared 60 y no sustituye el build físico
aceptado `7250f427ffb9`.

## Contrato y comportamiento

Se amplía [HMN v1](../../schemas/heather-movement-native-v1.md) con HMN08–12.
El [puerto de contactos](../../engine/ports/include/sh3/ports/movement_contacts.hpp)
recibe posición anterior, posición propuesta y ordinal, todos en la base
original. Debe responder con XYZ aceptados, indisponibilidad o falta de
soporte. La consulta no consume eventos ni produce efectos irreversibles:
puede repetirse después de que una lectura de animación falle.

[InspectionActor](../../engine/application/inspection_actor.cpp) conserva
una instantánea publicada y otra provisional. Su orden de ejecución es:

1. Validar inicialización, intención, ticks y propuesta de movimiento.
2. Prevalidar la selección HL, sin leer muestras ni consultar contactos.
3. Consultar una vez el puerto y comprobar sus tres coordenadas.
4. Reconstruir la matriz de instancia con la posición aceptada y el nuevo yaw.
5. Evaluar HL sobre una copia; publicar movimiento, reloj, caché, pose y
   matriz solo al terminar correctamente.

Las coordenadas de salida del puerto empiezan como NaN: una respuesta
parcial o sin escritura falla. Cero es un resultado válido si se escriben
los tres componentes. Las correcciones Y se conservan; una posición
totalmente bloqueada puede seguir avanzando la animación elegida por la
intención. No se vuelve a sumar el desplazamiento solicitado a la salida
del resolvedor.

Las matrices de hueso siguen en espacio de modelo. La matriz de instancia
contiene la colocación mundial y se aplicará una vez por el consumidor.
Un helper puro compartido construye esa matriz sin consumir ticks, con
validación y salida intacta ante error. La prueba con raíz local no nula
comprueba que no se introduce traslación mundial en la pose HL.

El actor conserva copias de perfil y topología; lector y puerto tienen
vida mayor que él. Reset prepara espera, muestra cero y ordinal cero sin
consultar contactos: el llamador debe aportar una colocación de escena
previamente validada. Un reset fallido conserva también `ready()`.

Los callbacks observan la instantánea previa; intentos de reentrar en
`reset` o `step` reciben `busy`. La publicación es síncrona para un hilo
propietario, sin garantías de concurrencia entre hilos. No hay asignaciones
dinámicas por llamada. El objeto ocupa **27.888 bytes en los hosts probados**;
la comprobación estática de ≤32 KiB también pasa al compilar para ARM.

Las transiciones admitidas siguen siendo las de HL. Espera→correr directo
y un cambio de objetivo durante la mezcla devuelven sus errores originales
sin consulta de contactos ni avance parcial. En HM-T3d, el presentador
deberá conservar la intención pendiente y continuar el objetivo vigente
hasta poder cambiar; este coordinador no añade colas ni transiciones ocultas.

## Pruebas y pipelines

| Comprobación | Resultado |
| --- | --- |
| CTest seleccionado macOS Release | 12/12 |
| Mismos casos ASan/UBSan, `halt_on_error=1` | 12/12 |
| Mismos casos GCC 12.2 en Linux | 12/12 |
| Batería del coordinador | 4.598 rechazos instrumentados, 554 actualizaciones tras reintentos, 23.609 callbacks observados |
| Cobertura de `inspection_actor.cpp` | 58/58 líneas, 22/22 ramas, 6/6 funciones |
| Cobertura de `inspection_movement.cpp` con helper | 55/55 líneas, 42/42 ramas, 6/6 funciones |
| ARM GCC 16.1 Release | Dominio y aplicación compilados; objeto del coordinador ELF32 ARM EABI5, texto 1.124 bytes, datos/BSS 0 |
| Regresión del verificador del repositorio | 35 pruebas Python |
| Contratos, enlaces locales y formato del diff | PASS, 0 errores |

La batería [test_inspection_actor.cpp](../../tests/cpp/test_inspection_actor.cpp)
inyecta fallos en cada lectura de ambos canales durante estabilidad,
mezclas, salidas y vueltas de clip. Compara los reintentos con el núcleo HL
independiente y una referencia analítica de colocación. Incluye NaN/Inf,
límites, respuestas parciales, reentrada, reset fallido, bloqueo total,
corrección vertical, conservación de cero con signo y capacidad de 73 huesos.
Las instantáneas fallidas se comparan byte a byte y `new` está prohibido
durante las pruebas. Los demás casos cubren las regresiones de reloj,
pose, publicación HL, presentador, controles SDK simulados y colocación.

El [gate nuevo](../../gcovr-inspection-actor.cfg) exige al menos 80 % en
líneas y ramas por módulo; su ejecución y XML se incorporan a
[CI](../../.github/workflows/ci.yml), sin sustituir los gates previos.
Se usa CMake/CTest real, flags estrictos y datos sintéticos. CI remota
no ejecutada en esta entrega.

GCC detectó dos problemas en las pruebas: una copia innecesaria en un
bucle nuevo y un callback existente de `test_character_world.cpp` que
carecía de `noexcept`, necesario para el tipo de `ferror` en glibc. Se
corrigieron sin relajar `-Werror` ni cambiar el runtime de archivos.
Los dos intentos fallidos y el tercero aprobado se conservan.

Evidencia local ignorada: `build/heather-movement/actor-v1/` contiene
comando/script del contenedor sin red, logs, XML de GCC/cobertura, resúmenes,
bibliotecas ARM, comandos de compilación y cabecera/tamaño del objeto.
Los XML host están en `build/host-{release,sanitize}/actor-tests.xml`.

```sh
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --target test_inspection_actor test_inspection_movement test_locomotion_clock test_locomotion_pose test_locomotion_update test_locomotion_probe test_ctr_locomotion_controls test_character_world --parallel 2
rtk proxy ctest --preset host-release -R '^(inspection_(actor|movement)|locomotion_(clock|pose|update|probe|ctr_controls)(_oracle)?|character_world(_wire)?)$' --output-junit actor-tests.xml
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --target test_inspection_actor test_inspection_movement test_locomotion_clock test_locomotion_pose test_locomotion_update test_locomotion_probe test_ctr_locomotion_controls test_character_world --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(inspection_(actor|movement)|locomotion_(clock|pose|update|probe|ctr_controls)(_oracle)?|character_world(_wire)?)$' --output-junit actor-tests.xml
rtk proxy .venv/bin/python -m pytest -q tests/python/test_repository.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
rtk proxy git diff --check
```

## Alcance pendiente

La conexión se verifica con resolvedores sintéticos. **Todavía no hay un
adaptador de colisión de habitación ni reproducción general del solver
PS2**; una posición aceptada finita no acredita alcanzabilidad física.
Geometría, radio/cápsula, suelo y formas soportadas pertenecen al adaptador
concreto posterior. No se añade un resolvedor de producción que acepte todo.

**Actualización:** [HM-T3d completada](f06-01-heather-movement-controls.md).
La [selección HM-T4a](f06-01-heather-room-profile.md) y el
[contrato HM-T4b.1](f06-01-heather-room-contacts-contract.md) están completados;
[HM-T4b.2](f06-01-heather-room-contacts.md) completa núcleo y puerto.
Sigue HM-T4b.3. Se conserva el alcance previsto al cerrar
HM-T3c: **HM-T3d**, intención pendiente, controles, reloj de pasos fijos,
pausa/paso/reinicio, suspensión sin recuperación de tiempo y replay a
distintas cadencias. HM-T4 integrará el adaptador de escena y la colocación
compartida; HM-T5 validará el nuevo build físicamente. Esta entrega compila
bibliotecas ARM, pero no genera un `.3dsx` nuevo ni acredita ejecución 2DS XL.
