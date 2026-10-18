# Baseline PCSX2 — BB01–BB08

## Requisitos EARS

- **BB01:** WHEN se prepare el baseline THEN el coordinador SHALL verificar el
  commit IB01 limpio, los 5.228 hashes y 70 enlaces del prefijo SRC48, y disponer
  de al menos 20 GiB libres antes de compilar.
- **BB02:** WHEN se configure THEN el coordinador SHALL usar un directorio nuevo,
  Apple Clang/Metal explícitos, Release x86_64/macOS 11, LTO y tests originales;
  SHALL registrar argumentos, entorno, unidades y recursos generados.
- **BB03:** WHILE compile THEN el supervisor SHALL muestrear cada segundo el
  espacio libre y los tamaños lógico/asignado de la etapa, incluidos temporales,
  con dos jobs, máximo 8 GiB de etapa, suelo de 10 GiB y plazo de 45 minutos.
  IF se alcanza un límite o falla la medición THEN SHALL rechazar la ejecución
  y solicitar la detención únicamente de su grupo de procesos.
- **BB04:** WHEN se detenga un grupo THEN el supervisor SHALL acotar TERM/KILL,
  registrar EPERM y comprobar los procesos vivos del grupo, incluso si su líder
  ya salió. IF no puede comprobar el cierre THEN SHALL informar cierre no
  verificado, sin esperar indefinidamente ni aceptar el build.
- **BB05:** WHEN termine una operación THEN el coordinador SHALL conservar log,
  muestras previas y resultado, incluidos fallos; SHALL ejecutar tests y
  consumidores solo después de un build aceptado.
- **BB06:** WHEN se acepte el baseline THEN SHALL comprobar arquitectura, carga,
  bundle y tests originales disponibles, y realizar un arranque acotado con
  perfil separado. SHALL distinguir CLI, ventana observada y ejecución de juego.
- **BB07:** IF se necesita corregir compatibilidad THEN SHALL conservar el
  intento y checkout originales y preparar una copia/parche identificados.
  El baseline SHALL permanecer sin instrumentación y sin datos privados en CI.
- **BB08:** IF el empaquetador informa errores aunque salga con código cero
  THEN el coordinador SHALL conservar el intento y rechazar su promoción.
  WHEN prepare un candidato local THEN SHALL verificar firma, IDs y rutas de
  carga/búsqueda, conservar los entitlements originales y probar el candidato
  exacto. Una firma ad hoc SHALL identificarse como local, sin notarización.

## Diseño y pruebas

`tools.qa.supervised_process` separa política de límites, inspección/detención
del grupo y coordinación. Medición y diario son puertos inyectados; el
coordinador privado posee rutas, entorno y recibos. Las pruebas usan procesos
sintéticos y fallos simulados, sin PCSX2, BIOS ni juego, y pertenecen al job
Python existente de CI.

El presupuesto es una cota preventiva, no una predicción medida: reserva hasta
4 GiB para objetos/LTO, 2 GiB para bundle/recursos y 2 GiB para temporales/logs.
Con 20 GiB iniciales deja margen para el sistema. El muestreo no impone una
cuota instantánea y no limita memoria RAM. Un fallo conserva evidencia y
requiere revisar la causa antes de reintentar. Las fuentes y dependencias ya
existentes se verifican por separado; la etapa nueva incluye todo crecimiento
controlado del build. No se aplica descuento de archivos dispersos de Xcode
a este build con Makefiles.

Los builds incrementales de tests comparten la etapa y su límite de 8 GiB;
su reserva de inicio y suelo son 10 GiB. BB01 exige 20 GiB antes del build
completo, no antes de cada proceso de verificación. La configuración de CI
ya ejecuta los nuevos tests mediante `tests/python`; el baseline privado se
construye localmente y no se incorpora al pipeline ni a sus artefactos.
