# F03.04 / CF-T6 — Cotejo privado del decoder poligonal

2026-10-23. **CF-T6 completada.** Cotejo de las dos extracciones privadas
contra el decoder y el oráculo de [CF-T5b](f03-04-collision-polygons-verification.md),
con el contrato [CP01–CP15](../../schemas/ps2-cld-polygons-v1.md) intacto.
La custodia y el enlace con el escenario continúan las evidencias de
[CF-T1–T3](f03-04-collision-shapes-research.md).

## Resultado por recurso

Se leyeron 285 recursos en cada copia: **570 archivos**, 2.690.720 bytes
por copia. Cada archivo coincide en tamaño y SHA-256 con el catálogo F02.04,
el recibo de extracción F02.05 y el inventario estructural CF-T1–T3.
Las parejas A/B también se compararon por bytes completos.

| Clasificación | Copia A | Copia B | Criterio |
|---|---:|---:|---|
| Aceptado | 233 | 233 | Vista completa del decoder idéntica a la del oráculo |
| No soportado | 52 | 52 | `CP_NONPOLYGON_UNSUPPORTED`: grupo 4 con formas activas de 48 bytes |
| Rechazado por otro error | 0 | 0 | Resto de errores tipados CP |

No hubo diferencias entre lectores ni entre copias. Los 52 recursos no
soportados quedan registrados completos, sin vista parcial y con el código
de ambos lectores. La clasificación conserva el primer error según la
precedencia del contrato: **no certifica los campos posteriores de un recurso
no soportado**. No se quitaron formas ni se ampliaron límites para aceptarlos.
`CP_VARIANT_UNSUPPORTED` también pertenece a «no soportado», pero solo aparece
en un control alterado, no en el corpus original.

Los 233 aceptados contienen **20.703 polígonos**: 1.642 triángulos y 19.061
cuadriláteros, con 20.900 referencias en las listas. Se comparó la vista
completa: palabras, coordenadas, tipos, signo del cero, offsets, terminadores,
orden y multiplicidad de referencias. Además, los contadores por grupo y
celda coinciden con el sondeo histórico independiente.

Se conservan los dos polígonos no referenciados del subconjunto aceptado:
índice 1 de los grupos 1 y 3 de `cc52.cld`. El sondeo anterior contó cuatro
en el corpus completo; los otros dos pertenecen a recursos no soportados
por este perfil. No se confunden referencias repetidas con nuevas formas
ni se eliminan registros que las listas no usan.

## Comparación con RAM conservada

Los dos recursos del carrusel son aceptados en A, B y RAM:

| Recurso | Bytes | Polígonos por grupo 0–4 | Dirección RAM | Muestras |
|---|---:|---|---|---|
| `tp1e.cld` | 19.552 | 10 / 0 / 105 / 105 / 0 | `0x0185FA00` | Slot 02, control del acertijo, sala `0xEA` |
| `tp1d.cld` | 11.984 | 1 / 0 / 49 / 80 / 0 | `0x0163FA00` | Slots 08–35 continuos y 36 diagnóstico restaurado, sala `0xEB` |

Identidad completa, sin depender del nombre:

- `tp1e.cld`: SHA-256 `1d5dee726af37e25e4e2687b0380a507abbf9473123c33f185b816b84523c751`.
- `tp1d.cld`: SHA-256 `506c5140ede39d21541acc5568271f3da7dacc3f08a047db9e15bb79a3deb793`.

En las **30 capturas** se verificaron nuevamente pins del estado/recibo,
CRC, PC, ciclo y procedencia; sala y escenario; habilitación y tabla de
registro en `0x01D0A7F0`/`0x01D0A800`; puntero/tamaño del cargador en
`0x00408B60`/`0x00408B64`; selección de recurso/celda en `0x01D051A0`.
Solo la celda 0 contiene referencias en estos dos recursos.

El buffer íntegro de RAM coincide con la extracción. Ambos lectores producen
la misma vista completa y esta coincide con la vista de las fuentes A/B.
Se conserva la distinción **1 control, 28 capturas continuas y 1 diagnóstico
restaurado**. Se vuelve a examinar evidencia guardada; no se ejecutó PCSX2
ni se creó una nueva secuencia continua. Tampoco se repitió aquí el cotejo
de ventanas ELF/overlay ni la investigación de listas dinámicas.

## Custodia, controles y reproducción

El coordinador local separa lectura con pins, evaluación de ambos lectores,
resumen de metadatos y comprobación del enlace RAM. No añade I/O al decoder.
Al terminar vuelve a leer las **643 fuentes consumidas**: 570 recursos,
60 estados/recibos, siete documentos de entrada y seis archivos fijados de
CF-T5b. También fija y comprueba los 58 archivos del coordinador y sus
importaciones locales. No modifica originales privados ni los paquetes IR-T7.
La ISO no se relee: la identidad procede del catálogo y recibo fijados.

Dieciséis controles en copias de memoria detectan:

- Truncamiento, stride inválido, variante no soportada, coordenada no finita,
  terminador alterado e índice fuera del grupo: ambos lectores devuelven
  exactamente el código esperado.
- Hash/tamaño incorrectos y corrupción de una palabra opaca: falla la custodia.
- Registro de recurso, tamaño del cargador, celda, sala o buffer RAM alterados:
  falla el cotejo del enlace.
- Coordenada de la vista cambiada o referencias reordenadas: falla la
  comparación completa contra el oráculo.

No se agregan esos controles a los conteos del corpus original. Una segunda
ejecución completa bajo `python -O` produce un recibo **idéntico byte por byte**.
Un verificador separado, sin importar el coordinador ni los lectores,
reconcilia inventario, pins, copias, códigos, sumas, referencias no utilizadas,
capturas y controles. Ruff/formato del auxiliar, custodia/arquitectura/EARS,
enlaces documentales y `git diff --check` pasan.

El comprobante detallado está en
`reports/local/f03-04-collision-polygons-private-v1.json`:
**1.261.623 bytes**, SHA-256
`319f9770751c525d93b1593e067d43ad755b7783a2b674316d7131b3c7d44a40`.
Contiene las 285 filas con ID, etiqueta, contenedor, tamaño, hash,
clasificación/códigos por copia y, para aceptados, hash de vista y contadores.
Incluye pins, capturas y controles; no incluye buffers ni coordenadas privadas.
`status=pass` acredita el cotejo, no aceptación de todos los recursos.
Se mantiene `capabilities=[]`.

Auxiliares locales ignorados por Git, separados de CI:

- `build/cld-polygons/cf-t6/audit_private.py`, SHA-256
  `9fc622cc4d4de2cd4ec85db95a43659b7907306d4d624dfc41abd29f498293cd`.
- `build/cld-polygons/cf-t6/verify_report.py`: reconciliación del recibo publicado.
- `build/cld-polygons/cf-t6/repeat-optimized.json`: repetición idéntica bajo `-O`.

```sh
# Sin --output: relee y verifica; solo imprime el resumen y hash del recibo.
rtk proxy .venv/bin/python build/cld-polygons/cf-t6/audit_private.py
rtk proxy .venv/bin/python -O build/cld-polygons/cf-t6/audit_private.py
rtk proxy .venv/bin/python build/cld-polygons/cf-t6/verify_report.py
```

`--output <ruta-nueva>` crea un recibo exclusivo con permisos `0600` y rechaza
sobrescribir un archivo existente. La reproducción requiere las fuentes
privadas fijadas y los auxiliares locales; CI sigue usando solo sintéticos.
Decoder, oráculo, constructor, vectores y tests mantienen los pins de CF-T5b.
No se repitió la suite completa de 8.307 pruebas ni CI remoto: esa evidencia
corresponde a [CF-T5c](f03-04-collision-polygons-ci.md).

## Siguiente tarea y límites

**CF-T7:** definir primero el contrato separado para fuente íntegra, vista
poligonal, procedencia y reconstrucción desde paquetes; después integrar y
comparar publicaciones A/B. El perfil de registros IR-T7 permanece intacto.
Este cotejo no produce build del visor ni valida solver, respuesta física,
formas activas de 48 bytes, listas dinámicas, daño o muerte. No cierra
F03.04 global ni G02/G03.
