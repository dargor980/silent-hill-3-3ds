# HM-T4c.1 — Datos, materiales y preparación del render compartido

2026-10-29. **HM-T4c.1 completada.** Las copias privadas A/B contienen las
31 formas de hp34, Heather SRI2 original, trece materiales de Heather y el
vidrio comprobado. Las otras **29 formas conservan toda su geometría con
material neutro de diagnóstico**. Transformación, orden, encuadre y presupuesto
están cotejados. La integración posterior del bucle y ciclo de vida se cerró
en [HM-T4c.2](f06-01-heather-room-runtime.md); este informe conserva la evidencia
de preparación c.1. La entrega `.3dsx` se cerró en
[HM-T4d](f06-01-heather-room-delivery.md); aceptación física pendiente.

## Entrega

- [Contrato HRS/SRM1](../../schemas/heather-room-scene-v1.md),
  [perfil de render](../../schemas/heather-room-render-v1.json),
  [conversor](../../tools/pipeline/heather_room_scene.py) y
  [preparador/relector](../../tools/pipeline/prepare_heather_room_scene.py).
- [Núcleo de fotograma](../../engine/domain/room_scene.cpp),
  [lector acotado](../../engine/platform/common/room_scene.cpp) y
  [estados Citro3D](../../engine/platform/3ds/render/room_material_state.cpp).
- Paquetes nuevos: `/Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-a`
  y `/Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-b`.
  **26 archivos de datos, 23551610 bytes por copia**, más manifiesto y enlace
  pendiente. Creación exclusiva 0700/0600; fuentes y paquetes anteriores intactos.
- Contactos HM-T4b.3 incorporados sin cambios: CLD completo, perfil, vista
  poligonal, 32 cajas y suelo. MAP/TEX crudos y atributos no interpretados
  permanecen en el paquete privado. No se copiaron payloads al repositorio.

El preparador verifica catálogo, recibo y las seis fuentes MAP/CLD/TEX A/B,
manifiestos y catorce archivos SRI2 por copia, y referencia MR de vidrio.
Reconstruye los datos preparados antes de publicar y después de releer ambas
copias. La auditoría vuelve a comprobar fuentes y paquetes al finalizar.

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `map.srm` | 1004928 | `9d4111c13d5dce370f8e7dcb11389f9fd9bbcb0415c5f09ac2d3a77615ca1944` |
| `map-view.json` | 1628946 | `ac4fc9cd04fe28b015b2afd137ae0e98f6b157d2c86a86b1d0b88d5620360b23` |
| `render-profile.json` | 718 | `4c0bae6ac831a6045dc6903fbe09a084f82c137c324080d7fca14a0ee01123e0` |
| `glass.rgba` | 262144 | `ac0eb5614da6041a0a2b8be83991b247ce34fdd39be18178c9a8d6dfa41eaaab` |
| `heather.sri` original | 290156 | `2bc96e9f7fec9e52b21186d033ee02694b67808098bf101d304fd944c928fc0b` |

## Transformación, materiales y orden

La vista conserva 15882 vértices fuente y 9300 triángulos de las 31 formas;
SRM1 expande 27900 vértices. Se incluyen el techo y los fondos. Heather
mantiene 36 huesos, 49 helpers, 58 muestras, 6943 vértices, 16566 índices,
13 materiales y clips 101/109/113, MDL522/ANM525.

El mapa recibe T(O) una vez y Heather recibe T(P)·Ry(yaw) una vez, después
del skin local. Ambos usan O=(100000,0,140000), B=(1,-1,-1) y escala 0.002F.
Se preservan los pesos Q12 y W; no se aplican el centrado, escala ni giro Z
del visor aislado. La cámara comparte la misma base.

Primero se emiten las 29 formas neutras y los doce materiales opacos de
Heather. Después se ordenan juntos los 32 triángulos de vidrio y los 240 de
cabello, de lejos a cerca, con desempate explícito. La lista puede intercalar
ambos materiales: no se fuerzan dos pases transparentes globales separados.
Vidrio y cabello prueban profundidad sin escribirla. Los estados se vuelven
a establecer en cada cambio de pase, incluidas mezcla, culling y alpha test.
El criterio de centroide es diagnóstico; no resuelve toda intersección
transparente posible ni acredita equivalencia visual con PS2.

El [oráculo independiente](../../tests/room_scene_oracle.py) recorre enlaces
y strips del MAP por su cuenta; reconstruye SRI2, jerarquía, helpers y skin
con otro cálculo escalar, deriva la base común y el orden. No importa el
conversor de geometría ni el núcleo C++. Compara todos los vértices del mapa,
rangos, atributos, W y posiciones del frame capturado por C++.

**472 cotejos privados aprobados:** 118 casos × A/B × Release/ASan-UBSan.
Incluyen las 58 muestras originales en spawn y cada extremo del recorrido
con los tres clips y cuatro orientaciones. Error máximo XYZ: **4.76837158203125e-7**
unidades render, bajo el límite 2e-5; atributos/W y rangos coinciden exactamente.
Se repitió la auditoría con `python -O`: otros 472 casos e informe idéntico.
No se basa en `assert` eliminables. Esto no acredita ejecución ARM ni un
replay integrado del controlador, que corresponde a HM-T4c.2.

## Encuadre y oclusión

El encuadre inicial HR (objetivo Y=-550, FOV70) falla: margen mínimo
**−0.5022807772** y 173559 semiespacios de vértices fuera. Se conserva ese
resultado. Alejar el ojo mejoraba el frustum, pero interponía una pared;
se descartó. No se retiró el techo ni otra forma para obtener visibilidad.

El refinamiento mantiene el ojo local **(275,-1000,-700)**, baja el objetivo
a **(275,-300,100)** y usa **FOV80**, near/far 0.02/12 y viewport 400×240.
Está en un perfil nuevo; el JSON HR fijado conserva su SHA-256 original.

[Auditor visual](../../tests/room_scene_visual_audit.py): **232 poses muestreadas**
(58 muestras × cuatro fracciones), seis extremos contando spawn y retorno,
seis planos del frustum. El mínimo para todos los yaw se obtiene analíticamente
y la traslación de cada segmento es continua. Resultado: **cero fallos**,
margen mínimo **+0.1698148134**. Esto cubre esas poses muestreadas, no demuestra
todos los tiempos continuos entre muestras de animación.

Se revisaron cuatro vistas software de spawn, caminar y correr en extremos
cercano/lejano y giros. El ray test contra las 29 formas neutras, de dos caras,
deja visibles 128/129, 128/129, 128/129 y 129/129 puntos del actor. Las vistas
contienen respectivamente 2850, 3393, 1533 y 2758 píxeles de Heather. Se usan
el plan nativo, texturas originales, clipping de seis planos, UV en perspectiva,
profundidad y alpha. No son capturas PICA ni prueba de filtrado píxel a píxel.

Lámina privada revisada:
`/Users/germancontreras/sh3-private-data/heather-room-scene-visual-v1/contact-sheet.png`.
El neutro plano no reproduce detalles/iluminación de las 29 superficies;
su etiqueta está preparada para la futura pantalla. No se afirma que todas
las formas estén simultáneamente dentro del encuadre.

## Memoria y pruebas

Presupuesto conservador del plan: **40190596 bytes, 38.33 MiB de 64 MiB**.
Incluye CPU/VBO estáticos y dinámicos, modelo/scratch, staging de lectores,
2 MiB de staging de textura, reservas de controlador/contactos y 12 MiB de
plataforma. Texturas residentes previstas: **17.5 MiB**, sin expandir las
variantes internas pendientes del mapa. No es un pico real medido en consola.

ARM confirmó `sizeof`: RoomMap=1004908, RoomFrame=748728,
RoomWorkspace=535360, InspectionLocomotion=389640, vértice=36 y rango=16
bytes; coinciden con las estructuras usadas en el presupuesto host.
`room_frame` no asigna heap; el lector solo lo usa para staging de carga.
Errores de memoria, cabecera, CRC, lectura/cierre, geometría, pose o instancia
preservan la salida anterior; la memoria del scratch puede quedar parcial.

- **78 pruebas Python nuevas**, **1058 regresiones relacionadas** aprobadas.
- CTest: **73/73 Release**, **72/72 ASan/UBSan** (la prueba de pila de contactos
  solo se registra fuera de sanitizadores). Incluye regresiones de rig,
  locomoción, movimiento, contactos y espacio mundial.
- **3/3 CTest GCC** específicos: escena, oráculo sintético y estados de material.
  Fixtures inventados, sin fuentes privadas en CI ni contenedor.
- Gates por módulo ≥80 % de líneas **y** ramas, añadidos a CI:

| Módulo nuevo | Líneas | Ramas |
| --- | ---: | ---: |
| Conversor Python | 105/105 (100 %) | 18/18 (100 %) |
| Preparación/relectura Python | 114/115 (99.1 %) | 14/16 (87.5 %) |
| Núcleo C++ | 161/161 (100 %) | 168/176 (95.5 %) |
| Lector C++ | 68/68 (100 %) | 75/76 (98.7 %) |
| Estado Citro3D | 22/22 (100 %) | 5/5 (100 %) |

Compilación ARM de `sh3_domain`, `sh3_diagnostics` y `sh3_room_material`,
ELF32 ARM EABI5. Objetos nuevos: 6108/1399/220 bytes de texto; sin data/BSS.
Imagen fijada `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`,
sin red y fuentes en solo lectura. GCC detectó dos copias innecesarias en
bucles de prueba y ARM una promoción distinta de enteros en el presupuesto;
corregidas antes del resultado final. No se atribuye rendimiento a compilar.

Informe de metadatos con hashes de código, ejecutables y los 26 archivos:
`reports/local/f06-01-heather-room-scene.json`. Logs, JUnit, gates, objetos y
tamaños ARM: `build/heather-room/scene-v1/`. El informe no contiene mallas,
píxeles, poses ni coordenadas extraídas.

## Reproducción

```sh
rtk proxy .venv/bin/python -m pytest tests/python/test_heather_room_scene.py
rtk proxy cmake --build build/host-release --target test_room_scene test_room_material
rtk proxy ctest --test-dir build/host-release -R '^room_(scene|scene_oracle|material)$' --output-on-failure
rtk proxy .venv/bin/python tests/heather_room_scene_private_audit.py \
  --profile "$PWD/schemas/heather-room-profile-v1.json" \
  --catalog "$PWD/reports/local/f02-04-asset-catalog.json" \
  --receipt /Users/germancontreras/sh3-private-data/f02-05/verified.json \
  --copies /Users/germancontreras/sh3-private-data/f02-05 \
  --heather-a /Users/germancontreras/sh3-private-data/heather-locomotion-a-v1 \
  --heather-b /Users/germancontreras/sh3-private-data/heather-locomotion-b-v1 \
  --reference /Users/germancontreras/sh3-private-data/f03-02-material-reference-v1/reference.json \
  --bundle-a /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-a \
  --bundle-b /Users/germancontreras/sh3-private-data/heather-room-scene-v1-copy-b \
  --executable "$PWD/build/host-release/test_room_scene" \
  --executable "$PWD/build/host-sanitize/test_room_scene"
```

Añadir `-O` después de Python reproduce el cotejo optimizado. El auditor solo
lee y emite metadatos por defecto. El diagnóstico visual opcional requiere
NumPy/Pillow y `--preview-root` externo con un `--preview-name` nuevo; publica
exclusivamente una lámina privada. La publicación inicial de datos usó
`tools.pipeline.prepare_heather_room_scene` con esas fuentes y
`--private-root /Users/germancontreras/sh3-private-data --run-prefix heather-room-scene-v1`.
Repetir ese nombre se rechaza; no sobrescribe paquetes.

[HM-T4c.2](f06-01-heather-room-runtime.md) conectó el plan a las reservas/limpieza
GPU, CRC y upload de texturas, controles/tiempo, contactos, pausa/reinicio/HOME/tapa
y manejo de errores; el ejecutable completo compila para ARM. Siguen pendientes
los materiales originales de las 29 formas, la cámara PS2, la medición física
y las gates globales. [HM-T4d](f06-01-heather-room-delivery.md) cerró el empaquetado.
