# HM-T3d — Controles, tiempo fijo y suspensión

Fecha: 2026-10-29. **Completada para el perfil nativo de inspección HMN v1.**
El controlador conecta la intención de movimiento con el actor y la animación
HL. El adaptador 3DS traduce HID, convierte el reloj ARM11 y gestiona los hooks
de tapa, HOME y salida. Su conexión al bucle de la habitación corresponde a
HM-T4; esta entrega no genera un `.3dsx` ni cambia el build físico aceptado
`7250f427ffb9`.

## Contrato y separación de responsabilidades

El [contrato HMN13–19](../../schemas/heather-movement-native-v1.md) fija las
reglas antes de la implementación. Se mantienen las interfaces de contactos
y lectura de animación de [HM-T3c](f06-01-heather-contact-animation.md).

- [MovementController](../../engine/application/movement_controller.cpp):
  estado de sesión, intención pendiente, tiempo y comandos; depende del actor
  y de puertos, sin SDK ni renderer.
- [MovementControls](../../engine/platform/3ds/movement_controls.cpp):
  traducción HID y reloj, registro/liberación RAII de `aptHook`; no resuelve
  contactos ni evalúa poses.
- `InspectionActor` conserva la transacción por paso: propuesta, contactos,
  pose HL y matriz de instancia se publican conjuntamente.

El controlador ocupa **27.944 bytes en host**, sin asignaciones dinámicas.
Un `static_assert` comprueba que controlador y adaptador juntos caben en
32 KiB, también durante la compilación ARM. El dueño del bucle debe mantener
un solo hilo y hacer vivir al controlador más que al adaptador. Las llamadas
reentrantes desde los puertos no avanzan ni cambian la sesión.

## Comportamiento implementado

Cada paso consume **40.000 µs**, equivalentes a los dos ticks del perfil HMN.
Se conserva el resto y se admiten como máximo tres pasos por muestra. Un
intervalo mayor de 120.000 µs se descarta completo junto con el resto; no
produce recuperación posterior. El adaptador conserva la fracción de la
conversión ARM11→µs para evitar deriva por truncamiento. El reloj retrocedido
y los intervalos excesivos se rechazan sin desbordamiento.

La última intención sustituye a la pendiente durante una mezcla HL. Se sigue
actualizando el objetivo vigente hasta que termina; desde espera, pedir
carrera recorre explícitamente espera→caminar→correr. El núcleo HL conserva
su rechazo a espera→correr directo. **El movimiento vigente continúa durante
esa mezcla, por lo que una petición de parada puede demorarse hasta su fin.**
Esta política pertenece al visor de inspección; no acredita el comportamiento
final de controles ni la física original de SH3.

| Control del futuro visor de habitación | Acción |
| --- | --- |
| Cruceta ↑ | Caminar mientras se mantiene |
| ↑ + B | Solicitar carrera |
| Cruceta ← / → | Girar; ambas juntas se cancelan |
| ↑ + ↓ | Cancelar intención de avance; ↓ sola no retrocede |
| A, flanco de pulsación | Pausar/reanudar |
| R, flanco de pulsación | Un paso mientras está pausado |
| L, flanco de pulsación | Reiniciar en el punto de entrada validado |
| START | Solicitar salida, con prioridad sobre todos los comandos |
| Tapa / HOME | Suspender y recuperar el estado previo de pausa |

La prioridad restante es guarda de liberación → pausa → reinicio → paso →
avance temporal. Los comandos consumen la muestra sin acumular su tiempo.
Al iniciar, cambiar pausa, reiniciar, fallar o volver de suspensión se exige
una muestra con todos los botones sueltos; esa muestra también descarta el
tiempo. Los botones aún no mapeados cuentan para esta guarda. Los hooks
duplicados no reinician el reloj ni alteran la pausa previa. La salida es
terminal.

Un error detiene el lote, limpia el tiempo y la solicitud pendiente, y deja
la sesión pausada para un reintento explícito. Si el segundo paso falla, el
primero ya publicado se conserva; el paso fallido no modifica la instantánea.
La garantía atómica es por paso, no por lote completo.

## Validación

| Comprobación | Resultado |
| --- | --- |
| CTest seleccionado, host Release | 14/14; 0 fallos |
| Mismo conjunto con ASan/UBSan | 14/14; 0 fallos |
| Mismo conjunto, GCC con cobertura | 14/14; 0 fallos |
| `movement_controller.cpp` | 97/97 líneas; 87/88 ramas (98,9 %) |
| `movement_controls.cpp` | 42/42 líneas; 30/34 ramas (88,2 %) |
| Regresión `inspection_actor.cpp` | 58/58 líneas; 22/22 ramas |
| Regresión `inspection_movement.cpp` | 55/55 líneas; 42/42 ramas |
| Biblioteca `sh3_movement_controls` y dependencias | Compilación ARM correcta |
| Pruebas Python del repositorio | 35/35 |
| Comprobador de repositorio / `git diff --check` | 0 errores |

Los dos gates nuevos exigen **≥80 % de líneas y ramas por archivo** en CI,
sin rebajar los gates previos. Se publican sus XML como artefactos del job.
La ejecución de GCC/gcovr y ARM fue local; no se ejecutó GitHub Actions remoto.

[Pruebas del controlador](../../tests/cpp/test_movement_controller.cpp):
umbrales 39.999/40.000/120.000/120.001 µs, límite entero, comandos simultáneos,
solicitudes sustituidas/canceladas, puente a carrera, fallos de contactos y
lector, reinicio fallido, reintento, liberación de botones y reentrada.
El replay combina cinco fases y 150 pasos; compara movimiento, matriz,
reloj HL, caché y poses con intervalos regulares e irregulares, incluyendo
pausas y suspensión. La equivalencia presupone la misma intención por tick;
no reconstruye cambios HID ocurridos entre muestras.

[Pruebas del adaptador](../../tests/cpp/test_ctr_movement_controls.cpp):
compilan el código de producción contra dobles SDK, separan botones retenidos
y flancos, verifican ambos pares de hooks y la liberación RAII. Dos segundos
producen exactamente **50 pasos a 25, 60 y 143 muestras HID por segundo**.
También cubren reloj retrocedido, saltos temporales, salida y fallo del actor.
Estos dobles no acreditan una ejecución física de tapa/HOME de este adaptador.

El objeto ARM del adaptador contiene 920 bytes de texto; el controlador,
2.192 bytes; ambos tienen cero bytes de datos/BSS propios. Estas cifras son
de objetos compilados, no tamaño del ejecutable ni memoria total de la escena.

Evidencia local ignorada por Git: `build/heather-movement/controller-v1/`
contiene el log, receta y argumentos del contenedor, `gcc-tests.xml`, cuatro
resúmenes y XML de cobertura, bibliotecas ARM y cabeceras/tamaños de objetos.
Los resultados host están en `build/host-{release,sanitize}/controller-tests.xml`.
La imagen devkitPro queda fijada por `toolchains/devkitpro-image.txt`; el
contenedor se ejecutó sin red, con fuentes de solo lectura y salida acotada.

Selección reproducible, después de compilar los targets correspondientes:

```sh
rtk proxy ctest --preset host-release -R '^(movement_(controller|ctr_controls)|inspection_(actor|movement)|locomotion_(clock|pose|update|probe|ctr_controls)(_oracle)?|character_world(_wire)?)$'
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize -R '^(movement_(controller|ctr_controls)|inspection_(actor|movement)|locomotion_(clock|pose|update|probe|ctr_controls)(_oracle)?|character_world(_wire)?)$'
```

## Siguiente tarea y límites

**Actualización:** [HM-T4a](f06-01-heather-room-profile.md) y
[HM-T4b.1](f06-01-heather-room-contacts-contract.md) completadas; sigue
HM-T4b.3 tras [completar núcleo y puerto HM-T4b.2](f06-01-heather-room-contacts.md).
Se conserva el alcance previsto:
**HM-T4a:** seleccionar el primer mapa y fijar geometría, materiales, formas
admitidas, punto de entrada, unidades comunes y presupuesto. Después se
implementará su adaptador concreto de contactos y se conectarán actor,
controles y renderer en el mismo bucle, antes de preparar el build HM-T5.

Los contactos usados aquí son sintéticos. No hay un resolvedor de producción
que acepte cualquier posición ni una habitación navegable acreditada. Se
mantienen pendientes las variantes de contacto y autoridad general del
movimiento PS2 de HM-T2. La búsqueda pospuesta de pared 60/hueco 14/60 queda
preservada hasta C148, sin reanudar PCSX2.

## Corrección posterior HM-T5

La política original de descartar intervalos >120 ms podía impedir todo
avance cuando el render superaba ese umbral. El seguimiento
[HM-T5](f06-01-heather-room-fault.md) la sustituye por un máximo de tres
pasos para intervalos hasta 1 s, sin deuda pendiente; >1 s sigue siendo
una discontinuidad. Se conserva arriba la evidencia y el contrato original
de HM-T3c para no atribuirle una prueba posterior.
