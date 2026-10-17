# DB v1 — dependencias host del build instrumentado

Extensión de [IB](pcsx2-build-preflight-v1.md), tarea
`F02.07/origin/effective-mapping/instrumented-build/prerequisites`.

## Requisitos EARS

- **DB01 — Procedencia.** CUANDO prepare una dependencia, el procedimiento
  DEBERÁ fijar versión, URL y SHA-256 esperado antes de ejecutarla; DEBERÁ
  contrastar la descarga y conservar fuente, parches y avisos en el área privada.
- **DB02 — Aislamiento.** MIENTRAS construya dependencias, el procedimiento
  DEBERÁ separar herramientas ejecutadas en el host de bibliotecas x86_64,
  instalar únicamente en prefijos privados y excluir bibliotecas ARM64 de
  Homebrew de la resolución de bibliotecas del emulador.
- **DB03 — Ensamblador.** CUANDO prepare NASM, el procedimiento DEBERÁ ejecutar
  sus pruebas disponibles y ensamblar un fixture propio Mach-O x86_64, enlazarlo
  con C++ y comprobar sus resultados en ejecución, incluido desbordamiento de
  aritmética sin signo. La versión impresa no sustituirá esos ensayos.
- **DB04 — JPEG.** CUANDO prepare libjpeg-turbo, el procedimiento DEBERÁ exigir
  SIMD x86_64, compilar bibliotecas compartidas, ejecutar CTest y verificar la
  arquitectura instalada. SI falta el ensamblador, falla una prueba o no se
  habilita SIMD, DEBERÁ conservar el fallo sin instalar ese resultado como válido.
- **DB05 — Evidencia.** CUANDO termine cada etapa, el procedimiento DEBERÁ
  registrar argumentos, entorno relevante, códigos de salida y hashes de logs.
  SI una etapa falla, DEBERÁ omitir sus dependientes y conservar el diagnóstico.
- **DB06 — Integración.** CUANDO se instale un conjunto de bibliotecas probado,
  el procedimiento DEBERÁ repetir CMake de PCSX2 en un directorio nuevo y
  registrar el primer requisito faltante sin dar por comprobados los posteriores.
- **DB07 — Alcance.** MIENTRAS prepare dependencias, el procedimiento DEBERÁ
  usar fixtures propios o del proveedor, conservar IB02 para operaciones grandes
  y mantener pendientes el build del emulador, sus pruebas y el mapa efectivo
  hasta obtener evidencia específica de cada resultado.
- **DB08 — Códecs auxiliares.** CUANDO prepare Zstd, LZ4 o WebP, el
  procedimiento DEBERÁ comprobar la arquitectura x86_64 y ejecutar un fixture
  propio enlazado con la biblioteca compartida concreta. DEBERÁ comparar el
  resultado completo del ciclo compresión/descompresión y rechazar destinos
  insuficientes; para Zstd/WebP, también entradas truncadas. CUANDO ejecute
  pruebas aleatorias del proveedor, DEBERÁ registrar semilla y límite, y
  distinguir ese subconjunto de una suite exhaustiva.

## Diseño y secuencia

Los scripts del proveedor construyen sus componentes. La coordinación local
registra resultados y detiene etapas dependientes; el gate IB05 sigue siendo
puro y no instala software. `host-tools` contiene NASM para el host;
`dependencies-x86_64` contiene las bibliotecas del emulador. El runtime 3DS no
depende de ninguno de estos prefijos.

1. Fijar y verificar NASM; configurar y compilar para el host; ejecutar pruebas
   del proveedor y fixture propio; instalar y comprobar identidad del ejecutable.
2. Verificar el archivo de libjpeg-turbo fijado por PCSX2; configurar con
   `REQUIRE_SIMD=ON`, ensamblador explícito y pruebas habilitadas; compilar y
   ejecutar CTest; instalar solo tras éxito y comprobar dylibs/manifiesto.
3. Repetir configuración limpia de PCSX2; continuar en orden de dependencias
   efectivamente faltantes, manteniendo avisos, archivos originales y resultados.
4. Ejecutar controles del repositorio y actualizar el backlog. CI `quality`
   conserva sus pruebas sintéticas; las descargas y builds host se validan
   localmente y no se presentan como ejecución de CI remota.
