# HS-T4: selector, ARM y comparación preparada

Build **f64760613473**, aplicación separada `sh3_heather_skinning`.
La preparación usa el perfil HG de cinco clips y hp34; el paquete HG aceptado
`0188790baedd` queda conservado. HM-T5 adicional y pared 60 siguen aplazados.
La aceptación y las mediciones en consola pertenecen a HS-T5.

## Integración

El selector A=CPU / L=híbrida precede a la carga. SELECT vuelve al selector,
con destrucción del controlador, hook y propietario GPU antes de cargar otra
variante. START tiene prioridad y los cambios de ciclo de vida exigen soltar
los botones. Ambas variantes arrancan PAUSED, Step 0, Clip 101, Q12 0.
La pantalla distingue modo solicitado, activo y causa de fallback; un fallo
al preparar el candidato conserva CPU y no se registra como medición híbrida.

El controlador, contactos, paso fijo y las cinco acciones permanecen compartidos.
Se conservan validación y expansión CPU de toda la escena, su copia dinámica,
materiales, cámara, habitación y transparencias. Los opacos se dibujan con el
plan de 15 lotes, 6558 vértices GPU, 15846 índices y 200 matrices subidas por
cuadro. Este prototipo permite comparar costes; no presupone una mejora.

La captura vive en heap, reserva 51.472 bytes y no asigna ni escribe archivos
por cuadro. X descarta 32 cuadros y recoge 256 llamadas; Y muestra dos páginas
con mediana/p95/máximo. Cadence usa 255 diferencias; las diez fases CPU y el
total se distinguen de la cola GPU. No se refresca el HUD durante una ventana.
Pausa/reinicio/suspensión cancelan una captura en curso. Los resultados completos
permanecen en RAM hasta X, SELECT o salida; no se crean logs en la SD.

El tiempo GPU se lee después de adquirir la cola anterior en FrameBegin y
antes de que FrameEnd reinicie el contador. Cada muestra lleva el ID del envío
anterior; un cuadro ocupado no consume esa asociación y una cola de error no
se cuenta como escena completa. La última muestra espera su finalización.
La duración incluye transferencias, y FrameEnd puede realizar flush global:
no equivale a tiempo exclusivo de shader ni se suma a CPU. Semántica contrastada
con [renderqueue.c de citro3d 1.7.1](https://raw.githubusercontent.com/devkitPro/citro3d/v1.7.1/source/renderqueue.c).

## SDK, ABI y memoria

Compilación Release ARMv6K con devkitARM r68-1/GCC 16.1.0, libctru 2.7.0-1,
citro3d 1.7.1-2 y picasso 2.7.2-3 en la imagen fijada por el repositorio.
Se comprobó el shader binario congelado de 408 bytes, atributos de 64 bytes,
paletas de 30 matrices y dos buffers de filas de 9648 bytes cada uno.
El layout ARM se extrajo de un objeto compilado, sin ejecutar código ARM.

| Recurso | Resultado |
| --- | ---: |
| Presupuesto CPU con captura | 51.875.924 B (49,47 MiB) |
| Presupuesto híbrido con captura y staging | 52.364.868 B (49,94 MiB) |
| Incremento híbrido ARM | 488.944 B |
| Margen hasta el límite del 80 % de 64 MiB | 1.322.223 B |
| Reserva SDK/código/targets/comandos/heap incluida | 12 MiB |
| Reserva runtime/candidato incluida | 2 MiB |
| Pila conservadora Clang, incluida reserva externa de 8 KiB | 32.416 / 32.768 B |
| Pila conservadora ARM, incluida entrada y reserva | 27.700 / 32.768 B |
| Código + datos + BSS ELF | 254.032 B |
| Ejecutable 3DSX | 251.456 B |

El propietario RoomRenderer pasó a heap antes del bucle, reduciendo su marco
de pila. No se elevó el límite de 32 KiB. El inventario de pila suma los marcos
seleccionados y la reserva de recursión del sort, además de 8 KiB externos;
no es una medición de watermark en hardware ni una auditoría completa del SDK.

Con recursos privados, el seguimiento host dio pico coexistente de 34.304.681 B,
residente CPU 32.235.617 B e híbrido 32.707.577 B. Incluye captura y renderer
reservados como en la entrada. Cada modo ejecutó 512 actualizaciones con
asignaciones y liberaciones prohibidas durante el tramo estable, incluidos
pasos R, pausas, suspensión, reinicio y cálculo de estadísticas. Cero asignaciones
por cuadro, liberación completa. Estos datos son tamaños de solicitudes C++ y
buffers del doble SDK, no RSS ni mediciones físicas de consola.

## Validación y evidencias

- Suite Release: 385/386 pasaron inicialmente; la prueba nueva de ventana
  detectó que el arranque aún estaba RUNNING. Se corrigió con el evento de pausa
  compartido y `room_runtime` pasó después, incluidas las dos variantes y fallback.
  Los 386 casos quedan cubiertos por esa corrida y la regresión corregida.
- 11 pruebas ASan/UBSan aprobadas, con 54 vectores nativos y regresiones de
  giros, locomoción, controles, bucle y selector. Los SDK de estas pruebas son dobles.
- 389 pruebas Python aprobadas, incluidas identidad por stem, ZIP determinista,
  paletas/shader y contrato HG. Ruff, formato y comprobación del repositorio.
- GCC: pruebas sintéticas de selector/captura/recursos y cobertura por archivo:
  entrada 97,2 % líneas / 86,6 % ramas; captura 100 % / 93,4 %;
  renderer 99,0 % / 95,8 %. Se añadió el gate de captura y build HS a CI.
- Escena privada autenticada A/B, extracción del paquete y ocho ejecuciones
  nativas Release/ASan: entrada completa, equivalencia renderer y recursos
  CPU/híbridos. La equivalencia del shader evaluado por el doble sigue siendo
  binary32 host; no acredita precisión ni rasterización PICA.

La primera recogida de cobertura leyó por error configuraciones históricas;
se descartó esa recogida y se usó un archivo con `search-path` exclusivo de
HS-T4. Se conservan logs y resultados negativos en la evidencia local.

Directorio de evidencia: `build/heather-skinning-delivery/`, informe agregado
`reports/local/heather-skinning-delivery-v1.json` e inventario de entrega
`reports/local/heather-skinning-delivery-f64760613473.json`.

## Paquete y siguiente fase

Copias privadas `heather-skinning-3ds-f64760613473-v1-copy-a/b`, cada una con ambos
modos. Son 29 archivos instalables: los 26 recursos autenticados HG/hp34,
ejecutable, icono y guía. El ZIP determinista tiene 30 entradas contando
SHA256SUMS. Publicación exclusiva por copia, archivos 0600/directorios 0700,
relectura byte a byte y hashes iguales A/B. No hay garantía transaccional entre
las dos carpetas ni frente a pérdida de energía.

El [protocolo HS](../compatibility/heather-skinning.md) incluye identidad,
selector, lecturas iniciales, pausa/R, reinicio, HOME/tapa, comparación visual
y tres ventanas alternadas por variante. Se mantienen pendientes la medición
GPU física, las tolerancias HSN y las curvas con cargas crecientes; este build
solo contiene el caso real fijo. No se instaló ni se modificó la SD.
