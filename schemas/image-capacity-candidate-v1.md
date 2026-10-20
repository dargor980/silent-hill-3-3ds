# LC-B — Candidato privado con capacidad 2.048 y PD v2

Historia: como investigador, necesito comprobar la corrección de SRC120 dentro
del proceso PCSX2 antes de dar por resuelto RT-T3b.3.

## Requisitos EARS

- **LC-B01:** WHEN se prepare el candidato THEN SHALL preservar fuentes,
  objetos, bibliotecas y candidatos anteriores; usar una copia nueva del servicio
  limpio y sincronizar las seis fuentes/cabeceras modificadas en SRC120.
  SHALL retirar los hooks privados del censo y del preflight histórico.
- **LC-B02:** WHEN cambie el ABI THEN SHALL reconstruir las 128 unidades
  afectadas, regenerar los MOC utilizados y comprobar las dependencias de cada
  objeto reutilizado, incluidas las de los miembros de los 19 archivos estáticos.
  IF aparece otra dependencia modificada THEN SHALL detenerse y ampliar la
  matriz explícitamente antes de compilar. SHALL fijar hashes y comandos.
- **LC-B03:** WHILE reconstruya este candidato THEN SHALL trabajar en serie,
  exigir 12 GiB libres al iniciar cada proceso, detenerse bajo 10 GiB libres o
  sobre 1 GiB de tamaño lógico/asignado del stage completo, y supervisar cada
  0,5 s. SHALL limitar cada compilación/enlace a 180 s, MOC/firma a 60 s y la
  secuencia completa de compilación a 3.600 s. IF excede un límite THEN SHALL
  conservar el rechazo y verificar el cierre del grupo de procesos propio.
- **LC-B04:** WHEN enlace THEN SHALL verificar las 470 entradas, resolución de
  frameworks, firma ad hoc y arranque `testconfig`; fijar manifiesto y consumidor
  Python PD v2 en copias privadas antes de las sesiones.
- **LC-B05:** WHEN pruebe el runtime THEN SHALL usar perfiles nuevos para un
  rechazo sin VM y dos arranques con VM pausada, conservar los plazos 5 s/2 s,
  comprobar identidad, secuencias, conteos, cierre y ausencia de admisión. IF
  no obtiene muestras positivas THEN SHALL mantener RT-T3b.3 abierto y publicar
  el fallo, sin omitir verificaciones ni ampliar plazos para aceptarlo.
- **LC-B06:** IF la preparación supera el preflight pero rechaza una imagen no
  cubierta THEN SHALL conservar ese candidato y crear una variante privada
  que registre únicamente la primera causa terminal, nombre del loader e
  identidad de archivo, sin cambiar la clasificación ni el retorno. SHALL
  reconstruir solo `platform_inventory.cpp`, verificar las otras 469 entradas
  y conservar firma, manifiesto y consumidor fijados. El presupuesto de 1 GiB
  SHALL incluir ambos stages; siguen los umbrales y plazos de LC-B03.
- **LC-B07:** IF la sonda identifica un archivo del sistema fuera de la caché
  THEN SHALL comprobar su identidad de disco, Mach-O y firma antes de fijarlo
  explícitamente en un manifiesto nuevo. SHALL conservar el manifiesto rechazado,
  usar una raíz exacta y un hash/tamaño concretos y repetir con el candidato sin
  sondas. SHALL NOT clasificarlo por nombre, omitirlo o añadir archivos durante
  una sesión. La clasificación ordinaria por archivo y la doble pasada permanecen.

## Diseño y presupuesto

Se conserva la separación de responsabilidades de LC: el build integra el
núcleo y los adaptadores existentes; no añade políticas al transporte ni cambia
las garantías del inventario. Se parte de `source-runtime-service-v2`, cuyo
contenido coincide con el candidato del censo salvo cuatro fuentes instrumentadas
y dos cabeceras de sonda. El núcleo propio se contrasta contra el repositorio.

La matriz anterior contiene 128 objetos que suman 18.165.200 bytes. La fuente
limpia ocupa 137.060.352 bytes asignados y el bundle anterior 113.041.408.
Estos tres conjuntos suman menos de 257 MiB; el límite de 1 GiB incluye además
MOC, dependencias, temporales del enlazador, copias del consumidor, perfiles y
logs. Los enlaces anteriores de este mismo producto duraron 21–28 s. Es una
estimación con aborto supervisado, no una garantía de consumo máximo.

La reserva inicial de 12 GiB deja al menos 2 GiB hasta el suelo y el stage
completo no puede superar 1 GiB. La compilación secuencial evita multiplicar
temporales y memoria de compiladores. Esta decisión acotada **no modifica IB02
de 20 GiB para builds completos ni extiende IC-L**, que cubría solo dos unidades.
No se compilan dependencias de terceros ni se borran builds para ganar espacio.

## Tareas

- [x] **LC-BT1 / RT-T3b.3a:** inventariar entradas, verificar archivos estáticos,
  regenerar MOC, reconstruir y firmar; comprobar preservación y `testconfig`.
  Requisitos LC-B01–04.
- [x] **LC-BT2 / RT-T3b.3b:** fijar consumidor/manifiesto, rechazo sin VM y dos
  sesiones pausadas; verificar muestras y cierre. Requisitos LC-B04–05.
- [x] **LC-BT3 / RT-T3b.3c:** publicar evidencia reproducible, fallos y límites,
  actualizar trazabilidad sin cerrar captura ni otros gates. Requisito LC-B05.
- [x] **LC-BT4:** identificar la imagen no cubierta en dos perfiles mediante
  la sonda terminal privada, contrastarla con el manifiesto y definir la
  corrección a partir de su identidad comprobada. Requisito LC-B06.
- [x] **LC-BT5:** fijar el manifiesto corregido y probar dos perfiles nuevos con
  el candidato sin sondas, conservando el rechazo anterior. Requisito LC-B07.

Resultado y límite de la entrega final: [SRC121](../docs/execution/f02-07-capacity-candidate.md).

La entrega final y LC-BT2 se completan posteriormente en
[SRC122](../docs/execution/f02-07-service-release.md), conservando el fallo de
cierre de SRC121 y el rechazo por plazo observado durante la nueva validación.
