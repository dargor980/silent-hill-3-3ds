# Ejecutor de diagnóstico — DW v1

Historia: como investigador, necesito presupuestar la preparación y el inventario
sin ejecutarlos en el hilo CPU, y distinguir cancelación solicitada de cierre
efectivamente confirmado. Un diagnóstico sigue siendo una observación histórica.

## Requisitos EARS

- **DW01:** CUANDO se acepte la primera solicitud, el ejecutor DEBERÁ fijar un
  deadline monotónico de 5 s antes de crear el hilo, la fábrica o los recursos.
  CUANDO se acepte una revalidación, DEBERÁ fijar 2 s. Preparación, lectura, hash,
  serialización y recogida del resultado DEBERÁN compartir ese mismo plazo.
- **DW02:** MIENTRAS haya una operación pendiente, el ejecutor DEBERÁ admitir
  solo un trabajo y un resultado. CUANDO se repita/cambie desafío o secuencia,
  haya solapamiento o una solicitud inválida, DEBERÁ invalidar la sesión sin
  reintentar ni cambiar de perfil. Una nueva sesión requiere otra instancia.
- **DW03:** CUANDO se prepare/muestree el proveedor, DEBERÁ hacerlo en un hilo
  propio. La fábrica, el trabajo, sus descriptores y su destrucción DEBERÁN
  pertenecer a ese hilo; el hilo CPU solo podrá enviar, recoger o invalidar.
  El reloj y la configuración inmutable DEBERÁN sobrevivir al ejecutor.
- **DW04:** CUANDO expire el plazo, retroceda el reloj, se cancele, se pierda el
  peer o cambie alguna época esperada, DEBERÁ conservar la primera causa, borrar
  el resultado pendiente e impedir toda publicación posterior. Volver a la época
  anterior SHALL NOT reactivar la sesión. El proveedor DEBERÁ poder consultar
  cancelación y tiempo restante durante cada fase.
- **DW05:** CUANDO se reciba una muestra, DEBERÁ validar PD v1, política local,
  épocas y continuidad de identidad antes de encolarla; DEBERÁ comprobar otra
  vez el deadline al recogerla. Los errores de proveedor y excepciones DEBERÁN
  terminar la sesión sin publicar payload parcial.
- **DW06:** CUANDO se solicite cancelar, SHALL NOT cerrar desde otro hilo los
  descriptores aún usados. El ejecutor DEBERÁ retener objetos hasta finalizar el
  trabajo, cerrar y destruir en su hilo, y unir el hilo. Una espera de cierre
  vencida DEBERÁ informar pendiente; SHALL NOT fingir cierre ni separar el hilo.
  La destrucción/unión bloqueante DEBERÁ realizarse fuera del hilo CPU.
- **DW07:** CUANDO un adaptador no coopere o una syscall no retorne, el ejecutor
  DEBERÁ rechazar el resultado por tiempo/cancelación y mantener el cierre como
  no confirmado. SHALL NOT prometer terminar forzosamente un hilo C++ con
  seguridad. La integración nativa DEBERÁ instrumentar sus fases y comprobar el
  cierre antes de considerarse terminada.
- **DW08:** CUANDO se presente el resultado, DEBERÁ incluir el informe de hechos
  AP desconocidos/violados. Incluso todos satisfechos SHALL NOT habilitar captura;
  exclusión CPU/PINE/VU/GS, JIT/caché/DMA/escritores y lifecycle requieren sus
  guardias runtime vigentes. Sin VM los hechos DEBERÁN ser desconocidos.
- **DW09:** CUANDO se valide, DEBERÁ probar plazos exactos, acumulación entre
  fases, revalidación, publicación tardía, cancelación concurrente, pérdida del
  peer, cambio y regreso de épocas, fallo de cierre y destrucción retenida.
  DEBERÁ distinguir dobles de la integración PCSX2 y mantener pruebas en CI.

## Diseño y SOLID

`DiagnosticClock` aporta tiempo monotónico. `DiagnosticBudget` da al proveedor
un punto cooperativo de comprobación y tiempo restante. `DiagnosticWorkFactory`
solo contiene configuración al entregarse: crear recursos o consultar el sistema
antes de `create()` violaría DW01. `DiagnosticWork` prepara, muestrea y cierra;
su resultado tipado contiene inventario, hechos y épocas, sin capacidades.

`DiagnosticWorker` posee fábrica, trabajo, hilo y buzón de tamaño uno. Un mutex
serializa publicación e invalidación; ninguna llamada externa ni IO se ejecuta
bajo ese mutex salvo el reloj confiable, rápido y no reentrante. El proveedor
recibe el presupuesto para comprobarlo entre operaciones; sus resultados solo
se copian al buzón tras validación. La recogida vuelve a comprobar el plazo.

El cierre tiene dos pruebas distintas: el hilo terminó y `close()` confirmó la
liberación. Un error de cierre no oculta la primera causa. La API de espera usa
el reloj real de `steady_clock`, separado del reloj inyectable de presupuesto.
Si vence, el dueño conserva el ejecutor y puede esperar de nuevo. El destructor
cancela y une sin `detach`; puede esperar si el proveedor incumple cooperación.
No se llama desde el propio trabajador ni bajo guardias del emulador.

## Tareas detalladas

- [x] **DW-T1 / PT-T5c.1:** implementar núcleo y puertos, presupuesto único,
  buzón, correlación, continuidad, invalidación y cierre con reconocimiento.
  Probar trabajo real en otro hilo con dobles controlables de fases/tiempo,
  sanitizadores, cobertura y controles de regresión; incorporar a CMake/CI.
- [x] **DW-T2 / PT-T5c.2:** instrumentar adaptadores nativos de preparación,
  lectura/hash y canal con el presupuesto; componer la sonda privada PCSX2 con
  este ejecutor. Probar stalls por fase, desconexión y cierre confirmado sin VM.
  No cerrar descriptores prestados desde un hilo de cancelación.
- [ ] **DW-T3 / PT-T5c.3:** unir al coordinador runtime y sus guardias de
  lifecycle/exclusión/escritores. Probar cambio de VM y regreso, gates ausentes,
  configuración JIT/DMA y cancelación retenida. Evaluar captura por separado;
  DW-T1 y el diagnóstico sin VM no completan PT-T5c/PS-T4/PD-T5.

## Integración nativa verificada en SRC108

[El contrato NW](native-diagnostic-work-v1.md) desglosa DW-T2: **NW-T1 / DW-T2a**
y **NW-T2 / DW-T2b** están completos para inventario nativo y sonda privada sin
VM. **NW-T3 / DW-T2c sigue abierto**: el presupuesto total debe incluir el canal,
escrituras parciales, backpressure, desconexión y descarte tardío. DW-T2 no se
marca completo por la sonda sin transporte. DW-T3 conserva las guardias runtime.

SRC109 completa únicamente **NW-T3a**, plazo del consumidor desde comprobación
del peer hasta admisión, con cancelación señalada al dueño. El productor DW aún
desactiva el presupuesto al recoger; **NW-T3b** debe mantenerlo durante el envío.
La sonda conjunta **NW-T3c** sigue pendiente, por lo que DW-T2 permanece abierto.

SRC110 añade **WD-T1 / NW-T3b**: el modo `submit_until` conserva el deadline
durante entrega y exige confirmación. No se mezcla con la recogida anterior.
El canal pertenece a su dueño de IO y se cierra por separado de DW. **NW-T3c**
debe comprobar la composición privada antes de cerrar DW-T2.

SRC111 completa **DW-T2 / PT-T5c.2** con la composición privada BC/DW/inventario/
canal: 20 casos finales y 21 procesos PCSX2 sin VM. El rechazo previo por cambio
del loader se conserva. **DW-T3 / PT-T5c.3 sigue pendiente**: esta evidencia
no habilita captura ni certifica guardias runtime.


SRC112 completa **RB-T1 / DW-T3a**: añade el puerto opcional `DiagnosticValidity`,
un snapshot runtime revocable y una composición que comparte su validador.
DW comprueba la revocación también durante esperas internas, con sondeos nominales
de 20 ms incluso ocioso. Un hijo bloqueado conserva limpieza pendiente.
Las pruebas usan hilos y núcleos de coordinador reales con datos locales;
**DW-T3 sigue abierto** hasta RB-T2 (adaptador privado y hooks) y RB-T3
(candidato enlazado con VM). Véase [RB v1](runtime-diagnostic-binding-v1.md).

## Progreso de integración: SRC113

SRC113 completa **RB-T2 / DW-T3b** mediante el [coordinador runtime](runtime-coordinator-v1.md):
ticket entre hilos, frontera CPU retenida, épocas/sampler privados y revocación
antes del retiro y de las transiciones cubiertas. La integración ejecuta cuerpos
privados con dependencias declaradas y compila unidades completas ON/OFF.
**DW-T3 sigue abierto** hasta RB-T3: conectar IO con CPU y DW en el candidato
enlazado, validar con VM y comprobar lifecycle/escritores. Captura deshabilitada.
