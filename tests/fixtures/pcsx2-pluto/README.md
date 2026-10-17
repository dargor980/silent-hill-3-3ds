# Fixture PlutoVG/PlutoSVG para el observador host

Contrato [PV01–PV07](../../../schemas/pcsx2-pluto-v1.md). Proyecto CMake local
para macOS x86_64, separado del runtime 3DS. Consume los targets exportados
`plutovg::plutovg` 1.3.2 y `plutosvg::plutosvg` 0.0.7, con FreeType 2.14.3.

## Casos y oráculos

| CTest | Comprobación independiente del resultado observado |
|---|---|
| `plutovg-raster` | Superficie 16×12 inicialmente transparente; rectángulo rojo en [2,6)×[3,8), stride 64 y todos sus píxeles |
| `plutovg-composite` | Rojo con alfa 128/255 sobre azul: ARGB `FF80007F`; sobre transparente: `80800000`; fondo intacto |
| `plutovg-guards` | Memoria externa 8×6 con stride 48, padding y guardas; clip [1,5)×[1,4), traslación x=2 y dibujo fuera del área; solo [2,5)×[1,4) cambia |
| `plutovg-bounds` | Creación propia rechaza dimensión 0, −1 o 32768 en cada eje; acepta 1×1; rechaza inversión de matriz singular |
| `plutosvg-render` | `scene.svg` produce 16×12 y 32×24, con dos rectángulos rojos/verdes y fondo transparente; verifica todos los píxeles y traslación del grupo |
| `plutosvg-ids` | ID `red`: extents (2,2,4,3), recorte 4×3 rojo; ID ausente rechazado al consultar y renderizar |
| `plutosvg-invalid` | Rechaza buffer vacío, texto sin XML, `<svg` truncado y destino de ancho 32768 |
| `plutosvg-freetype` | Glifo SVG A: carga como SVG y renderiza BGRA rojo; 20×35 y 40×70 píxeles, origen/avance previstos; repite tamaño 50 para reutilizar la cara |

Las versiones de cabecera/binario se comprueban en cada ejecutable. Se usa
formato ARGB premultiplicado nativo documentado por PlutoVG; FreeType entrega
bytes BGRA. Los contornos están alineados a píxeles: no se aceptan tolerancias
obtenidas de una salida previa ni imágenes golden capturadas del proveedor.
La memoria externa suministrada siempre es válida; su API no promete validar
un stride insuficiente y no se le pasan buffers inválidos.

Los SVG, helper y casos son originales, bajo Apache-2.0 del repositorio. RAII
libera documentos, superficies, canvas, biblioteca y cara aun ante error.
Los bytes de entrada sobreviven al documento/cara que los referencia. Cada
caso tiene timeout de 15 s y devuelve errores explícitos, sin `assert` que
Release pueda desactivar. No se abren ventanas ni se leen originales.

## Fuente SVG propia

`generate_svg_font.py` exige FontTools 4.60.1 y el hash de la fuente geométrica
de [FH](../pcsx2-fonts/README.md). Añade exclusivamente `glyph.svg` al glifo 2
en una tabla `SVG `; conserva timestamps. El glifo es un rectángulo rojo de
400×700 unidades con y=−700 en un documento de 1000×1000. A 50/100 px/em,
el tamaño previsto es 20×35/40×70 y el avance es 30/60 px.

Dos generaciones produjeron 1.548 bytes con SHA-256
`019a5919f32f9ad9906e0b896a2f276666d828598af124a6978f882d07b0639a`.
Se reutiliza el FontTools host fijado/verificado en SRC34, sin otra descarga.
El caso instala los hooks devueltos por `plutosvg_ft_svg_hooks()`, la API de
compatibilidad exportada que usa el ImGui del PCSX2 fijado. No compila una
copia del adaptador header-only dentro del fixture; exige soporte FreeType
en la biblioteca y su target CMake.

## Ejecución reproducible

Con FontTools 4.60.1 disponible en `PYTHONPATH` del proceso:

```sh
rtk proxy python3 tests/fixtures/pcsx2-fonts/generate_font.py build/rectangles.ttf
rtk proxy python3 tests/fixtures/pcsx2-pluto/generate_svg_font.py \
  build/rectangles.ttf build/rectangles-svg.ttf
rtk proxy cmake -S tests/fixtures/pcsx2-pluto -B build/pluto-fixture \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=x86_64 \
  -DSH3_VG_CONFIG_DIR=/ruta/privada/lib/cmake/plutovg \
  -DSH3_SVG_CONFIG_DIR=/ruta/privada/lib/cmake/plutosvg \
  -DSH3_PREFIX=/ruta/privada -DSH3_WITH_SVG=ON \
  -DSH3_FONT="$PWD/build/rectangles-svg.ttf"
rtk proxy cmake --build build/pluto-fixture --parallel 2
rtk proxy ctest --test-dir build/pluto-fixture --output-on-failure
```

Para probar antes de instalar, indicar el directorio de build que contiene
el `Config.cmake` exportado correspondiente. En la ejecución registrada también
se fijaron SDK/compiladores y aislamiento de CMake/pkg-config. Los paquetes
explícitos ausentes se rechazan incluso con otra instalación válida disponible.

Estos ocho casos cubren geometría sintética y un glifo SVG. No son una suite
completa SVG/OpenType ni validación de fuentes del juego, todos los operadores,
scripts tipográficos, consumo de memoria, rendimiento o gráficos 3DS.
