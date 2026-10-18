# QI v1 — Qt imageformats para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-imageformats`.
Hereda [DB](pcsx2-dependencies-v1.md) y usa Qt Base/SVG privados ya validados.

## Requisitos EARS

- **QI01 — Procedencia.** CUANDO prepare Qt imageformats, el procedimiento
  DEBERÁ verificar el archivo 6.11.1 contra la receta fijada, comprobar rutas
  antes de extraer, conservar originales/avisos y registrar cambios. DEBERÁ
  comprobar los binarios anteriores y tomar un snapshot del prefijo.
- **QI02 — Configuración.** CUANDO configure el módulo, el procedimiento
  DEBERÁ usar el helper privado, Qt 6.11.1 exacto, Release x86_64/macOS 11.0,
  `QT_GENERATE_SBOM=OFF` y `FEATURE_system_webp=ON`. DEBERÁ identificar plugins
  habilitados y procedencia de dependencias, excluyendo bibliotecas objetivo
  Homebrew. Las omisiones DEBERÁN quedar explícitas.
- **QI03 — Capacidad.** ANTES de construir, el procedimiento DEBERÁ confirmar
  menos de 128 MiB de fuentes y como máximo 128 unidades de compilación, e
  inicio con 16 GiB libres. MIENTRAS compile a dos jobs, DEBERÁ detener su
  grupo si supera 512 MiB lógicos/asignados de build o quedan menos de 14 GiB
  libres. SI el alcance supera esas condiciones, DEBERÁ revisar el presupuesto
  antes de iniciar. DEBERÁ verificar por hash el supervisor previo y registrar
  las muestras; el gate IB general de 20 GiB permanece vigente.
- **QI04 — Decodificación.** CUANDO decodifique WebP sin pérdida propio,
  el consumidor DEBERÁ verificar formato, tamaño, color y alpha contra valores
  conocidos. CUANDO solicite escalado soportado, DEBERÁ comprobar tamaño y
  píxeles interiores. DEBERÁ probar al menos otro formato habilitado con un
  archivo sintético independiente del escritor Qt.
- **QI05 — Errores y escritura.** CUANDO lea un archivo truncado, el consumidor
  DEBERÁ exigir rechazo y diagnóstico; CUANDO cargue después uno válido,
  DEBERÁ comprobar recuperación. DONDE se pruebe escritura, DEBERÁ validar
  el resultado con un lector independiente, además del retorno de la API.
  DEBERÁ documentar qué formatos/capacidades quedan sin probar.
- **QI06 — Plugins y consumo.** CUANDO ejecute las pruebas, el consumidor
  DEBERÁ enlazar solo Qt Gui para acceder a las imágenes, registrar carga
  efectiva de los plugins y WebP desde los árboles evaluados y rechazar una
  raíz explícita inexistente. DEBERÁ ejecutar casos propios y un subconjunto
  original documentado antes de instalar, y repetir desde consumidor nuevo.
- **QI07 — Instalación.** SOLO CUANDO aprueben los casos y la carga previa,
  el procedimiento DEBERÁ instalar; después DEBERÁ verificar manifiesto,
  arquitectura x86_64, mínimo declarado 11.0, dependencias y conservación de
  archivos/enlaces previos. DEBERÁ preservar los fallos y omitir pasos dependientes.
- **QI08 — Continuidad.** CUANDO cierre esta unidad, el procedimiento DEBERÁ
  repetir CMake PCSX2 y el gate IB en salidas nuevas, publicar solo metadatos
  y detallar Qt Tools/LinguistTools como siguiente unidad. Las pruebas host
  DEBERÁN distinguirse de CI remota, UI visible, GPU, juego y ejecución 3DS.

## Diseño y tareas

El coordinador separa procedencia/configuración, supervisión, pruebas e
instalación. El generador de WebP y su lector independiente usan la biblioteca
WebP aprobada; el consumidor de plugins usa Qt Gui. Los otros formatos
sintéticos se construyen directamente desde su estructura. Cada oráculo
comprueba valores conocidos y conserva un propósito independiente de la API
que se valida. No se incluyen assets del juego ni fixtures externos en el repo.

1. Verificar fuentes y prefijo, inventariar licencias/plugins, seleccionar
   casos originales y concretar fixtures/oráculos (QI01/QI02/QI04–QI06).
2. Configurar en árbol nuevo, auditar dependencias, unidades, arquitectura
   y capacidad; construir con supervisor verificado y presupuesto propio
   (QI02/QI03). El muestreo no es una cuota ni garantiza observar cada pico.
3. Compilar consumidores, ejecutar positivos/negativos y tests originales,
   comprobar carga real antes de instalar (QI04–QI06).
4. Instalar únicamente tras aprobar, repetir en consumidor nuevo, verificar
   arquitectura, manifiesto, cargas, negativos y conservación (QI06/QI07).
5. Publicar evidencia, repetir CMake/gate y detallar Qt Tools (QI08).
