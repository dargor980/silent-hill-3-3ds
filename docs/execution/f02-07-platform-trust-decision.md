# F02.07 — Dirección de implementación sobre la confianza en la plataforma

Estado: se desarrolla la opción A tras la nueva solicitud de continuar con la
recomendación presentada. El perfil separado PT v1 se implementa y prueba de
forma aislada; ninguna opción está activada en el proveedor PCSX2.
Véanse el [contrato PT](../../schemas/platform-inventory-v1.md) y el
[informe actual](f02-07-platform-inventory.md). La propuesta original se conserva
por hash en SRC100 y como snapshot local de esta transición.

El contrato actual NC09 exige evidencia del vínculo de caché/subcachés/AOT con
archivos antes de integrar el inventario completo. CI07 exige además verificar
las páginas contra esos archivos. La investigación VN obtiene el vnode de las
24/27 traducciones AOT individuales en arranque/salida, incluido dyld, pero
abrir sus rutas devuelve EPERM y el proceso no conserva descriptores de esos
archivos en las dos observaciones. La identidad puntual no permite completar
sus digests. Los 14 objetos de datos transformados y el heap JIT tampoco quedan
acreditados por esta API.

Apple [describe el almacén protegido y los descriptores proporcionados por
Rosetta](https://support.apple.com/es-es/guide/security/secebb113be1/web).
Eso explica una limitación esperable; no es una certificación de nuestros mappings.
La prueba local no demuestra imposibilidad absoluta de cualquier otra interfaz,
pero sí descarta abrir estas rutas o retener descriptores ordinarios en las fases
ensayadas. Repetir el mismo censo no añade una prueba de origen.

## Opción A — macOS como base de confianza del entorno (recomendada)

Reconocer explícitamente kernel, dyld y Rosetta como parte de la plataforma de
confianza, y centrar la identidad verificable en PCSX2, sus dependencias de
aplicación, el proveedor y los insumos del proyecto. Es una garantía distinta de
acreditar los bytes de todo el runtime de macOS.

Antes de habilitar nada, crear un perfil nuevo y versionado, con estos requisitos:

1. CUANDO se seleccione este perfil, el lanzador DEBERÁ fijar su identificador y
   evidencia esperada; el cliente SHALL NOT activarlo ni ampliar su alcance.
2. CUANDO se informe identidad, el proveedor DEBERÁ separar aplicación verificada,
   plataforma asumida y observaciones parciales. SHALL NOT marcar como verdaderos
   los campos históricos de integridad completa de caché/AOT.
3. SI aparece una dependencia ajena al conjunto esperado de aplicación o falta
   evidencia necesaria para clasificarla, el proveedor DEBERÁ rechazarla. Un
   prefijo de ruta, tag de memoria o UUID SHALL NOT ser el clasificador suficiente.
4. CUANDO se mida el proceso, el proveedor DEBERÁ conservar controles de nacimiento,
   sustitución de archivos, revisión del loader y peer. Un fallo SHALL NOT activar
   automáticamente un perfil menos estricto.
5. CUANDO se capture estado del emulador, el proveedor DEBERÁ cumplir igualmente
   exclusión de escritores, JIT de EE/VU/IOP, DMA y ciclo de vida. Confiar en la
   plataforma SHALL NOT omitir esos controles ni abrir `read_ram` por sí solo.

Tareas tras elegir A: especificar la frontera exacta y un clasificador comprobable;
versionar perfil/evidencia; probar mezcla de perfiles, dependencias desconocidas,
errores y sustituciones; después integrar el diagnóstico aislado. Si no se obtiene
un clasificador suficiente, documentar ese límite antes de habilitar captura.
Se reutilizan los componentes actuales, conservando el perfil estricto y sus tests.

## Opción B — conservar la garantía exhaustiva

Mantener NC/CI sin cambios y estudiar un entorno que exponga la procedencia
requerida. Hace falta una prueba de viabilidad antes de otro build grande:
inventario de imágenes, referencias retenibles, transformaciones y código dinámico.
Cambiar solamente a PCSX2 arm64 no resuelve por sí solo la caché transformada de
macOS; cambiar a un Mac Intel tampoco demuestra su origen. Otro sistema requiere
sus propios adaptadores y pruebas, sin prometer de antemano que satisfaga el contrato.

Tareas tras elegir B: identificar entorno disponible, fijar el mismo alcance de
garantía, ejecutar una sonda mínima con presupuesto y decidir por evidencia si
continuar la implementación. Hasta entonces la captura permanece cerrada.

La dirección A cambia la garantía que podrá anunciar el perfil futuro. El núcleo
implementado declara plataforma asumida y no reemplaza los resultados estrictos
de NC/CI. Su activación sigue pendiente de clasificador nativo, validación del
candidato, peer y gates del emulador; no se ha habilitado captura.
