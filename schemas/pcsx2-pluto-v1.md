# PV v1 — PlutoVG y PlutoSVG para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-plutovg-plutosvg`.
Hereda [DB01–DB08](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **PV01 — Procedencia.** CUANDO prepare PlutoVG 1.3.2 y PlutoSVG 0.0.7, el
  procedimiento DEBERÁ verificar archivos contra la receta PCSX2 fijada,
  conservar fuentes/avisos, incluidos los componentes internos, y registrar
  cualquier modificación separadamente.
- **PV02 — Build.** CUANDO compile, el procedimiento DEBERÁ producir bibliotecas
  compartidas x86_64 en builds separados, primero PlutoVG y después PlutoSVG,
  con ejemplos OFF e integración FreeType ON para PlutoSVG. DEBERÁ aislar
  CMake/pkg-config, resolver las dependencias privadas y conservar los intentos.
- **PV03 — Raster.** CUANDO valide PlutoVG, el fixture DEBERÁ comprobar versión,
  dimensiones, stride, píxeles de rectángulos, composición alfa, transformaciones
  y clipping mediante expectativas geométricas previas. SI se usa memoria
  externa válida, DEBERÁ comprobar que padding y guardas no cambian. DEBERÁ
  comprobar rechazo de tamaños no admitidos por la API de creación propia.
- **PV04 — SVG.** CUANDO valide PlutoSVG, el fixture DEBERÁ comprobar dimensiones,
  render, escalado, extents/selección por ID y rechazo de entradas inválidas,
  IDs ausentes y superficies demasiado grandes, usando solo SVG propios.
- **PV05 — FreeType.** CUANDO valide la integración, el fixture DEBERÁ cargar
  una fuente sintética con tabla SVG, instalar los hooks exportados por PlutoSVG
  y comprobar formato BGRA, tamaño, origen, avance y píxeles a dos escalas.
  DEBERÁ repetir carga/raster en la misma cara para ejercitar reutilización.
- **PV06 — Aceptación.** CUANDO instale las bibliotecas, el procedimiento DEBERÁ
  repetir el fixture desde otro proyecto CMake usando los targets exportados,
  exigir versiones exactas y rechazar un directorio de paquete explícito ausente.
  DEBERÁ verificar arquitectura, manifiestos y enlaces. SI el proveedor no
  registra tests, DEBERÁ declarar esa ausencia sin contar cero como aprobado.
- **PV07 — Continuidad.** CUANDO pasen las pruebas, el procedimiento DEBERÁ
  repetir CMake de PCSX2 en un directorio nuevo y reevaluar IB, registrando el
  primer faltante real. F02.07, build completo y mapa seguirán pendientes hasta
  satisfacer sus propios criterios.

## Diseño y tareas

Los SVG y la fuente son insumos propios. El generador solo añade una tabla SVG
a la fuente geométrica de FH; el fixture no genera su propio resultado esperado.
Un helper C++ administra recursos y lectura de píxeles; los casos VG/SVG prueban
sus API por separado. CMake resuelve versiones/targets; el coordinador privado
conserva argumentos, logs y hashes. El runtime 3DS y el gate puro IB no cambian.

1. Verificar archivos, API, avisos subordinados e inventario de tests (PV01).
2. Fijar SVG, generador determinista y casos positivos/negativos (PV03–PV05).
3. Compilar PlutoVG, probar contra el build e instalar (PV02/PV03).
4. Compilar PlutoSVG con FreeType privado, probar contra el build e instalar
   (PV02/PV04/PV05).
5. Ejecutar consumo instalado y negativos de paquetes; inspeccionar bibliotecas,
   fuentes y manifiestos, sin ocultar omisiones (PV06).
6. Repetir CMake/gate, validar repositorio y publicar metadatos; actualizar
   siguiente tarea según el faltante observado (PV07).

Aceptación: dos dylibs x86_64, fixtures previos/posteriores satisfactorios y
CMake que supera PlutoVG/PlutoSVG. No demuestra SVG arbitrario, fuentes del
juego, render 3DS ni rendimiento del port.
