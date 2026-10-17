# Fixture FreeType/HarfBuzz para el observador host

Contrato [FH01–FH07](../../../schemas/pcsx2-fonts-v1.md).
Proyecto CMake independiente del runtime 3DS. Requiere las bibliotecas
compartidas x86_64 FreeType 2.14.3 y, opcionalmente, HarfBuzz 14.2.0.

## Fuente y expectativas

`generate_font.py` genera una fuente TrueType original bajo la licencia
Apache-2.0 del repositorio. No copia contornos, tablas ni textos del juego o
de fuentes externas. Usa FontTools **4.60.1**, solo como herramienta host de
generación, con timestamps fijos. La salida tiene 1.356 bytes y SHA-256
`cdd254e7aec2ce13f35942b815da8374d8b0f36a61ef99ba4a4519c2dda81b97`.
Dos generaciones independientes deben producir los mismos bytes.

Unidades por em: 1.000; contornos rectangulares de altura 700, origen (0,0).

| ID | Glifo | Ancho de contorno | Avance |
|---|---|---|---|
| 0 | .notdef | 300 | 500 |
| 1 | space | vacío | 250 |
| 2 | A | 400 | 600 |
| 3 | V | 450 | 650 |
| 4 | AV | 800 | 1.000 |

El cmap contiene espacio, A y V. GSUB `liga` sustituye A,V por AV; GPOS `kern`
resta 80 al avance de A seguido de V. Estas reglas son el oráculo, definido
antes de ejecutar las bibliotecas, sin capturar resultados como golden.

## Casos

- FreeType: versión binario/cabeceras exacta; cmap y ausencia de glifo;
  raster sin hinting de A a 50 y 100 px/em (20×35 y 40×70 píxeles, todos 255),
  origen y avances; carga/raster del glifo AV con auto-hinting; rechazo de fuente
  truncada a 12 bytes, face index 1 y glyph index 5.
- HarfBuzz: shaper OpenType explícito, escala 1.000, script Latin, idioma es.
  `AVA` con ligadura produce IDs 4,2 y avances 1.000,600; sin liga ni kern,
  IDs 2,3,2 y avances 600,650,600; solo con kern, 520,650,600. Se comprueban
  todos los clusters y offsets; también espacio, texto vacío, U+10FFFF y una
  fuente truncada que no expone glifos.

RAII libera bibliotecas, caras, buffers y blobs aun ante error. Los casos
devuelven errores explícitos, sin `assert` desactivable en Release. CTest limita
cada caso a 15 segundos. La prueba geométrica no demuestra español completo,
tipografía real, scripts complejos, CoreText, subset/raster/vector de HarfBuzz
ni datos originales. El caso auto-hinting y el enlace directo prueban el camino
configurado; no miden por sí solos cada llamada interna de FreeType a HarfBuzz.

## Ejecución

Generar con un Python cuyo `PYTHONPATH` incluya el paquete FontTools fijado:

```sh
python3 tests/fixtures/pcsx2-fonts/generate_font.py build/rectangles.ttf
cmake -S tests/fixtures/pcsx2-fonts -B build/fonts-fixture \
  -DCMAKE_OSX_ARCHITECTURES=x86_64 -DCMAKE_BUILD_TYPE=Release \
  -DSH3_PREFIX=/ruta/privada/dependencies-x86_64 \
  -DSH3_FONT="$PWD/build/rectangles.ttf" -DSH3_WITH_HARFBUZZ=ON
cmake --build build/fonts-fixture --parallel 2
ctest --test-dir build/fonts-fixture --output-on-failure
```

La generación no forma parte del runtime ni necesita red después de obtener
FontTools. El proyecto no descarga dependencias. `SH3_PREFIX` es obligatorio;
no hay búsqueda implícita de otra instalación. Para probar antes de instalar,
usar pares `SH3_FT_BUILD`/`SH3_FT_SOURCE` y `SH3_HB_BUILD`/`SH3_HB_SOURCE`.
Las cabeceras generadas del build preceden a las fuentes. En la ejecución
documentada se usan además SDK/compiladores explícitos y búsquedas aisladas.
