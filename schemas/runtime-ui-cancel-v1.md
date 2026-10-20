# UC — Cancelación desde la interfaz Qt

Historia: como investigador, necesito salir desde la ventana o acción Salir
durante el diagnóstico sin detener CPU antes de retirar IO/DW.

## Requisitos EARS

- **UC01:** WHEN la interfaz solicite salir con un servicio diagnóstico iniciado
  THEN SHALL señalar cancelación antes de entrar en operaciones bloqueantes de
  VM; SHALL conservar la ventana y el bucle de eventos mientras termina IO.
- **UC02:** WHEN IO confirme finalización THEN SHALL usar la salida Qt existente
  que retorna al epílogo, unir IO y después detener CPU. SHALL NOT unir IO desde
  CPU, bloquear UI esperando CPU ni tratar una cancelación como retirada.
- **UC03:** IF el servicio no se activó o falló al arrancar THEN SHALL conservar
  la ruta habitual de salida. Solicitudes repetidas SHALL ser idempotentes.
  WHEN termine el servicio antes de procesar la petición THEN SHALL seguir
  encaminando la salida hacia su epílogo de unión.
- **UC04:** WHEN se valide THEN SHALL invocar la acción Qt Salir y el evento de
  cierre de la ventana reales, con Host/VMManager reales y perfiles separados.
  SHALL acreditar el punto observado: espera inicial sin VM, inventario con VM
  y espera de liberación tras tres respuestas. SHALL verificar causa cancelada,
  limpieza, orden de retirada/unión y salida cero, sin admitir captura.
- **UC05:** WHEN se use una sonda THEN SHALL aislarla de la solución, fijar sus
  fuentes y declarar su efecto. SHALL observar fases sin detenerlas ni ampliar
  plazos; si pierde la fase SHALL conservar el intento como no cubierto. SHALL
  comparar el candidato base y conservar rechazos y fallos.

## Diseño

Un puerto propio del servicio responde si posee una sesión que requiere el
epílogo especial. La interfaz llama al puerto al principio de closeEvent,
requestExit y quit. Si lo posee, señala cancelación y difiere la salida; el
timer Qt ya existente sale al finalizar IO. La interfaz no conoce el inventario
ni destruye recursos del trabajador. El puerto no depende de Qt ni se usa como
prueba de retirada; se prueba con servicio real y cola CPU de prueba por separado.

En el modo diagnóstico optativo, el cierre del servicio ya termina la aplicación
automáticamente. Estas rutas mantienen ese comportamiento. No se altera el flujo
normal sin diagnóstico ni se habilitan guardados o confirmaciones de apagado en
los perfiles de prueba. El botón Apagar VM y los callbacks tardíos tienen alcance
separado; esta etapa valida salida de aplicación.

La sonda privada marca entrada/salida de fases con atómicos y observa desde un
timer UI de 2 ms. Invoca `QAction::trigger` o `MainWindow::close`, sin llamar
directamente a cancelación. Registra hilo UI, fase antes/después, cancelación,
fin IO y unión antes de detener CPU. No bloquea trabajadores para hacer coincidir
la prueba. La ejecución programática de eventos Qt no equivale a un clic físico.
En liberación, además espera un archivo local fijado antes del arranque que el
padre crea después de aceptar la tercera respuesta. Es coordinación de la sonda;
no añade mensajes al protocolo ni cambia el plazo global o del consumidor.

## Presupuesto y tareas

UC-B: build incremental de las unidades afectadas y hasta tres bundles separados
(base observado, corregido observado y corregido sin sonda), fuentes propias
superpuestas a la base inmutable; unos 325 MiB de bundles antes de objetos/logs.
Inicio ≥11 GiB, suelo 10 GiB, máximo combinado 512 MiB, supervisión 0,5 s,
180 s por compilación/enlace y 600 s por secuencia. Sesiones ≤100 s cada una.
No autoriza un build completo; IB02 general sigue en 20 GiB. Las regresiones
nativas usan etapas ≤512 MiB, inicio/suelo 10 GiB y comandos ≤180 s.

- [x] **UC-T1:** fijar ruta/sonda, observar base y conservar su resultado;
  implementar puerto de cancelación e integración temprana en Qt. UC01–UC05.
- [x] **UC-T2:** probar activación, inactividad, repetición, espera, sesión activa
  y finalización; integrar CTest, Debug/Release, sanitizadores y TSan. UC01–UC03.
- [x] **UC-T3 / RT-T3c.1b.UI:** reconstruir candidato aislado, verificar firma,
  manifiesto y dependencias; dos perfiles por fase/ruta, con rechazo cancelado
  y orden de cierre comprobado. Preservar intentos no cubiertos. UC04–UC05.
- [x] **UC-T4:** publicar evidencia y límites; mantener separados cancelación
  durante entrega parcial, callbacks tardíos, rendimiento y gates. UC04–UC05.

Resultado: [SRC124](../docs/execution/f02-07-ui-cancel.md). Doce perfiles con
sonda y dos acciones visibles mediante CUA en el candidato sin sonda verifican
cancelación; un control sin cancelación conserva las tres respuestas aceptadas.
