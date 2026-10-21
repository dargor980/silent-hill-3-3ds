# F03.02 — Primera textura PS2 decodificada

2026-10-20. Completada la instancia **8 bits/cuatro unidades CLUT, salida privada
e inspección**. La comparación con el material dentro del juego original sigue
pendiente; F03.02 global, G02 y G03 no se cierran.
[Contrato PX01–PX07](../../schemas/ps2-texture-decode-v1.md),
[selección F03.01](f03-01-texture-structure.md) y
[matriz de cobertura](../reverse-engineering/format-coverage.md).

Continuidad posterior de esta fecha: [visor nativo y ZIP privado](f03-02-texture-inspection.md)
compilados y probados en Azahar; TI-T5 confirmada por el usuario en New 2DS XL.
La comparación del material PS2 permanece pendiente. El
[sondeo MAP posterior](f03-02-map-material-candidate.md) localiza geometría
candidata sin demostrar todavía la asociación.

## Resultado observable

La muestra seleccionada de 256×256 produce una imagen continua de una superficie
gris desgastada, sin cortes evidentes entre bloques durante la inspección del PNG.
Eso no identifica su sala, material, orientación UV en escena ni uso de alpha.
No se presupone que sea una puerta o una pared por su apariencia.

La paleta 0 tiene 256 colores RGBA distintos. En sus píxeles usados, alpha PS2
varía de 42 a 128; 3.463 píxeles alcanzan el límite de la normalización de vista.
Las paletas 1–3 son uniformes `0xCC`. Todas se conservan y se exportan, incluidas
las uniformes; el pipeline no elige silenciosamente una paleta para un material.

Cada copia privada de F02.05 generó 13 archivos de salida, idénticos byte a byte:
índices lineales, cuatro paletas RGBA originales, cuatro imágenes RGBA con alpha
original y cuatro PNG con `A=min(255,2*A_PS2)`. Los manifiestos también coinciden.
Total por sesión, sin manifiestos: 1.186.595 bytes. No se cambió el recurso ni se
añadieron imágenes del juego al repositorio, fixtures, build 3DS o artefactos CI.

## Identidad y custodia

Origen: perfil europeo SLES-51434/PAL 1.02. Recurso de 69.808 bytes, SHA-256
`65173379ae86c13512b0c546edf68ae3a82b79b7267f5b011a39d8d44ccf35e4`,
ordinal 0. Su ID completo se conserva en el manifiesto privado. Rangos recalculados
desde headers verificados: índices 128/65.536 bytes, CLUT 65.712/4096 bytes.
No se confía en offsets importados desde el informe anterior.

| Salida | SHA-256 |
|---|---|
| Cada manifiesto | `9d7b684ca600b34ea8862c057c1b1e2f7d85e8f026dd4e6d6667a573eeb736d1` |
| Índices lineales | `7b385adc99896c3ea0ec63e514f5cee5e60da61f7576fe30cd987b781b42b5d3` |
| Paleta 0 RGBA original | `c80b9622702f9488c682a13f8fa20e625c18fa0f14df08d1c319711a1be9429d` |
| Imagen 0 RGBA con alpha PS2 | `5e18dfe5e3d46b61c23ea25fcd56994e165fbb8bb4940a8a25ff07081d24d792` |
| Imagen 0 PNG normalizada, 66.395 bytes | `0587ad84d2c528a821ad095f8546f31aa72ce4109590a8be0c3525413b5c95fd` |

Sesiones relativas a la raíz privada autorizada:
`f03-02-texture-a-v1/` y `f03-02-texture-b-v1/`. La vista inspeccionada es
`palette-0.png`; `manifest.json` identifica todos los archivos. No reutilizar esas
sesiones. Los registros ignorados `reports/local/f03-02-execution-v1.json` y
`f03-02-decode-comparison-v1.json` conservan comandos, rutas y comparación.

El lector existente comprueba el hash completo antes de exponer cada fragmento
de ≤4096 bytes. La salida usa directorio 0700 y archivos 0600 exclusivos; verifica
bytes escritos y publica el manifiesto después de terminar los archivos.
Una excepción conserva parciales para diagnóstico. La operación presupone una
raíz bajo control del operador, como las extracciones anteriores.

## Referencias y contraste independiente

El layout CLUT procede de la referencia Sparagas fijada en F03.01.
El cálculo de índices se contrastó con
[GSTables.cpp de PCSX2](https://github.com/PCSX2/pcsx2/blob/fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3/pcsx2/GS/GSTables.cpp),
revisión `fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, licencia GPL-3.0+.
La copia local coincide por SHA-256 con el archivo descargado de esa revisión:
`a9a226297ede32b89177d7bdb04e9d8e21728e7d55799405f6112e97fe4969e8`.
No se copia ni enlaza PCSX2 en el decoder.

El oráculo escribe posiciones de bytes en memoria GS como PSMCT32 y las lee como
PSMT8 usando páginas, bloques y columnas. No usa la fórmula compacta del decoder
para generar esperados. **20/20 combinaciones admitidas**, 3.809.280 direcciones,
cero diferencias. El mapa completo de 256×256, serializado u32 little-endian,
tiene SHA-256 `b4408a996c085fd00e3f18176519c1d2bc3b977adadf2559d232a001e6ca3aa4`.

`build/f03-02/address-oracle-all.json` conserva el resultado; SHA-256
`77c32ffc40abaa0ac87e3da77485385f1e4977f57fff25d44a2af57d59991b32`.
El ensayo anterior de cinco dimensiones se conserva en `address-oracle.json`.
La herramienta de verificación lee la referencia externa fijada, sin ejecutar
código recibido ni necesitar originales del juego.

Pillow 12.3.0, disponible en el runtime de documentos, leyó independientemente los
cuatro PNG; dimensiones, modo RGBA y SHA-256 de los píxeles coinciden con la salida
previa al encoder. Evidencia: `build/f03-02/png-independent.json`. Pillow no es
una dependencia nueva del pipeline. La compresión de esta entrega usa zlib 1.2.12;
los hashes RGBA no dependen de la compresión PNG.

## Implementación y pruebas

- Decoder puro: índices lineales, paletas inmutables y render por paleta.
- Coordinación: evidencia de catálogo/recibo, selección explícita, sondeo de
  headers, lectura acotada y manifiesto.
- Adaptadores: PNG para inspección y writer privado separados del decoder.
- No cambia el runtime 3DS ni añade dependencias al SDK o al entorno Python.

**318/318 tests aprobados, 57 nuevos**. Suites: textura decode/probe, candidatos,
sondeo de cámara y repositorio. Se verifican mapa completo/biyectivo y huellas
independientes, puntos asimétricos, colores CLUT, 256 valores alpha, paletas
uniformes, dimensiones/tamaños incorrectos, selección ausente o fuera de rango,
variante no soportada, lectura corta, corrupción privada, salida repetible,
sesión ocupada, symlink, directorio sustituido, archivos extra, hash de escritura
incorrecto y fallo de disco sin manifiesto final. PNG se prueba también por
chunks, CRC, dimensiones y datos descomprimidos.

Cobertura de los cuatro módulos de producción nuevos: **188/189 líneas
(99,47 %) y 55/56 ramas (98,21 %)**. Decoder, encoder PNG y writer: 100 % de líneas
y ramas. La línea restante es el despachador `__main__`, ejecutado por las dos
conversiones reales fuera del proceso de cobertura. La herramienta de oráculo
se valida por su ejecución externa; no se suma a esos porcentajes.
JUnit y cobertura: `build/f03-02/final-tests.xml`, `final-coverage.json/xml`.
No se declara repetida toda la suite Python ni compilación C++/ARM.

El primer ensayo detectó tres fixtures que colocaban la salida privada como
ancestro del checkout ficticio; el guard de custodia los rechazó correctamente.
Se corrigió el montaje del test a directorios hermanos. No se relajó la política.
`initial-tests.xml` y `tests-v2.xml` conservan esos ensayos.

CI descubre las pruebas nuevas sin originales ni red. El oráculo completo y las
dos conversiones son comprobaciones locales explícitas, sin atribuir ejecución
remota ni comparación visual dentro de PCSX2.

Ruff check/format, gate de cobertura por líneas/ramas, arquitectura,
custodia/referencias y `git diff --check`: aprobados. El manifiesto de 18 archivos
propios y dependencias compartidas `build/f03-02/source-manifest.json` tiene
SHA-256 `7da9afb1455c7d6caf9133cab9c088344357a7ec982c9dee209492488d2c6dc8`.
Excluye este informe para evitar autorreferencia. No se creó commit.

## Reproducción y continuidad

Usar el catálogo/recibo y hashes registrados en F03.01:

```sh
rtk proxy .venv/bin/python -m tools.pipeline.decode_texture \
  --catalog reports/local/f02-04-asset-catalog.json \
  --catalog-sha256 39fff8337f51b21d520c8f35a1b9ba2fd8718d80fd40ff0b735d929832230d9d \
  --receipt /raiz/privada/f02-05/verified.json \
  --receipt-sha256 74720589caadefaf2f88a5ea0642ed080cc0d81ffab036cacf0bc5f051f3a943 \
  --private-copy /raiz/privada/f02-05/copy-a \
  --private-root /raiz/privada \
  --resource-id asset:0af58e26e1e91e71293f018ef07da3daed14ad44fd94d4ecea6b7d4eb4d72c3b \
  --ordinal 0 --run-id nueva-textura
```

La raíz del ejemplo es un marcador. Para repetir, usar copy-b y otro run-id.
Pendientes: contraste de paleta/orientación/alpha contra el uso original,
integración en escena y variantes de 4 bits u otras CLUT. La carga privada y
el ensayo físico del visor de inspección se completaron mediante TI-T1–TI-T5.
