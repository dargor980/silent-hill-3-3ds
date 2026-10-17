# FH v1 — FreeType y HarfBuzz para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-freetype-harfbuzz`.
Hereda [DB01–DB08](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **FH01 — Procedencia.** CUANDO prepare las dependencias, el procedimiento
  DEBERÁ verificar FreeType 2.14.3 y HarfBuzz 14.2.0 contra los hashes de la
  receta fijada, conservar fuentes y avisos y registrar herramientas auxiliares.
- **FH02 — Compilación.** CUANDO compile, el procedimiento DEBERÁ seguir
  FreeType sin HarfBuzz → HarfBuzz → FreeType con HarfBuzz en builds separados,
  conservar la configuración compartida x86_64 de la receta y aislar CMake y
  pkg-config del prefijo de Homebrew. DEBERÁ conservar los intentos fallidos.
  La variante final DEBERÁ usar `FT_DYNAMIC_HARFBUZZ=OFF`, además de
  `FT_REQUIRE_HARFBUZZ=TRUE`, para exigir enlace a la biblioteca privada y
  evitar la búsqueda de `libharfbuzz.0.dylib` por nombre en ejecución.
- **FH03 — Datos de prueba.** CUANDO pruebe las API, el fixture DEBERÁ usar una
  fuente geométrica propia, determinista, con métricas, contornos y reglas de
  composición conocidos antes de observar el resultado. No usará originales.
- **FH04 — FreeType.** CUANDO valide cada variante, el fixture DEBERÁ comprobar
  versión, mapeo Unicode, métricas y píxeles rasterizados a dos tamaños, carga
  con auto-hinting y rechazo de datos truncados/índices inválidos. DEBERÁ probar
  la variante final tanto antes como después de instalarla.
- **FH05 — HarfBuzz.** CUANDO valide el shaping, el fixture DEBERÁ comprobar
  IDs, clusters, avances y offsets con ligadura activada, desactivada y kerning,
  más texto vacío y carácter sin glifo. DEBERÁ exigir el shaper OpenType y
  repetir las comprobaciones con las bibliotecas finales instaladas.
- **FH06 — Evidencia.** SI el build de proveedor no registra pruebas CTest o
  sus suites requieren otras dependencias, el informe DEBERÁ indicar la omisión,
  sin contar cero tests como aprobados. CUANDO instale, DEBERÁ verificar hashes,
  arquitectura, enlaces, manifiestos y rechazo de un prefijo explícito ausente.
- **FH07 — Continuidad.** CUANDO pasen los fixtures, el procedimiento DEBERÁ
  repetir CMake de PCSX2 en un directorio nuevo, registrar su primer faltante
  y reevaluar IB. El build completo y el mapa efectivo seguirán pendientes
  hasta contar con sus verificaciones propias.

## Diseño y tareas

El generador define exclusivamente datos sintéticos. CMake resuelve bibliotecas
explícitas y registra los casos; los casos C++ prueban API públicas y administran
recursos con RAII. Los resultados y argumentos privados quedan en `build/`;
la evidencia pública contiene metadatos. El runtime 3DS no incorpora estas
dependencias host ni se modifica el gate puro IB.

1. Verificar archivos, avisos y opciones; inventariar tests del proveedor.
2. Generar y verificar dos veces la fuente propia; fijar expectativas de API.
3. Compilar FreeType inicial, ejecutar fixture e instalar el bootstrap.
4. Compilar HarfBuzz, probar shaping contra el build e instalar.
5. Compilar FreeType final con HarfBuzz requerido, probar e instalar; repetir
   integración, inspeccionar enlaces y probar rechazo de prefijo incorrecto.
6. Ejecutar configuración PCSX2 nueva, gate y controles del repositorio;
   publicar evidencia, limitaciones y siguiente tarea.

Aceptación: bibliotecas compartidas x86_64 verificadas; fixtures satisfactorios
y CMake de PCSX2 que supera FreeType. Esto no demuestra fuentes/textos del juego,
idiomas complejos, backend CoreText ni todos los formatos tipográficos.
