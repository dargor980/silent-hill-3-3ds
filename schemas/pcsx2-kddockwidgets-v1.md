# KDW v1 — Paneles Qt Widgets del observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-kddockwidgets`.
Hereda [DB](pcsx2-dependencies-v1.md). Consume Qt privado validado en SRC40–SRC45.

Como responsable del observador host, necesito paneles con disposición
persistente y un paquete consumible de forma independiente para continuar
la compilación instrumentada de PCSX2 con evidencia reproducible.

## Requisitos EARS

- **KDW01 — Procedencia.** CUANDO prepare KDDockWidgets 2.4.1, DEBERÁ
  verificar el archivo contra la receta fijada, validar rutas antes de extraer,
  conservar originales/licencias e inventariar las dependencias y tests.
  DEBERÁ comprobar evidencia Qt previa y capturar archivos/enlaces del prefijo.
- **KDW02 — Configuración.** CUANDO configure, DEBERÁ usar Release,
  x86_64/macOS 11.0, Qt 6.11.1 privado, `KDDockWidgets_QT6=true`,
  `KDDockWidgets_EXAMPLES=false` y frontend `qtwidgets`. DEBERÁ verificar
  paquetes, includes y enlaces efectivos, sin bibliotecas objetivo Homebrew.
- **KDW03 — Capacidad.** ANTES de cada build de esta unidad, DEBERÁ verificar
  menos de 256 MiB de fuentes, como máximo 500 unidades de compilación y
  14 GiB libres. MIENTRAS construya con dos jobs, DEBERÁ detener su grupo
  si el árbol de build supera 1 GiB lógico/asignado o quedan menos de 12 GiB
  libres. DEBERÁ verificar el supervisor SRC40 por hash y conservar muestras.
  SI excede el alcance, DEBERÁ revisar el presupuesto antes de construir.
  El gate IB general de 20 GiB permanece vigente.
- **KDW04 — Paneles.** CUANDO el consumidor cree paneles Qt Widgets con
  nombres estables, DEBERÁ verificar su contenido, estados acoplado/flotante,
  cierre/reapertura y relaciones de pestañas/disposición según la API real.
  DEBERÁ procesar eventos y comprobar estados observables, no solo compilar.
- **KDW05 — Persistencia.** CUANDO guarde una disposición y luego la
  modifique, DEBERÁ restaurar nombres, estados y relaciones esperados.
  CUANDO reciba una disposición inválida o un archivo ausente, DEBERÁ
  verificar rechazo y recuperación posterior con datos válidos. DEBERÁ
  distinguir estado semántico de geometría dependiente del entorno gráfico.
- **KDW06 — Pruebas.** CUANDO valide, DEBERÁ ejecutar consumidores propios
  y tests originales aplicables sin alterar sus expectativas. DEBERÁ registrar
  exclusiones, limitaciones de offscreen y fallos conservados. DEBERÁ usar
  el paquete/target exportado y rechazar una raíz explícita ausente sin fallback.
- **KDW07 — Instalación.** SOLO CUANDO aprueben las pruebas previas,
  DEBERÁ instalar. DESPUÉS DE instalar, DEBERÁ repetir en consumidores nuevos,
  verificar carga efectiva, manifiesto, arquitectura/mínimo macOS y conservación
  de archivos/enlaces previos. SI falla una etapa, DEBERÁ conservarla y
  omitir pasos dependientes.
  SI el test original revela una cabecera omitida por el paquete, DEBERÁ
  preservar el fallo y corregir únicamente la regla de instalación en una
  copia nueva, conservar originales/tests y repetir build, pruebas previas
  e instalación antes de declarar el paquete validado.
- **KDW08 — Continuidad.** CUANDO cierre, DEBERÁ repetir CMake PCSX2 y el
  gate IB en salidas nuevas, publicar solo código propio/metadatos y detallar
  FFmpeg como siguiente unidad. DEBERÁ distinguir pruebas host de CI remota,
  interacción física, build completo PCSX2, mapa efectivo y runtime 3DS.

## Diseño y tareas

La coordinación privada separa fuentes/configuración, supervisión, consumidores
y auditoría. Los casos propios usan un pequeño escenario de paneles con IDs
estables y aserciones independientes de posiciones exactas. La persistencia
consume datos propios en temporales; las dependencias se inyectan como raíces
CMake explícitas. Los tests del proveedor permanecen privados y sin cambios.

1. Verificar archivo, licencias, dependencias y prefijo; inspeccionar API,
   opciones y tests para definir el alcance efectivo (KDW01/KDW02/KDW06).
2. Configurar y construir con auditoría de comandos y capacidad (KDW02/KDW03).
3. Ejecutar paneles, persistencia, negativos, recuperación, tests originales
   y carga efectiva; registrar límites de offscreen (KDW04–KDW06).
4. Instalar tras aprobar y repetir consumidores nuevos; auditar manifiesto,
   paquetes, binarios y hashes anteriores (KDW07).
5. Actualizar CMake/gate, evidencia y tareas para FFmpeg (KDW08).

El muestreo no es una cuota ni garantiza observar picos. Las pruebas offscreen
no acreditan arrastre físico, apariencia visual o interacción con macOS.
