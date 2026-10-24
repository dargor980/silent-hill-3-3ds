# HI-T6: primer plano de Heather

Petición: acercar la cámara para ver la cara. Requisito HI07 de
[la spec](../specs/sh3-3ds/heather-inspection.md).
Build final: **`f25a2d9bb316`**. Validación física pendiente.

## Cambio de cámara

SELECT alterna entre cuerpo completo y un objetivo fijo de inspección
`(0,1.32,-1.98)`, distancia inicial 0,65. X/Y ajusta entre 0,45 y 9,
con velocidad proporcional a la distancia cuando es menor que 3. B recupera
el cuerpo completo. A/R/L, START y ciclo de vida conservan su comportamiento.
El preset corresponde al clip actual de espera; no sigue expresiones ni es
una cámara jugable general.

`OrbitCamera` transporta su objetivo y el cálculo de ojo/LookAt lo usa en
los adaptadores. `RenderProbe` recibe un mínimo por instancia, de 3 por
defecto; los visores anteriores mantienen su límite. Rechaza cámaras y
objetivos no finitos/fuera de rango. `RigProbe` gestiona SELECT y lo filtra
durante suspensión, regreso con controles retenidos y salida con START.
La ordenación del cabello usa el mismo objetivo que la cámara de dibujo.

## Defecto revelado por el zoom

El primer plano del build experimental `693c5df4fa25` mostró la cara y
el cabello con regiones de textura incorrectas. Las UV GS y los RGBA
estaban previamente contrastados; el error estaba en la orientación de
filas de la carga PICA. Se cambió únicamente `upload_rig_texture` para
leer la fila `height-1-y` al llenar Morton, conservando UV, CRC y normalización
alfa. Anclas sintéticas de una textura no cuadrada comprueban las cuatro
esquinas y límites de tesela. La comparación visual antes/después muestra
ahora ojos, labios, cabello y ropa en sus posiciones.

No se modifican los SRI ni las 13 texturas fuente de A/B. Los visores
anteriores del caballo tienen otro adaptador; esta corrección no acredita
ni modifica su orientación visual. Queda una revisión separada de ese
adaptador para evitar trasladar automáticamente esta aceptación.

## Validación

- 351 CTest completos aprobados en Release y ASan/UBSan tras cambiar cámara.
- Tras la corrección de upload, regresión dirigida de cámara/rig/render
  de 25 tests aprobada en ambos presets; no se atribuye nueva prueba completa a ese corte.
- 47 tests Python de SRI/lector/paquete aprobados.
- ARM compilado con SDK fijado y gate de salida del shader aprobado.
- Azahar: cara visible a 0,65 y 0,45, con texturas orientadas correctamente;
  88,205 segundos continuos a distancia mínima, Q12 39572 → 33602 con bucles.
  SELECT funciona en reproducción y pausa; X/Y acerca/aleja, cruceta gira,
  B vuelve al cuerpo y START retorna a la lista de aplicaciones.
  Recibo y capturas de controles en `reports/local/heather-camera-v1.json`
  y `build/heather/face-*.png`.
- La 2DS XL aún debe confirmar zoom, SELECT, duración y START/tapa/HOME.

Logs: `build/heather/camera-host-tests.log`, `camera-sanitize-tests.log`,
`camera-host-tests-v2.log`, `camera-sanitize-tests-v2.log`,
`camera-python-tests.log`, `camera-arm-build-v2.log`.
SHA del `.3dsx`:
`837c062d273e0205b2ab266bb5f8b4a814e14f90b0ecd7e8d31542fa44a8ce4f`.

Entrega exclusiva: `/Users/germancontreras/sh3-private-data/heather-3ds-v2/sd-card.zip`,
18.954.017 bytes, SHA
`80a97c21d01f6933069d05d3fc65500bb6f4a6d17d79575f0f2faee92f4731ab`.
Los ZIP de A/B coinciden; entradas y manifiesto se releen tras escribir.
Recibo: `reports/local/heather-delivery-v2.json`. La entrega anterior se
conserva como evidencia y queda reemplazada para las siguientes pruebas.
