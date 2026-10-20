# Entradas productoras CPU v1 — EP01–EP07

Detalle ejecutable de CQ3-B/B2; complementa [WD01–WD12](worker-drain-v1.md)
y [RD01–RD08](retained-drain-v1.md). El alcance son las entradas revisadas de
MTGS/MTVU y el aviso de cambio de idioma del frontend Qt fijado.

- **EP01:** WHEN una entrada instrumentada se ejecuta en CPU y la fase posterior
  a PINE ha empezado THEN SHALL cancelar y retirar el intento antes del primer
  efecto de su cuerpo, incluyendo contadores, FIFO directo, writeback y reservas.
- **EP02:** WHEN termina la cancelación THEN SHALL ejecutar la operación original
  conservando argumentos, retorno, orden y propiedad de callbacks/punteros.
  SHALL NOT convertir una operación void en un descarte silencioso.
- **EP03:** WHILE drenan reservas anteriores de PINE THEN las entradas SHALL
  permitir su progreso. IF no es el hilo CPU THEN el aviso SHALL NOT manipular
  el propietario de otro hilo ni declarar exclusión de ese productor.
- **EP04:** WHEN se cambia el idioma con EmuThread disponible THEN SHALL enviar
  el aviso por CPU y comprobar GS abierto al despachar. WHEN GS ejecuta el aviso
  THEN SHALL comprobar que FullscreenUI está inicializada antes de actualizarla.
  IF falta EmuThread o GS está cerrado THEN SHALL omitir el aviso de UI inactiva.
- **EP05:** WHILE el aviso espera CPU/GS THEN SHALL conservar su intención sin
  referencias a QWidget ni esperas síncronas. La corrección de propietario SHALL
  estar presente tanto con observador ON como OFF.
- **EP06:** WHEN se valida B2 THEN SHALL comparar efectos ON/OFF/anterior OFF,
  ensayar retención pendiente/retenida, trabajo PINE previo, FIFO directo,
  contadores GIF, payload VU y callbacks demorados, con sanitizadores.
- **EP07:** IF quedan entradas Qt, escritores ajenos o acuses VU/GS sin demostrar
  THEN SHALL mantener rechazado el puerto productivo y vacíos los modos admitidos.

## Diseño

Se reutiliza `BeforeObserverProducer` de SRC76: el puente decide sobre el
propietario CPU; RetainedDrain invalida y libera el puerto antes de reabrir PINE;
las funciones del proveedor conservan su trabajo. No se crea otro gate ni una
segunda autoridad de estado. La comprobación del flag CPU precede al acceso al
controlador TLS, incluyendo Reset/Close llamados por constructor/destructor VU.

El aviso se coloca como primera instrucción del cuerpo de cada entrada revisada,
bajo SH3_ENABLE_OBSERVER. No cubre evaluación de argumentos por el llamador ni
convierte esas funciones en APIs seguras para productores concurrentes. Helpers
privados de paquetes y bucles de trabajadores conservan su comportamiento.
SetRunIdle es una entrada de GS; requiere el protocolo de trabajador de CQ3-C.

LocaleChanged usa UI → Host::RunOnCPUThread → MTGS::RunOnGSThread. La disponibilidad
de EmuThread se comprueba en UI, GS en CPU y FullscreenUI en GS. El callback sin
capturas no conserva widgets ni una instancia antigua de FullscreenUI. El aviso
se aplica a la UI vigente al ejecutarse; no representa una transacción de idioma
con identidad de sesión. B3 cubre los demás despachos tardíos.

## Tareas y aceptación

- **EP-T1 / EP01–03,07:** nueva copia privada, inventario explícito y parche
  reversible de las entradas; compilar MTGS/MTVU ON/OFF.
- **EP-T2 / EP04–05:** corregir LocaleChanged; compilar Translations ON/OFF y
  probar ausencia/cierre/destrucción entre despachos.
- **EP-T3 / EP01–07:** cuerpos exactos privados con dobles de dependencias,
  secuencias de efectos y duración de punteros/callbacks; auditoría de custodia
  repetida, informe público sin fuentes del proveedor ni datos del juego.

Los tests aislados no acreditan ringbuffers reales, scheduler, reentrada Qt
completa ni retenciones de workers. La batería portable previa y la CI no
dependen de los includes privados; las compilaciones del proveedor son locales.
