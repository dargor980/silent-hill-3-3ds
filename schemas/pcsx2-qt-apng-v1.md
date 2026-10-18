# QAP v1 — Plugin APNG Qt para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-qt-apng`.
Hereda [DB](pcsx2-dependencies-v1.md). Usa Qt y libpng/APNG privados validados.

## Requisitos EARS

- **QAP01 — Procedencia.** CUANDO prepare QtApng 1.3.0, DEBERÁ verificar
  archivo y parche contra la receta fijada, validar rutas antes de extraer,
  conservar originales/licencias y aplicar el parche sin fuzz en una copia.
  DEBERÁ inventariar los cambios y capturar archivos/enlaces previos del prefijo.
- **QAP02 — Dependencias.** CUANDO configure, DEBERÁ usar Release,
  x86_64/macOS 11.0, Qt Core/Gui 6.11.1 privados, libpng/APNG privada y ZLIB
  del SDK. DEBERÁ comprobar rutas efectivas de includes/enlaces y excluir
  las copias PNG/ZLIB incorporadas del build objetivo.
- **QAP03 — Capacidad.** ANTES de compilar, DEBERÁ exigir menos de 128 MiB
  de fuentes, como máximo 100 unidades de compilación y 14 GiB libres.
  MIENTRAS compile con dos jobs, DEBERÁ detener su grupo si supera 512 MiB
  lógicos/asignados de build o quedan menos de 12 GiB libres. DEBERÁ verificar
  el supervisor SRC40 por hash y registrar muestras. SI el alcance excede
  esos límites, DEBERÁ revisar el presupuesto antes de continuar. El gate IB
  general de 20 GiB permanece vigente.
- **QAP04 — Lectura animada.** CUANDO QImageReader lea APNG propios,
  DEBERÁ verificar dimensiones, orden, número y RGBA de los cuadros,
  incluyendo alpha, mezcla y disposición, retardos y repetición conforme
  al formato. DEBERÁ contrastar imágenes estáticas y errores con oráculos
  independientes del plugin; un formato anunciado no acreditará lectura.
- **QAP05 — Reproducción.** CUANDO QMovie reproduzca un APNG propio finito,
  DEBERÁ observar cuadros y finalización mediante su bucle de eventos, sin
  error. DEBERÁ verificar las propiedades temporales declaradas sin confundir
  tiempos de pared del host con una garantía de rendimiento.
- **QAP06 — Negativos.** CUANDO reciba contenido inválido o truncado,
  DEBERÁ comprobar rechazo de lectura y diagnóstico. DESPUÉS DEL rechazo,
  DEBERÁ recuperar lectura válida. DEBERÁ probar aislamiento del plugin y
  rechazar una raíz Qt explícita ausente, conservando cualquier limitación
  observada sin alterar expectativas del proveedor para ocultarla.
- **QAP07 — Instalación.** SOLO CUANDO aprueben consumidores y tests
  originales aplicables, DEBERÁ instalar. DESPUÉS DE instalar, DEBERÁ repetir
  desde consumidores nuevos y verificar carga efectiva del plugin/libpng,
  manifiesto, arquitectura, mínimo macOS y conservación del prefijo.
  SI una etapa falla, DEBERÁ conservarla y omitir pasos dependientes.
- **QAP08 — Continuidad.** CUANDO cierre, DEBERÁ repetir CMake PCSX2/gate
  en salidas nuevas y publicar solo código propio y metadatos. DEBERÁ
  detallar KDDockWidgets como siguiente unidad y distinguir validación host
  de CI remota, UI visible, juego, mapa efectivo y runtime Nintendo 3DS.

## Diseño y tareas

El coordinador privado separa adquisición/parches, configuración, supervisión,
consumidores y auditoría. Un generador propio escribe chunks APNG usando
compresión estándar y un modelo RGBA independiente; el consumidor Qt recibe
las rutas de fixtures y plugin como parámetros. Las pruebas del proveedor
se ejecutan desde copias privadas sin cambiar sus expectativas.

1. Verificar procedencia, dependencias, parche, licencias y tests; auditar
   unidades/enlaces y presupuesto antes del build (QAP01–QAP03).
2. Construir con supervisor verificado y registrar recursos/resultados
   conservando intentos fallidos (QAP02/QAP03).
3. Generar APNG propios, comparar cuadros/composición/tiempos, ejecutar
   QMovie, negativos, tests originales y trazas (QAP04–QAP06).
4. Instalar solo tras aprobar y repetir con consumidores nuevos; comprobar
   carga, arquitectura, manifiesto y hashes anteriores (QAP07).
5. Registrar configuración PCSX2/gate, evidencia y tareas siguientes (QAP08).

## Correcciones derivadas de las pruebas

La primera batería reveló discrepancias con los casos válidos. Para cumplir
QAP04–QAP07, una copia nueva DEBERÁ convertir reproducciones totales APNG a
repeticiones adicionales Qt, interpretar denominador cero como 100, excluir
la imagen inicial oculta del número de cuadros y rechazar firmas inválidas
en la selección del plugin. DEBERÁ preservar el build fallido, registrar
diff/hashes privados y repetir la batería sin cambiar tests del proveedor.
DEBERÁ permitir el sondeo de capacidades que QMovie realiza con un dispositivo
vacío; la lectura efectiva de archivos vacíos o firmas incompletas DEBERÁ
seguir rechazándose. Ambas condiciones DEBERÁN probarse juntas.
El caso propio de aislamiento DEBERÁ desactivar autodetección para impedir
que el lector PNG estático de Qt suplante al plugin APNG ausente.

El muestreo no es una cuota ni garantiza detectar picos intermedios. No se
atribuirá cobertura exhaustiva del formato a estos casos seleccionados.
