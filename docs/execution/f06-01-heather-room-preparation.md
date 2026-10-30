# HM-T4b.3 — Preparación y cotejo privado de contactos

2026-10-29. **HM-T4b.3 y HM-T4b completadas.** Se prepararon y releyeron dos
paquetes hp34 idénticos desde fuentes privadas A/B: CLD íntegro, vista de los
34 registros, suelo y 32 cajas con bits originales. El spawn y los cinco
tramos pasan en ambos sentidos frente al oráculo independiente y al núcleo/
puerto C++. Sigue **HM-T4c.1: datos y render compartidos**. La habitación aún
no está integrada al bucle ni se ha publicado o probado un nuevo `.3dsx`.

## Entrega y custodia

- [Conversor](../../tools/pipeline/heather_room_contacts.py),
  [preparador](../../tools/pipeline/prepare_heather_room_contacts.py) y
  [contrato del paquete](../../schemas/heather-room-contacts-package-v1.md).
- Carpetas privadas: `/Users/germancontreras/sh3-private-data/heather-room-contacts-v1-copy-a`
  y `/Users/germancontreras/sh3-private-data/heather-room-contacts-v1-copy-b`.
  Creación exclusiva, directorios 0700 y archivos 0600. No se reemplazó ningún
  paquete anterior ni se copiaron payloads privados al repositorio.
- Se fijaron perfil, catálogo y recibo, y se comprobaron tamaño/hash,
  procedencia e igualdad de mapa/CLD/textura externa en ambas copias antes
  de decodificar. Se revalidaron después de escribir y al finalizar el cotejo.
- Se conservaron 34 roles: un suelo, un techo excluido de las consultas y
  32 bloqueadores. La vista completa retiene listas, offsets, flags y XYZW;
  el CLD preserva también los bytes que no interpreta esa vista.

Cada copia contiene 34448 bytes de datos, más el manifiesto y su enlace
pendiente. Los cuatro archivos coinciden byte a byte entre copias:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `source.cld` | 3920 | `e49f5c97048fe95dd9109413bc37c854078fd0defeead3d4dbdbf8acdbfbaff0` |
| `room-profile.json` | 3585 | `5838c4b445a0da3f4a2636ac9c9e61edfe754dc89b33d25db33284581212e531` |
| `polygons.json` | 22409 | `6dd9fbbc20473bd22f6544ea989e31e2bb7164f4afc7494787858447854bbe47` |
| `contacts.json` | 4534 | `3047fe8cc887e8cdb7f3b7f386cbc023e5fff29eef89761eb25f8ab82a42055c` |

La publicación es individual por copia; la pareja se acepta tras releer
ambas. Una interrupción durante B puede conservar A completa, pero no produce
un resultado exitoso de pareja. Los fallos previos al commit impiden el
manifiesto final. La salida alterada se rechaza por reconstrucción desde el
CLD fijado, aunque se modifique también su manifiesto.

## Cotejo independiente

[Auditor](../../tests/heather_room_private_audit.py) y
[proyección/oráculo](../../tests/heather_room_preparation_oracle.py):

1. Lectura CLD independiente, comparación completa de árboles tipados y bits,
   proyección independiente de las 32 cajas, suelo y roles.
2. Oráculo racional por intersección con lados, independiente del barrido
   entero C++. Spawn válido y cinco segmentos continuos libres, también
   probados en sentido inverso. No se usan solo muestras de los extremos.
3. Cien consultas por copia: 14 libres, 39 bloqueadas, 40 inicios inválidos,
   tres no finitas, dos con Y discordante, una fuera de rango y una indisponible.
   Incluyen las 32 cajas individualmente, los cuatro límites abiertos del
   suelo, tangencia cerrada y un ULP a cada lado de la pared.
4. Cuatrocientas comparaciones nativas: 100 × A/B × Release/sanitizadores.
   Se comparan códigos, puerto y todos los bits de salida. El ejecutable
   también verifica centinelas, aliasing, repetición, escena inmutable y
   ausencia de asignaciones durante preparación/consulta.
5. Relectura de paquetes publicados y fuentes al terminar; auditoría normal
   y `python -O` con informes idénticos. Las condiciones del auditor no
   dependen de `assert` eliminables.

El punto propio al otro lado de la pared usado como negativo está ocupado:
se rechaza como inicio inválido; desde el spawn, la consulta hacia él bloquea.
El cruce con ambos extremos libres se verifica separadamente con geometría
inventada en el CTest de preparación y los vectores HRC.

Informe local de metadatos: `reports/local/f06-01-heather-room-preparation.json`.
Conserva hashes del código, ejecutables y datos cotejados, sin coordenadas
extraídas ni payloads. Repeticiones y compilación:
`build/heather-room/preparation-v1/`.

## Pruebas y compilación

- 66 pruebas nuevas de conversión, identidad, corrupción, entradas no regulares,
  publicación, cambios de fuente y fallo de la segunda copia; **4023 pruebas
  Python relacionadas aprobadas** en el conjunto CLD/contactos/preparación.
- Gate independiente de líneas/ramas ≥80/80, añadido a CI por archivo:
  conversor **74/74 y 12/12 (100/100)**; custodia/publicación **111/112 y
  19/20 (99,1/95)**. Solo queda fuera la entrada `__main__` en esta medición;
  la CLI real se ejecutó al publicar A/B.
- CTest de contactos: **4/4 Release** (incluye pila), **3/3 ASan/UBSan**.
  La preparación sintética recorre la cadena CLD → conversión → oráculos →
  núcleo/puerto; las regresiones HRC conservan los 894 casos exactos previos.
- **17/17 CTest GCC** relacionados aprobados en contenedor sin red. Cobertura
  C++: núcleo **154/154 líneas y 188/194 ramas (100/96,9)**; adaptador
  **7/7 y 4/4 (100/100)**.
- Compilación ARM nueva de `sh3_domain`, `sh3_application` y `sh3_diagnostics`,
  ELF32 ARM EABI5 verificado. Imagen fijada:
  `devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
  Fuentes montadas en solo lectura, sin activos privados en el contenedor.
- Se mantienen las reservas HRC de **576 + 2560 = 3136 bytes**. El gate ARM
  conserva **2116 bytes de pila conservadora + 576 residentes = 2692 bytes**;
  GCC host, **2944 bytes**. El análisis incluye grafo de llamadas y reserva
  externa. Objetos ARM: núcleo 3932 bytes de texto y adaptador 272; ambos
  sin `.data` ni `.bss`.

La compilación acredita compatibilidad ARM, no ejecución del recorrido en
consola. No hubo nueva captura de VM, validación física, cambio de materiales,
encuadre de cámara ni integración del lector/bucle. Las cajas son el perfil
conservador propio definido en HR/HRC; no acreditan la física general PS2.

## Reproducción local

Desde la raíz del repositorio, con fuentes privadas disponibles:

```sh
rtk proxy .venv/bin/python tests/heather_room_private_audit.py \
  --profile "$PWD/schemas/heather-room-profile-v1.json" \
  --catalog "$PWD/reports/local/f02-04-asset-catalog.json" \
  --receipt /Users/germancontreras/sh3-private-data/f02-05/verified.json \
  --copies /Users/germancontreras/sh3-private-data/f02-05 \
  --native "$PWD/build/host-release/test_room_contacts" \
  --native "$PWD/build/host-sanitize/test_room_contacts" \
  --bundles /Users/germancontreras/sh3-private-data
```

Para la repetición optimizada, añadir `-O` inmediatamente después de `python`.
El comando solo lee fuentes/paquetes y emite metadatos. La publicación inicial
usó `tools.pipeline.prepare_heather_room_contacts`, los mismos cuatro inputs,
`--private-root /Users/germancontreras/sh3-private-data` y
`--run-prefix heather-room-contacts-v1`; repetirla rechaza carpetas existentes.
