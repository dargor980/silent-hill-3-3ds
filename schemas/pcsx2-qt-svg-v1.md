# QS v1 — Qt SVG para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-svg`.
Hereda [DB](pcsx2-dependencies-v1.md). Usa Qt Base validado en
[SRC40](../docs/compatibility/pcsx2-qtbase-build-evidence.json).

## Requisitos EARS

- **QS01 — Procedencia.** CUANDO prepare Qt SVG, el procedimiento DEBERÁ
  verificar el archivo 6.11.1 contra el hash de la receta fijada, comprobar rutas
  antes de extraer, conservar originales y avisos, y registrar cualquier cambio
  de fuentes. DEBERÁ verificar el prefijo Qt previo antes de construir.
- **QS02 — Build y capacidad.** CUANDO configure el módulo, el procedimiento
  DEBERÁ usar qt-configure-module del prefijo privado, Qt 6.11.1 exacto,
  Release x86_64/macOS 11.0, QT_GENERATE_SBOM=OFF y búsquedas aisladas.
  ANTES de construir, DEBERÁ confirmar alcance pequeño e inicio con 16 GiB
  libres; MIENTRAS compile a dos jobs, DEBERÁ vigilar el build y detener su
  grupo de procesos si supera 512 MiB lógicos/asignados o quedan menos de
  14 GiB libres. DEBERÁ registrar el muestreo y sus límites.
- **QS03 — Renderer.** CUANDO renderice SVG propio, el fixture DEBERÁ exigir
  documento válido, dimensiones esperadas y píxeles interiores/exteriores
  conocidos. CUANDO aplique una transformación y transparencia, DEBERÁ verificar
  posiciones y canales con tolerancia declarada, evitando bordes antialias.
- **QS04 — Errores.** CUANDO reciba XML SVG mal formado, el renderer y el lector
  de imágenes DEBERÁN rechazarlo. CUANDO reciba después un documento válido,
  el fixture DEBERÁ comprobar recuperación. Ninguna omisión de un caso inválido
  DEBERÁ contarse como resultado satisfactorio.
- **QS05 — Plugins.** CUANDO abra el SVG mediante QImageReader, el fixture
  DEBERÁ comprobar formato, dimensiones, píxeles y escalado. CUANDO cree QIcon
  desde un recurso SVG, DEBERÁ comprobar tamaño y colores del pixmap solicitado.
  El procedimiento DEBERÁ verificar carga efectiva de los plugins SVG de imagen
  e iconos desde el árbol evaluado, además del renderer enlazado directamente.
- **QS06 — Consumo.** CUANDO valide el módulo, el procedimiento DEBERÁ usar
  consumidores nuevos con targets Qt exportados y raíces explícitas, ejecutar
  casos propios y un subconjunto documentado del proveedor antes de instalar,
  y repetirlos contra la instalación. SI falta la raíz SVG explícita,
  DEBERÁ rechazarla aunque exista un Qt válido en otro lugar.
- **QS07 — Instalación.** CUANDO instale resultados aprobados, el procedimiento
  DEBERÁ verificar manifiesto, arquitectura x86_64, dependencias y carga efectiva;
  DEBERÁ comprobar conservación de los archivos previos del prefijo y las fuentes.
  SI una prueba falla, DEBERÁ conservarla y omitir las etapas dependientes.
- **QS08 — Continuidad.** CUANDO termine, el procedimiento DEBERÁ repetir
  CMake PCSX2 y el gate IB general en salidas nuevas, publicar solo metadatos
  y detallar Qt imageformats como siguiente unidad. DEBERÁ mantener explícitos
  LinguistTools/Qt Tools, FFmpeg y demás pendientes; pruebas offscreen no
  acreditarán UI visible, GPU, juego ni runtime 3DS.

## Diseño y tareas

El coordinador mantiene procedencia/configuración/instalación separadas de
los fixtures. El renderer y los dos plugins tienen consumidores separados
para que enlazar QtSvg directamente no oculte un plugin ausente. Helpers de
comprobación comparten únicamente oráculos de píxeles y gestión de errores.
SVG y XML inválido son propios; fuentes/tests externos permanecen privados.

Este módulo pequeño tiene presupuesto propio QS02; no hereda la excepción
de Qt Base. Si el inventario supera 128 MiB de fuentes o 128 unidades de
compilación, el procedimiento debe revisar el alcance antes de construir.
La política IB02 de 20 GiB permanece vigente para operaciones grandes.
Se reutiliza el supervisor ensayado en SRC40 después de comprobar su hash;
el muestreo no constituye una cuota ni garantiza observar todos los picos.

1. Verificar archivo y tamaño, conservar originales/licencias y snapshot del
   prefijo; definir cinco casos propios y seleccionar tests originales (QS01).
2. Configurar desde build nuevo con el helper instalado y auditar targets,
   arquitectura, dependencias, versiones y alcance (QS02).
3. Construir bajo vigilancia; probar renderer, transformación/alpha, errores,
   lector/plugin e icono/plugin, además de los tests originales seleccionados
   (QS03–QS06).
4. Solo tras aprobar, instalar y repetir desde consumidor nuevo; comprobar
   negativos, manifiesto, arquitectura, carga y hashes anteriores (QS06/QS07).
5. Repetir CMake/gate y publicar evidencia con límites, procedencia y siguiente
   tarea detallada (QS08). No se modifica código del runtime 3DS.
