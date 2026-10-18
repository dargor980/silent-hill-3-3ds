# QTO v1 — Qt Tools/LinguistTools para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-tools`.
Hereda [DB](pcsx2-dependencies-v1.md). Usa Qt Base, SVG e imageformats privados.

## Requisitos EARS

- **QTO01 — Procedencia.** CUANDO prepare Qt Tools, el procedimiento DEBERÁ
  verificar el archivo 6.11.1 contra la receta fijada, validar rutas antes de
  extraer y conservar originales/licencias. DEBERÁ comprobar los binarios Qt
  anteriores y tomar un snapshot de archivos/enlaces del prefijo.
- **QTO02 — Configuración.** CUANDO configure, DEBERÁ usar el helper privado,
  Qt 6.11.1 exacto, Release x86_64/macOS 11.0 y `QT_GENERATE_SBOM=OFF`.
  DEBERÁ respetar designer ON y assistant, clang, kmap2qmap, pixeltool,
  pkg_config, qev, qtattributionsscanner, qtdiag y qtplugininfo OFF.
  DEBERÁ inventariar herramientas/componentes efectivos y omisiones, con
  búsquedas aisladas y sin bibliotecas objetivo Homebrew.
- **QTO03 — Capacidad.** ANTES del build, DEBERÁ comprobar menos de 256 MiB
  de fuentes, como máximo 1.000 unidades de compilación y 15 GiB libres.
  MIENTRAS compile a dos jobs, DEBERÁ detener su grupo si supera 2 GiB
  lógicos/asignados de build o quedan menos de 12 GiB libres. DEBERÁ verificar
  por hash el supervisor previo y registrar sus muestras. SI excede el alcance,
  DEBERÁ revisar el presupuesto antes de construir. El gate IB general de
  20 GiB permanece vigente; este presupuesto es específico de Qt Tools.
- **QTO04 — Extracción.** CUANDO lupdate procese C++ propio, DEBERÁ generar
  un TS con contexto, mensajes Unicode, desambiguación y plural esperados.
  CUANDO actualice una traducción existente, DEBERÁ conservar sus traducciones.
  Las comparaciones DEBERÁN inspeccionar XML, no solo el código de salida.
- **QTO05 — Compilación y consumo.** CUANDO lrelease compile TS propio,
  DEBERÁ generar un QM que QTranslator cargue y traduzca al español con
  contexto, desambiguación y plural correctos. Dos compilaciones iguales
  DEBERÁN producir archivos idénticos. CUANDO falte una traducción,
  DEBERÁ conservarse el texto fuente mediante QCoreApplication.
- **QTO06 — Errores y UI.** CUANDO procese TS inválido o un archivo ausente,
  DEBERÁ exigir rechazo y diagnóstico. CUANDO QTranslator reciba QM inválido,
  DEBERÁ rechazarlo y recuperarse al cargar uno válido. DONDE UiTools esté
  habilitado, DEBERÁ comprobar un formulario propio mediante QUiLoader y
  rechazar XML UI inválido. Designer compilado no acreditará interacción visual.
- **QTO07 — Validación e instalación.** SOLO CUANDO aprueben herramientas,
  consumidores, tests originales seleccionados y carga previa, DEBERÁ instalar.
  DEBERÁ repetir desde consumidor nuevo, resolver LinguistTools/targets desde
  raíces explícitas y rechazar una raíz ausente sin fallback. DEBERÁ verificar
  manifiesto, arquitectura, versiones, dependencias y conservación del prefijo.
  SI falla una etapa, DEBERÁ conservarla y omitir pasos dependientes.
- **QTO08 — Continuidad.** CUANDO cierre esta unidad, DEBERÁ repetir CMake
  PCSX2 y el gate IB en salidas nuevas, publicar solo metadatos y detallar
  Qt translations como siguiente unidad de receta aún pendiente. DEBERÁ
  distinguir pruebas host de CI remota, UI visible, GPU, juego y runtime 3DS.

## Diseño y tareas

El coordinador separa fuentes/configuración, supervisión, herramientas,
consumidores e instalación. El verificador XML inspecciona resultados de
lupdate sin depender de Qt; lrelease produce QM consumido por un programa
Qt Core. UiTools se prueba en otro ejecutable Qt Widgets/offscreen.
Los textos, TS y formularios son propios, sin material del juego. Los tests
externos permanecen privados y conservan sus expectativas originales.

1. Verificar archivo, prefijo y avisos; auditar componentes/tamaño, definir
   fixtures y seleccionar tests originales aplicables (QTO01/QTO02/QTO04–QTO07).
2. Configurar en árbol nuevo, comprobar alcance y construir bajo presupuesto
   propio con supervisor verificado (QTO02/QTO03). El muestreo no es una cuota
   ni garantiza observar picos intermedios.
3. Ejecutar extracción, compilación, repetibilidad, traducción, negativos y
   UI donde aplique; comprobar carga efectiva y paquetes exportados (QTO04–QTO07).
4. Instalar tras aprobar, repetir consumidores nuevos y verificar artefactos,
   versiones, manifiesto y hashes anteriores (QTO07).
5. Repetir CMake/gate, publicar evidencia y detallar translations (QTO08).
