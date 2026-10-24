# F03.04 / CF-T7a — Contrato intermedio y reconstrucción sintética

2026-10-23. **CF-T7a completada**: [contrato CPI01–CPI14](../../schemas/collision-polygons-intermediate-v1.md)
y [ejemplos públicos propios](../../tests/fixtures/synthetic/collision-polygons-intermediate-v1.json)
comprobados por reconstrucción independiente. CF-T7 continúa con su adaptador,
preparador, batería de integración y publicación privada; esas etapas no
quedan acreditadas por esta comprobación del contrato.

## Decisiones fijadas

El perfil `ps2-cld-polygons-intermediate-v1` conserva un CLD completo por ID,
una vista JSON por aceptado, la fila completa del catálogo y referencias
históricas con pins. El buffer original es la autoridad para reconstruir;
la vista no sustituye padding, palabras opacas ni datos sin referencias.
No se deduplican recursos de distinto ID aunque sus bytes sean iguales.

Los recursos no soportados y rechazados conservan buffer y primer código CP,
sin vista parcial. Un hash incorrecto frente a la fuente aborta la importación,
en lugar de convertirse en un rechazo estructural. El decoder CP permanece
intacto, al igual que el intermedio de registros IR-T7.

Las vistas se separan por recurso para respetar el codec compartido de
8 MiB/500.000 nodos por árbol. El nuevo perfil limita raíz y vista a 1 MiB
cada una, manifiesto a 256 KiB y salida lógica a 40 MiB. Un ejemplo sintético
con 768 polígonos y 4.096 referencias produjo una vista canónica de 386.968
bytes; es una comprobación de viabilidad, no una prueba exhaustiva del límite.
Se especifican inventario dinámico, nombres derivados del ID y tratamiento
del enlace auxiliar `.manifest.pending.json` del writer actual.

La procedencia evita rutas del host. Los pins históricos no se recalculan
desde metadatos recodificados. Los enlaces de escena son referencias al
informe fijado, sin volver a ejecutar PCSX2 o seguir direcciones de RAM.
El lector de paquetes verifica coherencia interna; el cotejo con fuentes
originales es una comprobación adicional explícita.

El comprobante CF-T6 se volvió a verificar por tamaño/hash antes de usarlo
para diseñar la receta: 1.261.623 bytes, SHA-256
`319f9770751c525d93b1593e067d43ad755b7783a2b674316d7131b3c7d44a40`.
Sus 285 recursos, 233/52/0 y 30 capturas son evidencia anterior; no se volvió
a leer el corpus privado durante CF-T7a. La futura publicación A/B deberá
reproducir esos resultados y verificar sus 519 archivos lógicos más manifiesto.

## Ejemplos y resultado observado

El fixture materializa **24 paquetes de ejemplo** con bytes, tamaños y hashes
de cada archivo. El caso base tiene siete recursos: tres aceptados (incluido
un mismo CLD bajo dos IDs), dos no soportados y dos rechazados por CP. Son
11 archivos lógicos y un manifiesto, **36.115 bytes** en total.
Los buffers provienen exclusivamente de los vectores propios CF-T4; sus
expectativas aceptadas se conservan, no se generan con el decoder de producción.
Los documentos de procedencia son propios y usan `kind=synthetic`.

El verificador local usa stdlib y el oráculo CP independiente existente.
No importa el generador ni módulos de producción. Vuelve a interpretar CLD,
regenera vistas, reconstruye la raíz y el manifiesto y compara todos los bytes.
Durante reconstrucción, un audit hook rechaza cualquier apertura de archivo;
un intento deliberado confirma que ese bloqueo está activo. Los buffers
necesarios se suministran en memoria antes de activar el bloqueo.

| Casos | Resultado |
|---|---|
| `CPI-V01` | Paquete reconstruido íntegro; buffers y filas de catálogo coinciden con los originales propios. |
| `CPI-E01`–`CPI-E21` | 21 alteraciones rechazadas con el código esperado. |
| `CPI-V02` | Padding alterado y hashes coherentemente recalculados: paquete reconstruible, pero el cotejo externo detecta diferencia de fuente. |
| `CPI-V03` | Metadato desconocido cambiado de booleano a entero: paquete reconstruible, fuentes binarias iguales, cotejo externo de catálogo detecta diferencia. |

Los dos últimos controles son positivos de **coherencia de paquete**, no de
fidelidad histórica. Evitan prometer autenticación a partir de un manifiesto
que pudo cambiar junto con sus datos. La futura auditoría privada debe exigir
también la igualdad con las fuentes fijadas, incluidos campos desconocidos.

Los 21 rechazos cubren archivo ausente/extra, corrupción, versión booleana o
float, perfil/claves inesperados, orden/duplicación de IDs, ruta indebida,
cambio del signo de cero, reordenación de referencias, forma eliminada,
tipo de palabra cambiado, cuarto vector alterado, hash de catálogo incoherente,
código/clasificación falsos, claves JSON duplicadas y codificación no canónica.
Los casos de vista tienen hashes y manifiesto actualizados para que la
comprobación semántica, y no solo el hash, detecte el fallo.

Resultado: **3 paquetes coherentes reconstruidos y 21 inválidos detectados**,
con resultados idénticos en modo normal y `-O` (24 casos por modo).
El generador reproduce exactamente el fixture. No se atribuye cobertura de
un adaptador de producción: todavía no existe. Fronteras exhaustivas,
evidencia privada, fallos de I/O y concurrencia quedan en CF-T7b–e.

## Artefactos, comprobaciones y continuación

Fixture público: **1.842.068 bytes**, SHA-256
`7101765a39b0b3ccee3930e0f48730af9d6ed8444b3bbd9efdfc131f0ba58446`.
Contiene datos y resultados, por lo que su uso futuro en CI no dependerá del
generador local. Los auxiliares ignorados están en
`build/cld-intermediate-contract/generate.py` y `verify_examples.py`.
Comprobante local de metadatos:
`reports/local/f03-04-collision-polygons-intermediate-contract-v1.json`.

```sh
rtk proxy .venv/bin/python build/cld-intermediate-contract/verify_examples.py
rtk proxy .venv/bin/python -O build/cld-intermediate-contract/verify_examples.py
rtk proxy .venv/bin/python -m tools.qa.check_repository
```

Ruff/formato de los auxiliares, comprobaciones de custodia/arquitectura/EARS,
enlaces documentales y `git diff --check` pasan. Se verifican los seis pins
de decoder, oráculo, constructor, vectores y tests CF-T5b: permanecen intactos.
No se ejecuta de nuevo la suite completa ni CI remoto, ni se cambia el workflow
para añadir módulos inexistentes. El contrato fija sus gates y pruebas futuras.

**Siguiente: CF-T7b**, implementar el adaptador puro y sus tres APIs con
errores tipados, regeneración de vistas y reconstrucción desde bytes suministrados.
Después: CF-T7c preparador/writer, CF-T7d oráculo ampliado/CI, CF-T7e publicación
y reconstrucción privadas A/B. No se habilita respuesta física ni se prepara
un nuevo build del visor en esta etapa.
