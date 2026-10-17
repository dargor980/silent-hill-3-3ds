# SD v1 — SDL3 para el observador host

Unidad `F02.07/origin/effective-mapping/instrumented-build/prerequisites/dependencies-sdl3`.
Hereda [DB01–DB08](pcsx2-dependencies-v1.md) e [IB](pcsx2-build-preflight-v1.md).

## Requisitos EARS

- **SD01 — Identidad.** CUANDO prepare SDL3, el procedimiento DEBERÁ verificar
  SDL 3.4.12 contra URL/SHA-256 de la receta PCSX2 fijada y conservar fuente y
  `LICENSE.txt` en la raíz privada.
- **SD02 — Configuración.** CUANDO construya SDL3, el procedimiento DEBERÁ
  generar una biblioteca compartida x86_64, conservar las exclusiones de vídeo,
  energía, sensores, diálogos y bandeja de la receta, y registrar por separado
  las opciones adicionales para construir pruebas. DEBERÁ limitar tanto la
  búsqueda CMake como `pkg-config` al prefijo privado y revisar el resultado
  para rechazar bibliotecas ARM64 de Homebrew.
- **SD03 — Pruebas del proveedor.** CUANDO ejecute CTest, el procedimiento
  DEBERÁ conservar inventario, selección, omisiones justificadas, códigos y
  resultados JUnit; DEBERÁ usar audio dummy y evitar pruebas interactivas.
  SI una prueba falla, DEBERÁ conservarla y resolver su causa antes de aceptar
  la dependencia; una omisión no contará como aprobada.
- **SD04 — Contrato de API.** CUANDO valide la biblioteca, un fixture propio
  DEBERÁ comprobar versión de cabecera/binario, orden y contenido de eventos,
  cambios y liberación de un mando virtual, conversión PCM en memoria y lectura
  acotada/EOF de un buffer. DEBERÁ incluir entradas inválidas o límites sin
  producir audio real, usar originales ni modificar mandos físicos.
- **SD05 — Integración.** CUANDO instale SDL3, un proyecto CMake propio DEBERÁ
  resolver `SDL3Config.cmake` exclusivamente en el prefijo privado, enlazar su
  target compartido y ejecutar el fixture contra cabeceras/biblioteca instaladas.
  DEBERÁ verificar arquitectura, manifiesto y ausencia de enlaces a Homebrew.
- **SD06 — Continuidad.** CUANDO pasen las pruebas seleccionadas y el fixture,
  el procedimiento DEBERÁ repetir CMake de PCSX2 en un directorio nuevo,
  registrar el primer faltante posterior y conservar pendiente el build completo,
  la instrumentación y el mapa hasta sus propias verificaciones.

## Diseño y tareas

El proveedor construye SDL y sus pruebas. El proyecto de fixture solo resuelve
el paquete indicado y prueba API públicas; cada caso tiene su responsabilidad
y libera recursos aun ante error. Los resultados privados guardan argumentos,
entorno y hashes; la evidencia pública contiene metadatos. El gate IB no cambia
y el runtime 3DS no incorpora SDL ni dependencias del emulador.

1. Verificar archivo/avisos/opciones y definir selección de tests según funciones.
2. Configurar y compilar con SDK explícito y pruebas; inventariar CTest.
3. Ejecutar tests seleccionados y fixture contra el árbol de build.
4. Instalar en el prefijo privado, ejecutar el proyecto CMake de integración y
   verificar dylib/manifiesto. Detener dependientes ante fallo.
5. Repetir CMake/gate de PCSX2, publicar evidencia y actualizar siguiente tarea.

Aceptación de esta unidad: SDL3 probada e instalada, fixture instalado aprobado
y configuración PCSX2 que supera SDL3. Las pruebas de dispositivos reales y
funciones deshabilitadas quedan fuera de esta aceptación y se registran aparte.
