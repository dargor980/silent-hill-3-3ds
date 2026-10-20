# F02.07 / LP-C — Núcleo de guardia de continuidad

Fecha: 2026-10-18. Fuente: SRC65. Contrato:
[LG01–LG08](../../schemas/lifetime-guard-v1.md). Evidencia:
[metadatos públicos](../compatibility/lifetime-guard-evidence.json).

## Resultado y alcance

Se implementó `sh3::observer::LifetimeGuard`, un núcleo C++17 host que invalida
un intervalo ante escrituras protegidas, cambios de sesión/época, huecos,
duplicados, retrocesos, reset, intento de restauración o pérdida de eventos.
La primera causa persiste; liberar y reasignar el objeto, restaurar sus bytes o
intentar rearmar no recupera un intervalo fallido.

**La integración de los productores de PCSX2 está pendiente.** Un estado
`sealed` solo valida las notificaciones suministradas. No demuestra que hayan
llegado todas las escrituras ni acredita ejecución, continuidad real o lectura.
JR conserva su rechazo predeterminado y esta unidad no produce eventos `Read`.

## Investigación y cobertura pendiente

Dos ventanas de asignación/liberación, 548 bytes en total, coinciden entre el
ejecutable y el estado privados. Se fijaron cinco escrituras sobre handle,
generación y bloqueo, y se reverificaron las tres ventanas de SRC64. Son referencias
estáticas para investigar reutilización; no son una lista exhaustiva de escritores.
El estado conservado tiene cero filas activas y no sirve como inicio de captura.

Se contrastaron siete archivos de PCSX2 en el commit fijado
`fd9d310ccbb6b8b62c976da8886a3c8fd3a10ff3`, contra sus hashes históricos y las
copias baseline/instrumentada. Seis son iguales; `VMManager.cpp` conserva únicamente
su extensión OBS1 previa para consultar escrituras pendientes de estados.
Los números de línea y hashes exactos están en la evidencia.

| Superficie consultada | Hallazgo y trabajo requerido |
|---|---|
| `VMManager.cpp` | Reset, cambios de configuración e intento de carga requieren invalidación host antes del efecto, incluso si falla la carga. |
| `vtlb.cpp` | Escrituras del intérprete, caminos de caché y copias por bloque requieren resolución física y notificación. |
| `iR5900LoadStore.cpp`, `recVTLB.cpp` | El JIT emite escrituras por rutas distintas del intérprete; un hook solo en este último no basta. |
| `SPR.cpp` | Existen copias directas desde scratchpad hacia RAM que deben cubrirse. |
| `SaveState.cpp` | Restauración de memoria por copia; la época host no debe restaurarse con el estado. |
| `DebugTools/Breakpoints.cpp` | Las funciones de memcheck consultadas no proporcionan por sí solas una prueba de cobertura completa. |

Esta matriz identifica brechas, no acredita una auditoría exhaustiva de todos los
escritores. Ningún hook de continuidad se instaló en PCSX2 en esta unidad.

## Diseño y SOLID

El núcleo solo decide validez a partir de datos tipados; no abre archivos, sockets
ni estados, no asigna memoria dinámica y no depende de PCSX2. La interfaz pequeña
`arm/notify/report` permite que adaptadores de captura y pruebas suministren datos
sin incorporar adquisición al validador. La integración dependerá de este
contrato, manteniendo separados productor, transporte y reconciliación JR/CP.
No se introduce herencia para responsabilidades que no requieren sustitución.

Protege 80 bytes: raíz, cabecera del pool, vtable y campos de identidad/referencias
de la fila. Posición y caché son mutables y sus valores siguen a cargo de JR/CP.
Las escrituras iguales también invalidan; cruzar un límite hacia bytes protegidos
invalida aunque el inicio de la escritura esté permitido. El plan exige estructuras
físicas completas sin alias y dentro de RAM.

El contador u64 debe ser consecutivo; el ciclo puede repetirse durante una pausa,
pero el cierre exige progreso respecto al inicio. Hay un máximo de 1.000.000 de
notificaciones y 60 segundos de ciclos por intervalo, con memoria constante.
El productor debe serializar todas las llamadas antes de sus efectos. Este contador
interno no sustituye los límites de estados y solicitudes regionales OBS1.

## Reproducibilidad y pruebas

Los dos análisis estáticos produjeron informes idénticos de 5.103 bytes, SHA-256
`b475b5802a179b56106259f4302d90f9519dff014c8e0a861b079eb76b8c8063`.
Se reverificaron ISO, ejecutable, catálogo, contenedor, recurso y estado de origen.
El nuevo plan privado se creó sin sobrescritura, con directorio 0700 y archivo
0600; los lectores se cerraron antes de publicar y las fuentes quedaron intactas.

Se añadieron **once escenarios CTest**, con fixtures propios: identidad, secuencia,
ciclos, presupuesto, escrituras, ciclo de vida, protocolo, terminales y límites.
Incluyen cada byte protegido, cambios sin diferencia final, reciclaje, restauración
fallida, overflow y **5.120 combinaciones** contrastadas con un oráculo por bytes.
Los checks permanecen activos en Release.

- **Debug, Release y ASan/UBSan:** 60/60 pruebas aprobadas en cada configuración.
- **Cobertura LLVM del núcleo:** 77/77 líneas, 92/92 ramas y 110/110 regiones;
  cabecera: 2/2 líneas, sin ramas. Gate local de líneas/ramas 80/80 aprobado.
- **Regresión Python:** 3.096/3.096 aprobadas, sin errores, fallos ni omisiones;
  5.303/5.348 líneas y 1.449/1.482 ramas, gate 80/80 aprobado.
- Ruff y formato: aprobados para los 137 archivos del alcance de CI. Controles
  de repositorio, custodia, enlaces, hashes y diff aprobados; entradas fijadas de
  SRC55–SRC64 intactas.

La preparación local corrigió tres supuestos del investigador: selección explícita
del SDK para LLVM; diferencia OBS1 ya existente en `VMManager.cpp`; y nombre
canónico `SPR.cpp` en el manifiesto. La cabecera sin ramas se trata como denominador
vacío, sin rebajar el umbral del núcleo. Las versiones iniciales de los scripts
auxiliares se conservaron; esos intentos no publicaron evidencia privada. Se
evitaron copias innecesarias en los bucles de fixtures y se repitieron las pruebas
host y la cobertura. No hubo fallos de los casos C++ ni de la regresión Python.

## Compilación y CI

`CMakeLists.txt` incorpora `sh3_lifetime` y los once casos bajo el bloque de pruebas
host. Los jobs existentes de Release, sanitizadores y cobertura GCC los descubren;
el filtro de `gcovr.cfg` ya incluye `tools/observer/`. No hacen falta datos originales
para ejecutar estas pruebas. Repetición local con CMake/CTest disponibles:

```sh
rtk proxy cmake --preset host-release
rtk proxy cmake --build --preset host-release --parallel 2
rtk proxy ctest --preset host-release
rtk proxy cmake --preset host-sanitize
rtk proxy cmake --build --preset host-sanitize --parallel 2
rtk proxy env UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ctest --preset host-sanitize
```

La medición local usó LLVM/Apple Clang 21 y SDK explícito, con instrumentación de
perfiles y exportación `llvm-cov`; sus artefactos quedan identificados por hash.
No se ejecutó aquí el gate GCC de CI ni la CI remota. Las fuentes del runtime
Nintendo no cambian; no se recompiló 3DS y el cambio de CMake afectará la identidad
de un build futuro. Tampoco se recompiló PCSX2 ni se abrió una nueva sesión.

## Tareas y siguiente unidad

- [x] **LG-T1:** sitios de asignación/liberación, matriz de brechas y dos análisis.
- [x] **LG-T2:** núcleo host de guardia y fixtures propios.
- [x] **LG-T3:** CMake, tres configuraciones, cobertura y regresión completa.
- [x] **LG-T4:** trazabilidad y criterios para integrar productores.

La siguiente unidad es **integrar y acreditar el productor de continuidad**:

1. **LG-I1 / LG03,06,07 — Cobertura de escrituras.** Completar el inventario de
   escritores físicos y aliases, incluyendo caché, JIT, copias directas, DMA y
   modificaciones host. Definir un modo de ejecución cubierto; cualquier ruta
   habilitada sin cobertura debe impedir armar. Instrumentar antes de cada efecto
   relevante. Entregables: matriz completa, adaptador y pruebas de cada ruta que
   cambian un byte protegido y lo restauran, o escriben el mismo valor. Aceptación:
   invalidación persistente en todas las rutas y ausencia de modos sin cubrir.
2. **LG-I2 / LG01,02,04–06 — Época y serialización.** Integrar identidad/época
   exclusivamente host, cierre/reset/restore/configuración, invalidación del JIT
   cuando corresponda y exclusión de escritores concurrentes. Probar intento de
   carga fallido, reset durante el intervalo, reordenamiento, huecos y agotamiento.
   Aceptación: ninguna restauración puede recuperar la guardia y ningún exceso
   puede descartarse silenciosamente. Medir coste y respetar el presupuesto.
3. **LG-I3 / LG05,07 — Extremos y transporte.** Armar desde el retorno real de
   apertura, antes del descriptor finalizado, y vincular el cierre al retorno de
   lectura. Extender captura/descubrimiento sin omitir ni renumerar pausas o
   sondeos. Transportar resultado, identidad y secuencia con validación estricta;
   probar falta de extremo, sello ajeno, desconexión y reporte truncado. Aceptación:
   JR permanece cerrado hasta acreditar cobertura y ambos extremos de la sesión.
4. **LG-I4 / LG08 — Integración verificada.** Compilar el observador privado con
   fuentes fijadas y ejecutar fixtures propios de escritura/restauración sin ISO.
   Repetir pruebas host/Python y conservar rechazos. Aceptación: evidencia de todas
   las rutas habilitadas antes de intentar LP-D; un `sealed` aislado no es suficiente.

Después siguen progreso temprano del worker y descubrimiento/captura LP-D en
español/Normal/Normal, desde antes de la carga y sin restaurar entre puntos:
≤48 estados, ≤256 solicitudes/hits, 60 segundos activos, 3.600 de pared,
8 GiB de etapa y 10 GiB libres, con cierre, custodia y dos reimportaciones iguales.
F02.07/Q05/G02, procedencia real, semántica de cámara, dos salas conectadas y
validación en New Nintendo 2DS XL permanecen pendientes.
