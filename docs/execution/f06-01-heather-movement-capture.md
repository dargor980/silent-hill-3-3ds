# HM-T2a: movimiento y corrección de Heather en PCSX2

**Resultado:** primera cadena de carrera capturada y auditada. El escritor
horizontal, el ajuste vertical posterior y la publicación de la matriz quedan
separados dentro de **una misma actualización**, ordinal 81849. HM-T2a cierra
ese alcance acotado; HM-T2, el controlador y la habitación permanecen abiertos.
Requisitos [HM03–04](../specs/sh3-3ds/heather-movement.md).

## Procedencia y adquisición

- Heather original, actor `0x004481D0`, tipo `0x0100`, callback `0x001986C0`.
  MDL522 y ANM525 se cotejan por hash en las 16 capturas.
- Perfil privado nuevo `heather-movement-v1`, PID observado **18885**,
  socket propio. Ejecutable instrumentado SHA-256
  `54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
- Copia de `normal-controls-v2.p2m2`, controles normales grabados previamente
  por el usuario. SHA-256
  `23b065767544703b785d43570aa9a4de5c224a3efb061034f11cf1a9e67d17c0`.
  Ancla SHA-256
  `2d448f68eaeeb61f23de33c527eefce3ab55d313c7167cfc6c8ee7cc6f452fc7`.
- **Dos restauraciones iniciales declaradas:** lanzamiento desde la copia y
  comienzo de la reproducción desde su ancla. RAM, registros CPU decodificados
  y ciclo inicial `110119712356` coinciden exactamente. No hay continuidad
  atribuida a la sesión HL anterior ni restauraciones entre las muestras 02–15.
- Sin escrituras de PC, RAM ni controles artificiales para provocar movimiento.
  Se usan breakpoints, pasos de depurador y guardados exclusivos mediante PINE.
  Los breakpoints antiguos de HL conservan condición `0`.
- **16 estados completos**: dos anclas y 14 paradas del ordinal 81849;
  **12 observaciones pequeñas** con el observador de solo lectura. Estas últimas
  conservan PC/ciclo/datos y hash de respuesta, pero no se presentan como
  observaciones enlazadas individualmente a un estado completo.
- Entrada `0x1800` (↑ + Cuadrado), ticks=2 y recursos iguales en toda la cadena.
  Reserva de 512 MiB y presupuesto inicial de 32 estados; no se agotaron.
  Originales de grabación, ancla, perfil, BIOS y tarjetas permanecen intactos
  según los hashes de preparación y auditoría.

La ventana de juego requirió ayuda del usuario para salir de pantalla completa.
Después se pudo abrir la reproducción y avanzar sin más entrada manual. Una
serie rápida de clics de paso ejecutó solo el primero; el observador rechazó
el PC esperado y se conservó la parada 07. Se continuó verificando cada paso
por separado, sin reconstruir ni ocultar esa incidencia.

## Escritura del desplazamiento

En la entrada `0x001DCCE0`, `a0=actor`, `a1=0x01FFFB80` y
`ra=0x001481FC`: se acredita el llamador `0x001480D0`, cuya llamada está en
`0x001481F4`. El vector recibido es `(69,99999237060547, 0, 0, 0)`.

| Parada | PC | Posición X | Posición Y | Ciclo EE |
| --- | --- | ---: | ---: | ---: |
| Entrada | `0x001DCCE0` | −19112,69921875 | −0,567034900188446 | 118152873302 |
| Antes de SQC2 | `0x001DCCF0` | −19112,69921875 | −0,567034900188446 | 118152873307 |
| Después de SQC2 | `0x001DCCF4` | −19042,69921875 | −0,567034900188446 | 118152873309 |
| Retorno observado | `0x001481FC` | −19042,69921875 | −0,567034900188446 | 118152873312 |

Z=20000 y W=1 se conservan. La diferencia X almacenada es exactamente 70,
compatible con el redondeo f32 de la suma de los operandos de esta muestra.
No se generaliza esta comparación a toda la aritmética EE/VU.

El par 03/04 acredita la instrucción `SQC2 vf4,0(v1)`, opcode `0xF8640000`:
`v1=actor+0x20`, VF4 igual antes/después, 32 palabras bajas GPR iguales,
intervalo de dos ciclos y **ningún byte distinto fuera del destino de 16 bytes
en los 32 MiB de RAM EE**. Los 16 bytes almacenados coinciden con VF4.
La comparación no afirma que todos los bytes del destino cambien ni que la
operación precedente esté validada para operandos arbitrarios.

## Corrección posterior y matriz

La posición no cambia al volver de `0x001480D0` ni en las observaciones tras
`0x00136D50`, `0x00135200`, `0x00133DD0` y `0x001345C0`. Dentro del bloque
`0x001378B0`, el par completo 09/10 delimita la llamada a **`0x001372D0`**:

| Punto | PC | Y | Ciclo EE |
| --- | --- | ---: | ---: |
| Antes de la llamada | `0x001378CC` | −0,567034900188446 | 118152892784 |
| Retorno | `0x001378D4` | −0,567047119140625 | 118152892836 |

Solo Y cambia en la posición4; delta **−0,000012218952178955078**. El resultado
coincide bit a bit con el campo `0x01CFB504` capturado antes de la llamada y
con `actor+0x130` después. El análisis estático muestra la copia de ese campo,
la comparación con Y y la escritura candidata `0x0013732C`; su condición
se satisface en la entrada conservada. **No se capturó antes/después de esa
instrucción escalar individual**: la atribución dinámica llega a la rutina.
La procedencia completa del resultado de consulta y sus casos de error siguen
pendientes; no se ha implementado ni validado un solucionador de colisión.

Después de `0x00137780`, al salir del callback en `0x001987A4` y al entrar
en `0x001DCBA0`, la posición permanece idéntica. La entrada del constructor
usa `a1=actor+0x30`, `a2=actor+0x20`; antes conserva la traslación anterior.
En `0x001DCC28` ya publica la posición corregida como traslación de matriz,
**idéntica en bytes**, sin alterar la posición. El retorno de composición
`0x001DD434`, ciclo `118153042357`, conserva ese resultado.

Once ventanas de código del ELF PAL fijado coinciden en las 14 capturas de
esta actualización: escritor, llamador, callback, rutinas posteriores,
consulta, corrector, helper escalar y constructor. Sus hashes están en el
informe local; se conserva el ELF fijado por HM-T1.

## Comparación independiente y límites

El prefijo espacial completo de 128 bytes en la publicación final coincide
con el ordinal 81849 de la referencia HL auditada en HM-T1. Sin embargo,
la referencia tiene ciclo **118153042270**, frente a **118153042357** aquí:
**diferencia de +87 ciclos EE**. El primer auditor, que exigía además igualdad
de ciclo, rechazó esa comparación. La discrepancia se conserva expresamente;
el resultado aceptado es igualdad espacial y orden interno de esta cadena,
**no equivalencia temporal entre ejecuciones**. No se ha atribuido todavía
la causa exacta de esos 87 ciclos.

Este tramo no prueba caminar, parada, giro, empuje contra paredes, escalones,
pendientes ni aceleración. Tampoco descarta escrituras transitorias entre
observaciones ni acredita la autoridad exclusiva del movimiento raíz.
La unidad temporal general y los casos de contacto requieren HM-T2b antes
del contrato del controlador. El visor y el build físico `7250f427ffb9`
no cambian en esta investigación.

## Verificación y reproducción local

- **52 pruebas sintéticas** del comprobador puro de almacenamiento:
  literales asimétricos, cero con signo, escritura idempotente, destino,
  opcode, sesión/PID, PC/ciclos/ordinal, GPR, VF4, límites, tipos y mutaciones
  de cada byte del destino y fuera de él. **26/26 líneas y 2/2 ramas**.
- Adquisición, contrato puro y auditoría de archivos son componentes separados;
  el comprobador no usa sockets, archivos ni SDK. Son herramientas diagnósticas
  locales, sin cambio de producción ni nuevo gate de CI remoto.
- Se releyeron todos los estados y recibos, identidad y recursos, las ventanas
  ELF/RAM, procedencia y originales. Auditoría normal y con Python `-O`
  produjeron informes byte por byte iguales.
- El primer comando de cobertura apuntó al archivo como nombre de módulo y
  no recolectó datos; se corrigió a `--cov=store_evidence`. Solo la medición
  posterior indicada arriba se considera válida.

Directorio privado: `/Users/germancontreras/sh3-private-data/heather-movement-v1`.
Herramientas locales: `build/heather-movement/{launch,capture,peek,
store_evidence,audit_capture}.py` y `test_store_evidence.py`.
Informe: `reports/local/heather-movement-capture-v1.json`, SHA-256
`817c86f62a816cac6b62be47936b21735f63513a1ede9197f6a99d62879ff217`.
El material del juego y los estados permanecen privados.

```sh
rtk proxy .venv/bin/python -m pytest build/heather-movement/test_store_evidence.py --cov=store_evidence --cov-branch --cov-report=json:build/heather-movement/store-coverage.json -q
rtk proxy .venv/bin/python build/heather-movement/audit_capture.py /tmp/heather-movement-audit.json
rtk proxy .venv/bin/python -O build/heather-movement/audit_capture.py /tmp/heather-movement-audit-o.json
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Siguiente: **HM-T2b**, ampliar el contraste a caminar, parada, giro y contacto,
seguir el productor de la consulta vertical y comprobar la base temporal.
