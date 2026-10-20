# IC — Censo diagnóstico de módulos

Historia: como investigador, necesito medir la demanda que invalida el registro
de 1.024 imágenes antes de decidir una capacidad de producción. Referencia:
[SRC118](../docs/execution/f02-07-native-preflight.md), RT-T3b.1.

## Requisitos EARS

- **IC01:** WHEN llegue un evento del loader THEN el censo SHALL observarlo
  bajo el mismo mutex que el registro original, sin sustituirlo ni cambiar sus
  veredictos, límite o estado fallido.
- **IC02:** WHEN un alta llegue con 1.024 entradas ocupadas THEN el censo SHALL
  registrar si su dirección ya está presente, junto con ordinal y contadores.
  Esta observación SHALL contrastarse con el rechazo real del registro original.
- **IC03:** WHILE observe THEN el censo SHALL mantener como máximo 4.096
  direcciones y 16.384 eventos, sin asignación dinámica, llamadas de sistema ni
  desreferenciar imágenes en los callbacks. Estos límites solo acotan la sonda.
- **IC04:** IF llega un duplicado, una retirada desconocida, una dirección nula
  o se agota un presupuesto THEN el censo SHALL quedar incompleto, conservar
  la causa y no presentar los contadores parciales como demanda total.
- **IC05:** WHEN se informe una muestra THEN SHALL copiarla bajo mutex y emitir
  únicamente metadatos fuera del callback. SHALL distinguir lecturas durante
  arranque/pausa y un corte posterior al cierre de CPU; ningún corte afirma
  cubrir eventos posteriores durante finalización del proceso.
- **IC06:** WHEN se valide THEN SHALL ejecutar controles de borde y errores,
  regresiones nativas y sanitizadores, y repetir VM pausada y frontend sin VM
  en perfiles separados. SHALL preservar fuentes, candidatos y rechazos previos.
- **IC07:** IF el censo es completo THEN sus cuentas SHALL servir para proponer
  un presupuesto, no para admitir inventario, imágenes, escritores o captura.
  Una ejecución breve SHALL NOT acreditar la demanda de todas las fases del juego.

## Diseño SOLID

`ImageCensus` es una máquina de estados pura y serializada por su dueño, con
almacenamiento fijo y estadísticas propias. La copia privada de `MacOSImageEvents`
la alimenta dentro del mutex existente y copia observaciones. El emisor local
formatea fuera del bloqueo. Qt solicita el corte final después de detener CPU.
No cambia `ImageLedger`, su ABI ni las respuestas del servicio.

Se mantienen la traza y el preflight de SRC118 para vincular el evento observado
con el rechazo. Los contadores solo son completos si no ha fallado ni el censo
ni su envoltorio de proceso/mutex. El tamaño de la sonda se mide en los tests;
la complejidad máxima es O(4.096) por evento y queda acotada por IC03.

## Reenlace acotado de esta sonda — IC-L

Los enlaces verificados de SRC117/SRC118 duraron 28,163, 22,153 y 21,198 s;
las etapas observadas alcanzaron 108,54, 107,91 y 107,93 MiB. Para esta
reconstrucción parcial se usa una excepción específica al presupuesto genérico
de IB02: **12 GiB iniciales, suelo 10 GiB, etapa máxima 512 MiB, 180 s por
compilación y 180 s por enlace**. La etapa incluye copia de fuentes, temporales,
objetos, bundle, perfiles y logs. Se mide antes de crearla y antes de cada proceso.

Solo se permite recompilar `macos_image_identity.cpp` y `QtHost.cpp`, regenerar
el MOC de QtHost y reutilizar las otras 468 entradas de enlace fijadas por hash.
No se reconstruyen dependencias, no se ejecuta el build completo ni se permiten
inputs no fijados. Un cambio de alcance invalida esta excepción y requiere
evaluar su presupuesto antes de ejecutarlo. El supervisor y sus pruebas de
cierre son los existentes; los fallos quedan conservados. El muestreo no es
una cuota instantánea de disco ni un límite de RAM.

IB02 conserva sus 20 GiB para builds completos y dependencias grandes. Esta
excepción no se aplica a una futura corrección de capacidad ni a otros enlaces.

- [x] **IC-T1:** máquina de estados, integración de pruebas y controles nativos.
- [x] **IC-T2:** copia privada acotada, dos objetos, firma y control sin VM.
- [x] **IC-T3 / RT-T3b.1:** repeticiones, cuentas completas, clasificación del alta
  al llenarse y propuesta de presupuesto con sus límites explícitos.

Resultado: [SRC119](../docs/execution/f02-07-native-census.md), 1.067 módulos
sin VM y 1.069 con VM pausada en dos repeticiones de cada perfil. La propuesta
de 2.048 entradas requiere RT-T3b.2; no modifica la capacidad de producción.
