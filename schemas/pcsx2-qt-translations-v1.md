# QTR v1 — Catálogos Qt del observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-translations`.
Hereda [DB](pcsx2-dependencies-v1.md) y consume LinguistTools validado en SRC43.

## Requisitos EARS

- **QTR01 — Procedencia.** CUANDO prepare Qt translations, DEBERÁ verificar
  el archivo 6.11.1 contra la receta fijada, validar sus rutas y conservar
  originales y licencias privados. DEBERÁ comprobar hashes Qt anteriores
  y registrar archivos/enlaces del prefijo antes de instalar.
- **QTR02 — Configuración.** CUANDO configure, DEBERÁ usar el helper privado,
  Qt 6.11.1 exacto y `QT_GENERATE_SBOM=OFF`, inventariar los TS y dependencias
  de catálogos y verificar el lrelease efectivo. Los QM DEBERÁN describirse
  como datos independientes de arquitectura; sus consumidores host usarán
  x86_64/macOS 11.0 y raíces Qt explícitas.
- **QTR03 — Capacidad.** ANTES de generar catálogos, DEBERÁ comprobar menos
  de 256 MiB de fuentes, ausencia de compilación C/C++ del módulo y 14 GiB
  libres. MIENTRAS genere a dos jobs, DEBERÁ detener su grupo si el árbol de
  build supera 1 GiB lógico/asignado o quedan menos de 12 GiB libres.
  DEBERÁ verificar por hash el supervisor de SRC40 y conservar sus muestras.
  SI excede el alcance, DEBERÁ revisar el presupuesto antes de continuar.
  Este presupuesto específico no reemplaza el gate IB general de 20 GiB.
- **QTR04 — Catálogos.** CUANDO lrelease genere QM, DEBERÁ verificar que
  dos generaciones independientes producen los mismos bytes para todos los
  catálogos generados. DEBERÁ registrar catálogos disponibles y omisiones,
  comprobar todos los QM mediante QTranslator y resolver sus dependencias.
- **QTR05 — Español.** CUANDO pruebe los catálogos españoles, DEBERÁ usar
  un oráculo XML independiente sobre TS originales y comparar mensajes
  terminados, contexto, desambiguación, Unicode y plurales disponibles.
  CUANDO cargue un catálogo agregador, DEBERÁ verificar traducciones desde
  sus dependencias, sin publicar textos ni archivos del proveedor.
- **QTR06 — Negativos.** CUANDO falte un QM, esté corrupto o falte una
  dependencia requerida en un directorio aislado, DEBERÁ rechazar su carga.
  DESPUÉS del rechazo, DEBERÁ demostrar recuperación con un catálogo válido.
  CUANDO no exista una traducción, QCoreApplication DEBERÁ conservar el
  texto fuente. DEBERÁ rechazar una raíz Qt explícita ausente sin fallback.
- **QTR07 — Instalación.** SOLO CUANDO aprueben catálogos y consumidores
  previos, DEBERÁ instalar. DESPUÉS DE instalar, DEBERÁ repetir las pruebas
  con un consumidor nuevo, verificar QM contra el build, manifiesto, rutas
  de carga, arquitectura del consumidor y hashes previos del prefijo.
  SI falla una etapa, DEBERÁ conservarla y omitir pasos dependientes.
- **QTR08 — Continuidad.** CUANDO cierre, DEBERÁ repetir CMake PCSX2 y el
  gate IB en salidas nuevas, publicar solo metadatos y señalar QtApng como
  siguiente unidad. DEBERÁ distinguir catálogos Qt de textos del juego,
  pruebas host de CI remota y configuración de PCSX2 de un build completo.

## Diseño y tareas

La coordinación privada separa adquisición/configuración, supervisión,
generación, validación e instalación. Un lector XML propio produce oráculos
JSON privados desde los TS inalterados; un consumidor Qt Core compara QM
con esos oráculos. No se incluyen textos externos en fixtures públicos.
El consumidor recibe rutas de datos y el coordinador recibe sus herramientas,
sin acoplar la lógica de comparación al árbol privado de esta ejecución.

1. Verificar archivo y prefijo; inventariar TS, dependencias y licencias;
   configurar y verificar alcance/capacidad (QTR01–QTR03).
2. Generar con supervisor verificado; regenerar en salida separada y
   comparar todos los QM por hash (QTR03/QTR04).
3. Crear oráculo privado y consumidor propio; ejecutar carga de catálogos,
   español, agregadores, negativos, recuperación y trazas (QTR04–QTR06).
4. Instalar tras aprobación local; repetir desde consumidor nuevo y auditar
   manifiesto, datos, binarios consumidores y prefijo (QTR07).
5. Actualizar CMake/gate y evidencia trazable; detallar QtApng (QTR08).

El muestreo de capacidad no es una cuota ni garantiza observar picos
intermedios. No se atribuye cobertura de traducción humana ni de todos los
idiomas a las comparaciones automáticas seleccionadas.
