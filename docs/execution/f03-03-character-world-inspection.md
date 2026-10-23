# GC-T5 — Tres colocaciones del caballo en el visor

2026-10-23. Build **`abe9a7a35464`**, aplicación **SH3 world placement**.
**GC-T5a–f completadas para este visor**; aceptación funcional y métricas aproximadas
reportadas por el usuario. [Contrato EARS GCI01–GCI06 y tareas](../specs/sh3-3ds/character-world-inspection.md).

## Comportamiento y responsabilidades

El visor coloca tres copias del caballo con las matrices del estado 08 de
[GC-T4](f03-03-character-world.md), identificadores 398, 399 y 400. Comparte
el clip `0x1449`, tres texturas y luz neutra. Las colocaciones quedan fijas:
no reproduce la trayectoria del carrusel, IA, combate ni iluminación de escena.
El reloj de inspección comienza en Q12=0; el estado fuente tenía Q12=66220
para los tres actores. No se restaura esa sesión en el emulador PS2.

El dominio calcula colocación; el lector SCW1 comprueba el contrato y publica
solo después de cerrar correctamente el archivo; el preparador verifica
SHA-256 de informes, estado, manifiestos y recursos residentes. El presentador
deforma una malla y coloca tres instancias. El renderer recibe tres bloques,
comparte texturas y espera la propiedad del buffer antes de copiarlo.
La validación de modelo/mundo precede al uso inmutable durante reproducción.

SCW1 ocupa 264 bytes y enlaza los CRC de SCM/SAN/SCT. Valida rigidez, valores
finitos, tres identificadores distintos y encuadre común. La colocación conserva
W y aplica la base B después del modelo. El cálculo `R*p+(T-origin)*w` evita
restar posiciones grandes por vértice; origen y escala son comunes a las tres
instancias. La esfera conservadora incluye factor 1,004 por la tolerancia rígida.

Se dibujan 4.365 vértices únicos / 3.339 triángulos, nueve llamadas de dibujo,
un buffer GPU de 360.612 bytes y tres texturas de 3 MiB en total. No hay
asignación ni lectura de archivos por cuadro. A/R/L, cámara, START y ciclo de
vida usan el comportamiento existente. La pantalla separa **Skin CPU**,
**Place CPU**, **Submit+wait** y **GPU previous**; Submit incluye espera y no
se suman esos valores para deducir FPS. Previsualización: 25 evaluaciones/s.

## Verificación local

| Comprobación | Resultado |
|---|---|
| Python relacionado | 198 tests aprobados (192 relacionados + 6 del script nuevo); encoder/preparador 93,79 % combinado de líneas/ramas; gate aprobado |
| C++ Release y ASan/UBSan | 166 pruebas render y unidad de material aprobadas en cada configuración |
| SCW1 independiente | Fixture válido, 27 corrupciones y tres fallos I/O; publicación transaccional |
| Renderer compartido | 24 escenarios adicionales de tres instancias; fallos de inicio, propiedad GPU, envío y datos inválidos |
| ARM | Visor nuevo y tres anteriores compilados con SDK fijado, sin red, copia de código sin recursos privados |
| PICA | Gate aprobado, 12 componentes escritos una vez; mismo shader corregido |
| Preparación privada A/B | Ocho salidas y metadatos idénticos; SCW coincide con el contrastado |
| Calidad | Ruff, formato, contratos del repositorio y diff aprobados |

Precisión: **240.075 colocaciones** usando 28 estados, 24 poses enteras y
cuatro poses fraccionarias adicionales en el estado fuente. Error máximo
**0,000331778** frente a doble sobre los mismos vértices ya deformados en f32;
límite fijado previamente **0,001 unidades originales**. La variante que suma
primero la traslación grande alcanza 0,012360573 y falla en 197.225 colocaciones.
Este resultado mide exclusivamente colocación relativa al origen: no acredita
precisión total de pose/skinning, equivalencia EE/VU, rasterización ni pantalla.
Las limitaciones numéricas GC-T4 y las tolerancias CM se conservan.

Auditor local `build/character-world/precision.py`, SHA-256
`d9afbd5f048601c2a279f104507d872378b9b68337a06b2e27f132258777efc7`.
Informe privado `f03-03-character-world-inspection-v1/precision.json`, SHA-256
`934237c01e9f2480f71d65d1cdc4e66024b7323d4df7760f7f1f86df2a17fe76`.
Informes locales: `build/character-world/{pytest.xml,coverage.json,arm-build.log,arm-regression.log,build-script-tests.xml}`;
JUnit C++ `build/host-{release,sanitize}/character-world-tests.xml`.
No se ejecutó CI remoto. El job existente compila el target nuevo y publica
solo binarios de código y metadatos, sin recursos privados.

Docker dejó de responder durante el primer intento, que no produjo salida.
Tras el reinicio autorizado, la compilación y las regresiones finalizaron.
No se borraron imágenes ni volúmenes. La copia compilada coincide con el
inventario de fuentes `build/character-world/source-inventory.json`.

## Validación en Azahar

Azahar 2126.2 Vulkan mostró los tres caballos texturados en colocaciones
separadas. Dos observaciones con **70,553 segundos** de reproducción entre
ellas registraron Q12 **10866 → 31060**, sin bloqueo observado. Son capturas
puntuales, no un vídeo continuo. A pausó y reanudó; L devolvió Q12 a 0 en
pausa; R avanzó a 3686. Las cuatro direcciones y X/Y modificaron la cámara;
B restauró 0,35 / 0,35 / 4,00. START regresó a la lista de aplicaciones.
El encuadre común deja los caballos pequeños: X permite acercarse.

Lecturas ilustrativas: Skin 4,99 ms, Place 8,99 ms, Submit+wait 16,01 ms,
GPU previous 0,25 ms. Son valores del emulador, no rendimiento de 2DS XL.
En esa etapa, tapa/HOME y aceptación física estaban pendientes. La copia al perfil
portátil conservó por hash los 34 archivos preexistentes. No se modificó
la configuración del emulador. La entrega posterior a SD se registra abajo.

Capturas privadas: `f03-03-character-world-native-check-v1/`.
SHA-256 de `ui-receipt.json`:
`55a640218c23f9376e2703d5de392f9ce020c9272fde86e0067139aa8741e0cc`.

## Entrega

Directorio privado:
`/Users/germancontreras/sh3-private-data/f03-03-3ds-character-world-v1/`.
El ZIP crea `/3ds/sh3_character_world_probe/` con siete archivos y conserva
los visores anteriores. [Protocolo físico y estado](../compatibility/character-world-inspection.md).

| Artefacto | SHA-256 |
|---|---|
| manifest.json | `98a0a130b1d4bec9df09655c37f4a63bc12944e2e30422b02e6cc6cc58321f53` |
| sd-card.zip (3.492.399 bytes) | `35c5565945ae6008d247ca99b6c0820b592c24cfc79ebc9ae2f1830dba360615` |
| 3DSX (280.664 bytes) | `4d0b552b35fcd9db37801be6500d8ebc9522f44ab21510ad6e84b73ce67a7722` |
| character.scw | `33885ccd954c413887761824be79ab4d11a6bce8d61a729d31069d8a90965ddd` |

Entrega posterior, 2026-10-23: build copiado a SD NO NAME, siete archivos /
3.490.287 bytes verificados por lectura posterior; 56 archivos anteriores
conservados. Expulsión segura confirmada. Comprobantes y hashes en el
[registro físico](../compatibility/character-world-inspection.md).

Aceptación posterior: el usuario confirmó 60 segundos, tres caballos texturados
y animados, controles, START, tapa y HOME. **GC-T5f.1 aceptada**.
**GC-T5f.2 completada** con lecturas aproximadas: Skin 14,25 ms, Place 26,9 ms,
Submit+wait 35,50 ms y GPU previous 2,39 ms. No se comunicaron cámara/zoom ni
una serie temporal. No se deduce FPS sumando las lecturas. Véase el registro
físico para alcance y ambos comprobantes.

Siguiente paso: [F03.04, intermedio y reconstrucción del perfil verificado](f03-04-character-intermediate.md).
F03.03 global, G02/G03, daño/muerte, mezclas, movimiento de raíz, colisión,
selección de luces y un circuito jugable siguen pendientes. Las métricas
físicas LI-T4f.2 y CT-T5e.2 permanecen separadas, sin medir.
