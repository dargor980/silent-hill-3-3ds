# DMA write probe v1 — DW01–DW07

Segundo lote de LG-I1. Instrumentación del proveedor PCSX2 fijado, con RAM
sintética propia. No habilita una sesión real ni completa LG-I1–I4.

## Requisitos EARS

- **DW01:** WHEN SPR copia a un destino host THEN el adaptador SHALL avisar antes
  de cada fragmento no vacío usando su puntero y longitud efectivos; SHALL
  conservar las escrituras, retornos y actualizaciones originales.
- **DW02:** WHEN MFIFO ejecuta una copia circular THEN el adaptador SHALL avisar
  antes de cada copia que realmente ejecuta el proveedor, incluidos wrap y fin
  exacto; SHALL conservar su comportamiento incluso con una longitud mayor que
  el anillo, sin sustituirlo por un algoritmo circular supuesto.
- **DW03:** WHEN SIF o la salida IPU copian fragmentos THEN el adaptador SHALL
  observar cada fragmento no vacío, incluidos destinos ajenos a RAM EE; el puente
  SHALL ignorar estos últimos sin consumir eventos LG.
- **DW04:** WHEN VIF1 solicita un retorno GS de longitud positiva THEN el
  adaptador SHALL invalidar por cobertura desconocida antes de la solicitud;
  SHALL conservar la llamada original y no certificar su finalización ni admitir
  captura real hasta verificar sincronización y todos los caminos GS.
- **DW05:** WHILE el observador está desactivado THEN el proveedor SHALL conservar
  las funciones originales sin referencias a los hooks; WHILE no hay conexión
  THEN los hooks SHALL ser inertes. Una invalidación SHALL NOT cancelar la copia.
- **DW06:** WHEN se valida el lote THEN SHALL ejecutar cuerpos exactos del
  proveedor con dobles explícitos y datos propios en ON, OFF y ASan/UBSan; SHALL
  comprobar avisos previos, bytes, tamaños, orden, ceros, destinos ajenos, rechazos
  de dirección y persistencia tras escribir el mismo valor o restaurarlo.
- **DW07:** WHEN se publica evidencia THEN SHALL separar compilación de unidades,
  harness de funciones y VM completa, conservar fuentes previas y hashes, y
  mantener pendientes JIT/caché/host, época, concurrencia global y extremos.

## Diseño

Se reutilizan `PhysicalWrites` y `LifetimeGuard` sin cambiar sus contratos.
SPR, SIF e IPU insertan avisos en las copias de sus funciones hoja. El helper común
de copia circular recibe un callback opcional solo en compilaciones del
observador; únicamente `hwMFIFOWrite` lo proporciona. Así `common` no depende
del observador y el resto de consumidores mantiene su comportamiento.

El alcance es un inventario acotado de productores, no una demostración exhaustiva.
SIF/IPU pueden copiar a temporales o memoria IOP: el destino host determina si
hay efecto sobre RAM EE. No se normaliza una dirección virtual por máscara.
El mutex del puente serializa avisos, no los efectos de memoria. El camino GS
queda cerrado conservadoramente antes de delegar; no se lee el ciclo EE desde
el hilo GS ni se interpreta el envío de un trabajo como su finalización.

## Tareas y aceptación

1. **DW-T1 / DW01–04:** inventariar función hoja, llamadores, destino, unidad de
   longitud, contexto de ejecución y sincronización. Registrar las rutas excluidas.
2. **DW-T2 / DW01–05:** crear nueva copia privada con parche reversible, callbacks
   antes del efecto y cero cambios en las fuentes anteriores. No añadir armado.
3. **DW-T3 / DW02,05,06:** compilar unidades reales ON/OFF; ejecutar harness con
   oráculos de bytes y eventos, bordes de anillo y errores. Conservar rechazos.
4. **DW-T4 / DW07:** repetir regresión host/Python y controles de custodia;
   publicar auditoría repetible y actualizar las tareas sin cerrar LG-I1.
