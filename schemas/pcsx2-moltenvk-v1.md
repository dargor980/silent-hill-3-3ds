# MV v1 — MoltenVK del observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-moltenvk`.
Hereda [DB](pcsx2-dependencies-v1.md) y mantiene la reserva general IB.

Como responsable del observador, necesito una implementación Vulkan/Metal
privada y verificable para completar sus dependencias gráficas en macOS.

## Requisitos EARS

- **MV01 — Procedencia.** CUANDO prepare MoltenVK 1.4.1, DEBERÁ verificar
  archivo/hash de receta, rutas de extracción y revisiones de las siete
  dependencias; conservar originales, licencias, parches e inventario previo.
- **MV02 — Configuración.** CUANDO configure Xcode, DEBERÁ comprobar valores
  efectivos x86_64/macOS 11.0, SDK, herramientas, rutas y opciones de receta
  para argument buffers/API privada. SI los valores difieren, DEBERÁ detener
  el build y registrar la corrección, sin cambiar tests del proveedor.
  DEBERÁ distinguir la opción de configuración de API privada del soporte
  compilado: en la receta fijada `MVK_CONFIG_USE_METAL_PRIVATE_API=1` y
  `MVK_USE_METAL_PRIVATE_API` omitido producen un valor efectivo de 0.
- **MV03 — Capacidad.** ANTES de preparar fuentes, DEBERÁ disponer de 14 GiB
  libres; ANTES del build, 13 GiB, fuentes originales/copia menores de
  1,5 GiB y como máximo 2.000 unidades de compilación planificadas.
  MIENTRAS construya con dos jobs, DEBERÁ supervisar toda la etapa, incluidos
  DerivedData y temporales, detener el grupo bajo 10 GiB libres o al superar
  4 GiB presupuestados/asignados y conservar muestras/fallos. Los archivos
  dispersos CAS `CompilationCache.noindex/generic/v1.1/v8.index` (8 GiB) y
  `v8.data` (16 GiB) DEBERÁN contabilizar todos sus bloques asignados y
  registrar por separado la reserva lógica; cualquier nombre/tamaño distinto
  conservará el mayor de tamaño lógico/asignado. DEBERÁ probar esta política. SI no cabe, DEBERÁ
  revisar capacidad antes de reintentar. Son límites de un intento acotado,
  no una estimación probada ni una cuota; IB conserva sus 20 GiB generales.
- **MV04 — Ejecución.** CUANDO pruebe la biblioteca, DEBERÁ verificar versión,
  carga privada, capacidades y operaciones Vulkan con datos propios. DEBERÁ
  separar consultas API de transferencia y cómputo GPU, comparar resultados
  leídos con un oráculo CPU y esperar finalización antes de liberar recursos.
- **MV05 — Errores.** CUANDO falten raíces/bibliotecas o se solicite una
  extensión inexistente, DEBERÁ comprobar rechazo y recuperación posterior.
  DEBERÁ liberar objetos en orden y acotar esperas de GPU.
- **MV06 — Pruebas originales.** CUANDO valide, DEBERÁ identificar y ejecutar
  pruebas originales aplicables sin cambiar sus expectativas, distinguir
  demos/consultas de pruebas con oráculo y registrar exclusiones. NO DEBERÁ
  equiparar este ensayo a Vulkan CTS ni a compatibilidad de todas las GPU.
- **MV07 — Instalación.** SOLO CUANDO aprueben las pruebas previas, DEBERÁ
  instalar en el prefijo privado; repetir en consumidor nuevo, verificar
  arquitectura/dependencias/hash y conservación del prefijo previo.
- **MV08 — Continuidad.** CUANDO cierre, DEBERÁ repetir CMake/gate, publicar
  código propio/metadatos y detallar el build completo. DEBERÁ distinguir
  preparación, compilación, ejecución host, CI remota e instrumentación/3DS.

## Diseño y tareas

El coordinador separa adquisición, parches, configuración, supervisión y
auditoría. Los consumidores inyectan bibliotecas/headers explícitos; RAII
separa propiedad de objetos de operaciones y oráculos. Fuentes externas,
dependencias y builds permanecen privados. Los casos propios no contienen
datos del juego ni dependen del emulador.

1. Verificar archivo, siete commits, licencias y prefijo; copiar originales
   antes de aplicar los dos parches y ajustes de receta (MV01).
2. Inspeccionar proyectos/esquemas/tests; medir fuentes y unidades, consultar
   settings Xcode y fijar DerivedData/temporales bajo supervisión (MV02/MV03).
3. Construir dependencias y paquete macOS; registrar cada intento y comprobar
   arquitectura real de archivos estáticos/dylib (MV02/MV03).
4. Ejecutar casos propios y originales aplicables, negativos y trazas;
   registrar resultados observados y límites de cobertura (MV04–MV06).
5. Instalar tras aprobación, repetir pruebas y comprobar manifiesto/prefijo;
   ejecutar CMake/gate y detallar próxima unidad (MV07/MV08).
