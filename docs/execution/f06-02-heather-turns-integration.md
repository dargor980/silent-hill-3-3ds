# F06.02/heather-turns — HG-T4.3: acciones, contactos y ciclo de vida

2026-10-30. **HG-T4.3 completada.** Perfil 2 integrado con actor, controlador y bucle HM.
Alcance: HGT05–07/10/12 del [contrato HG-T3](../../schemas/heather-turns-native-v1.md).
El cierre de pico/pila y ARM corresponde a HG-T4.4; HG-T5 prepara la entrega.
Se conserva el build de consola `c3aae59d1a70`. Las mediciones y pruebas
adicionales de HM-T5, y la investigación de pared 60, siguen aplazadas.

## Integración

`InspectionAction` distingue espera, caminar, correr, giro derecho e izquierdo.
El actor deriva de esa acción el clip y la clase de movimiento; no expone
un par arbitrario de clip/movimiento. `InspectionTurn` conserva el yaw mundial
de la entrada actual, incluso si la animación termina una mezcla en dirección
contraria. La entrada anterior del actor sigue disponible: idle más yaw usa
101. El controlador solo habilita animaciones 107/108 para el perfil 2.

El controlador conserva la última acción completa y reemplaza el objetivo
incluso con cero tiempo transcurrido. Soltar botones cancela el objetivo previo.
Una mezcla termina antes de solicitar otro arco; derecha↔izquierda y
marcha↔giro pasan por espera, y espera→correr pasa por caminar. El siguiente
salto empieza en un paso de simulación posterior. Avanzar tiene prioridad
para seleccionar animación; izquierda/derecha opuestas cancelan yaw y
arriba/abajo opuestos cancelan avance. B solo no inicia carrera.

La nueva entrada `step_action` comparte la transacción existente del actor:
movimiento validado → selección → contactos → instancia → ambas poses de
canal → publicación completa. Los giros solicitan traslación cero y consultan
igualmente los contactos. La instancia mundial se aplica una sola vez después
de la pose local. No se modifica el algoritmo de contactos, los materiales,
el orden de dibujo ni el filtro corregido de R.

El cargador existente transmite `rig.profile` a `RoomLoop`; no necesita una
rama alternativa para el perfil 2. La prueba de runtime carga un SRI2 sintético
independiente de 78 muestras y el escenario de 31 formas/32 cajas con
materiales de formato original y píxeles inventados. Recorre espera, caminar, correr y ambos
giros a 25/60/143 Hz, incluidos contactos, interrupciones y render real contra
dobles del SDK. Comprueba igualdad final de pose/movimiento entre cadencias,
inmutabilidad de geometría estática y ausencia de asignaciones C++ por cuadro.
Esto valida la ruta nativa; no constituye una observación en GPU o consola.

## Vectores, publicación y fallos

El JSON de HG-T3 permanece intacto, SHA-256
`433811f29a1687bb5bd357d73234f7290a0cbef407df18a6dba1575c62c833ae`.
El adaptador `tests/heather_turns_integration_oracle.py` entrega sus entradas
al controlador C++ y coteja **32 combinaciones, 25 rutas y 36 filas de replay**:
destinos, modo, contador, beta, objetivo pendiente, ordinal y yaw inmediato.
Se conservan además los vectores de núcleo de HG-T4.1 y las regresiones HL/HM.

El nuevo ensayo de integración inyecta **156 fallos y 156 reintentos** en
los cuatro arcos espera↔giro, en entrada, continuación y salida. Falla cada
lectura requerida de un esqueleto jerárquico de dos canales, o entrega NaN o
cuaternión nulo; prueba también cinco errores de contacto. En cada rechazo
la instantánea completa permanece idéntica byte a byte. Los callbacks ven
la instantánea anterior y las reentradas de paso/reinicio se rechazan.
Cada reintento coincide con una ejecución limpia.

Se comprueban acción/dirección/ticks inválidos, arco no permitido, interrupción
de mezcla, perfil legado, reinicio fallido y recuperación tras error de
simulación o render. Un fallo en el segundo o tercer paso del lote conserva
las publicaciones completas anteriores. Las pruebas de reemplazo a 0/1 µs
verifican que una intención cancelada no reaparece después de la mezcla.
El puerto real `RoomMovementContacts` verifica bloqueo de traslación ante una
pared, giro sin desplazamiento y separación de pose local/instancia mundial.

## Pausa, R, reinicio y HOME/tapa

Se ejecuta el adaptador `MovementControls` de producción contra HID/APT de
prueba en seis situaciones: derecha/izquierda durante entrada con caché,
giro estable y retorno con caché. Se prueban RUNNING y PAUSED, HOME y tapa
por separado y superpuestos, con intervalos de diez segundos. La instantánea
permanece intacta, se limpian deuda/objetivo, se conserva la pausa anterior
y se exige liberación; tampoco se acumula el tiempo de la muestra neutra.

En PAUSED, una pulsación estable de R produce un paso y mantenerla no repite,
incluso con flancos `down` reiterados. Diez segundos sin botones no cambian
la instantánea. L restaura 101/Q12=0/Step=0, conserva PAUSED y descarta caché
y objetivo; A permite continuar y START tiene prioridad sobre A/L/R.
También se conservan las pruebas HM de señales espurias de R y las trazas
del HUD a 25/60/143 Hz. Son pruebas host con dobles del SDK; no reabren HM-T5.

## Validación y límites

Clang Debug, ASan/UBSan y GCC 12.2: **27/27 CTest** en cada configuración.
Python: **614 pruebas** del contrato, reconstrucción y runtime de habitación,
más **19** del observador de ciclo tras corregir su formato preexistente.
Ruff y formato Python pasan en el alcance completo de CI (344 archivos);
también el formato de las nuevas interfaces C++/ensayo de integración,
el control del repositorio y `git diff --check`. GCC detectó una copia
innecesaria en el bucle del ensayo; se corrigió y se repitieron sus dos casos
en Clang/ASan, además de los 27 GCC. No se ejecuta CI remoto.

Pasan **16 gates individuales ≥80 % de líneas y ramas**, con GCC 12.2/gcovr
en la imagen fijada, sin red. Se reutilizó el árbol de cobertura SRI2 y se
borraron sus contadores antes de las 27 pruebas; los informes anteriores
se conservaron. Estos gates del adaptador prueban dobles SDK, no la plataforma física.

| Unidad | Líneas | Ramas |
|---|---:|---:|
| ctr-movement-controls | 99/99 — 100.0 % | 83/84 — 98.8 % |
| inspection-action | 22/22 — 100.0 % | 10/10 — 100.0 % |
| inspection-actor | 65/65 — 100.0 % | 26/26 — 100.0 % |
| inspection-locomotion-domain | 28/28 — 100.0 % | 38/38 — 100.0 % |
| inspection-locomotion-reader | 192/192 — 100.0 % | 166/168 — 98.8 % |
| inspection-movement | 55/55 — 100.0 % | 42/42 — 100.0 % |
| locomotion-clock | 111/111 — 100.0 % | 138/138 — 100.0 % |
| locomotion-pose | 180/183 — 98.4 % | 197/220 — 89.5 % |
| locomotion-probe | 123/146 — 84.2 % | 103/119 — 86.6 % |
| locomotion-update | 45/45 — 100.0 % | 42/42 — 100.0 % |
| movement-controller | 129/130 — 99.2 % | 109/113 — 96.5 % |
| room-loop | 54/54 — 100.0 % | 63/68 — 92.6 % |
| room-main | 123/126 — 97.6 % | 109/127 — 85.8 % |
| room-movement-contacts | 7/7 — 100.0 % | 4/4 — 100.0 % |
| room-renderer | 157/158 — 99.4 % | 109/114 — 95.6 % |
| room-runtime-reader | 125/130 — 96.2 % | 109/126 — 86.5 % |

El ensayo falla ante cualquier `new/new[]` durante las transacciones nuevas;
el runtime mantiene su guardia de asignaciones. Tamaños host observados:
actor **27960**, controlador **28024**, bucle **28072 bytes**. No representan
el pico total del proceso ni medidas ARM. HG-T4.4 deberá cerrar ese presupuesto
con los recursos reales de HG-T4.2, la escena y la plataforma.

JUnit y cobertura: `build/heather-turns-integration/`. Informe local agregado:
`reports/local/heather-turns-integration-v1.json`.
SHA-256: `946121e882de114b2f2b6ca1a98f327d8ff0b9161807506f132ed7aa7a0b5477`.

Docker volvió a bloquearse con errores de escritura del disco virtual.
Se eliminaron únicamente objetos de compilación regenerables, conservando
ejecutables, informes y recursos. El reinicio autorizado recuperó Docker y
se verificó `test.postgres12` activo; la ejecución final GCC/cobertura terminó
correctamente. Inventario de limpieza: `build/heather-turns-integration/object-cleanup.json`.

**Siguiente unidad: HG-T4.4**, almacenamiento, pico/pila, gates finales y
compilación ARM antes del empaquetado HG-T5. F06.02 global y G04/G05 siguen
abiertos; HM-T5 adicional permanece aplazada.
