# Servicio IO del candidato privado — RT v1

Historia: como investigador, necesito que el candidato PCSX2 ejecute una sesión
de diagnóstico con Host/VMManager reales y que cierre antes de detener CPU.

## Requisitos EARS

- **RT01:** CUANDO el launcher active el servicio, DEBERÁ fijar endpoint absoluto,
  manifiesto absoluto, tres hashes y disparador local antes de crear IO. La
  ausencia de activación DEBERÁ conservar el arranque habitual; configuración
  incompleta DEBERÁ fallar antes del despacho CPU.
- **RT02:** CUANDO llegue el disparador de pausa, IO DEBERÁ fijar un único plazo
  de cinco segundos antes de conectar y encolar. Conexión y espera CPU DEBERÁN
  consumir ese plazo. La espera inicial de pausa DEBERÁ ser cancelable y acotada.
- **RT03:** CUANDO conecte, DEBERÁ comprobar PID, nacimiento y usuarios del padre
  local fijado al arrancar, y conservar su identidad nativa completa en el canal.
  Datos recibidos por el socket SHALL NOT seleccionar expectativas ni políticas.
- **RT04:** CUANDO publique CPU una vinculación, IO DEBERÁ componer la fábrica
  nativa y la sesión con ese mismo objeto; la sesión DEBERÁ terminar después de
  tres respuestas como máximo o del primer rechazo, sin reintentar adquisiciones.
- **RT05:** CUANDO se cancele o falle, IO DEBERÁ cerrar el canal, cancelar el
  handoff y conservar trabajador/solicitud hasta retirada CPU y unión DW.
  Excepciones de construcción DEBERÁN recorrer la misma limpieza.
- **RT06:** MIENTRAS IO tenga limpieza pendiente, el frontend DEBERÁ conservar
  CPU activo y procesar eventos. Solo después de terminar IO DEBERÁ unirlo y
  detener EmuThread. La espera de CPU SHALL NOT ejecutar una unión de IO/DW.
- **RT07:** CUANDO se valide, DEBERÁ distinguir tests con puertos de prueba,
  unidades completas, candidato enlazado sin VM y candidato con VM. Ninguno
  habilitará captura ni cambiará los gates desconocidos o violados.

## Diseño SOLID y tareas

Un servicio macOS posee un hilo IO y configuración local inmutable. El frontend
Qt solo inicia, señala pausa/cancelación y recoge un hilo terminado. El servicio
usa el puerto de cola existente; fábrica, protocolo y transporte conservan sus
responsabilidades. Los hooks están limitados a `SH3_ENABLE_OBSERVER && __APPLE__`.

El disparador `paused` procede de `Host::OnVMPaused`; `immediate` permite probar
rechazo con CPU real sin VM. No pausa ni reanuda la VM por su cuenta. En modo
diagnóstico optativo, el frontend sale al terminar la única sesión. La espera
de pausa tiene 60 s; no amplía el presupuesto posterior de cinco segundos.

- [x] **RT-T1 / RS-T3b.1:** implementar servicio, contrato local, conexión
  no bloqueante y limpieza; probar errores, cancelación, pausa y retiro CPU.
- [x] **RT-T2 / RS-T3b.2:** derivar copia privada verificable, integrar hooks Qt,
  compilar ON/OFF y enlazar candidato en etapa nueva bajo IB02.
- [ ] **RT-T3 / RS-T3b.3:** empaquetar/verificar candidato y probar sin VM y con
  VM; contrastar lifecycle, gates, escritores y repetibilidad del loader.

No sustituye los criterios pendientes de RS-T3/RB-T3/DW-T3.

La salida programática usa `QCoreApplication::exit` desde UI y detiene su timer.
`QApplication::quit` pasa por la terminación nativa de Cocoa y no garantiza
retornar al epílogo que une IO y detiene CPU. Esta distinción se valida con el
candidato, además de las pruebas del servicio.
