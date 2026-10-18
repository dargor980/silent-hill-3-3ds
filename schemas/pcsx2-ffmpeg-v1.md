# FM v1 — FFmpeg del observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-ffmpeg`.
Hereda [DB](pcsx2-dependencies-v1.md) y conserva el gate general IB.

Como responsable del observador host, necesito bibliotecas multimedia probadas
y aisladas para completar la configuración enlazada de PCSX2.

## Requisitos EARS

- **FM01 — Procedencia.** CUANDO prepare FFmpeg 8.1, DEBERÁ verificar URL/hash
  contra la receta fijada, validar la extracción, conservar originales/licencias
  y capturar el prefijo previo. DEBERÁ comprobar NASM host y evidencia anterior.
- **FM02 — Perfil.** CUANDO configure, DEBERÁ reproducir componentes de la
  receta con target x86_64/macOS 11.0, autodetección desactivada, bibliotecas
  shared avcodec/avformat/avutil/swresample/swscale y protocolo file. DEBERÁ
  registrar encoders/muxers efectivos y exclusiones, resolver solo dependencias
  del prefijo privado/SDK y separar herramientas host de objetos objetivo.
- **FM03 — Capacidad.** ANTES de construir, DEBERÁ verificar fuentes menores
  de 512 MiB, como máximo 2.000 objetos planificados y 14 GiB libres. MIENTRAS
  construya con dos jobs, DEBERÁ detener su grupo si el build supera 2 GiB
  lógicos/asignados o quedan menos de 12 GiB libres. DEBERÁ reutilizar el
  supervisor SRC40 verificado por hash y conservar muestras. SI el perfil
  supera esos límites, DEBERÁ revisar el presupuesto antes de construir.
  La reserva general de 20 GiB no cambia; el muestreo no es una cuota.
- **FM04 — Multimedia.** CUANDO ejecute consumidores, DEBERÁ comprobar
  codificación de cuadros/PCM propios, escritura de un contenedor y resultados
  independientes de conversión de imagen/remuestreo. DEBERÁ cubrir las cinco
  bibliotecas, metadatos, tamaños, timestamps y contenido cuando sea observable.
- **FM05 — Errores.** CUANDO reciba opciones o formatos inválidos, DEBERÁ
  comprobar rechazo y recuperación posterior. CUANDO drene un encoder,
  DEBERÁ comprobar finalización y rechazar envíos posteriores según la API.
  DEBERÁ gestionar propiedad/liberación de contextos, paquetes y buffers.
- **FM06 — Pruebas.** CUANDO valide, DEBERÁ ejecutar tests originales
  aplicables sin cambiar sus expectativas y conservar fallos/exclusiones.
  DEBERÁ rechazar raíces explícitas ausentes y comprobar carga efectiva.
  NO DEBERÁ habilitar decoders o depender de hardware para aparentar cobertura
  que el perfil de receta no proporciona.
- **FM07 — Instalación.** SOLO CUANDO aprueben las pruebas previas,
  DEBERÁ instalar. DESPUÉS DE instalar, DEBERÁ repetir consumidores nuevos,
  auditar binarios/manifiesto/arquitectura/mínimo macOS y conservar archivos
  y enlaces anteriores. DEBERÁ explicar transformaciones de instalación.
- **FM08 — Continuidad.** CUANDO cierre, DEBERÁ repetir CMake PCSX2 y gate
  en salidas nuevas, publicar código propio/metadatos y detallar MoltenVK.
  DEBERÁ distinguir validación host, CI remota, frameworks/hardware, build
  completo, instrumentación, mapa efectivo y ejecución física en 3DS.

## Diseño y tareas

La coordinación separa procedencia, configuración, supervisión, consumidores y
auditoría. Los consumidores usan interfaces públicas e inyectan las raíces de
headers/bibliotecas; las responsabilidades de buffers, codificación, contenedor
y oráculos se separan. Los tests originales permanecen en el área privada.

1. Verificar archivo/licencias/NASM y prefijo; inspeccionar perfil, API y
   tests disponibles (FM01/FM02/FM06).
2. Configurar y auditar objetos/comandos antes del build supervisado (FM02/FM03).
3. Probar datos sintéticos, negativos, recuperación y tests originales;
   comprobar resultados y carga (FM04–FM06).
4. Instalar tras aprobación, repetir con consumidor nuevo y auditar prefijo,
   manifiesto, binarios y fuentes (FM07).
5. Repetir configuración/gate, publicar evidencia y detallar MoltenVK (FM08).
