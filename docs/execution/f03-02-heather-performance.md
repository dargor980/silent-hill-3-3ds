# HP: primera optimización del visor de Heather

Fecha: 2026-10-24. [Spec HP](../specs/sh3-3ds/heather-performance.md).
Build **`8f778b6e4960`**, probado en New 2DS XL por el usuario.
**HP-T1–T4 completadas:** mayor fluidez reportada durante 60 s en cuerpo
y 60 s en cara. Se conserva el reloj de animación de inspección.

## Baseline y cambios

El usuario confirmó 60 segundos, rostro, SELECT/zoom/controles, START y
tapa/HOME en `f25a2d9bb316`, pero informó baja fluidez: ≈60,7 ms Skin+sort
CPU, 49 ms Submit+wait y 4,36 ms GPU previous. No hay FPS previos medidos
ni percentiles; no se suman etapas para deducirlos. La aceptación funcional
HI-T5b/HI-T6c consta en el [registro físico](../compatibility/heather-inspection.md).

La malla comparte 6.943 vértices entre 16.566 índices. El baseline calculaba
transformación de inspección y UV por índice, validaba 16.566 resultados y
volvía a emitir el cabello después de ordenarlo. Ahora prepara y valida
6.943 salidas únicas, calcula profundidad desde ellas y copia triángulos
en su orden final. Conserva posiciones originales, pesos deficientes y W;
no reduce geometría ni texturas. El scratch máximo aumenta en 192 KiB,
propiedad del presentador fuera de la pila, sin reservas por cuadro.

Se conserva la validación independiente del renderizador, su espera
`C3D_FrameBegin` antes de escribir el VBO, flush y liberación de recursos.
El SDK fijado expone `osSetSpeedupEnable`: se solicita CPU rápida al
identificar la familia New, se repite tras restaurar y se desactiva al salir.
Ante fallo de identificación se mantiene el modo predeterminado.
`CPU: New fast` indica solicitud al SDK, no MHz medidos.

`FrameCadence` mide presentaciones correctas por segundo transcurrido,
incluidos intentos ocupados y coste del HUD. Reinicia la ventana ante
suspensión/restauración o retroceso del reloj. La UI se actualiza cada
250 ms o al pulsar botones. `FPS submit` no mide barridos de pantalla ni
la velocidad nativa del clip.

## Validación

| Comprobación | Resultado |
|---|---|
| CTest Release completo | 353 aprobados |
| CTest ASan/UBSan completo | 353 aprobados |
| Python rig y contratos del repositorio | 82 aprobados |
| Oráculo escalar sintético | 32 poses/cámaras, 18.000 índices, 1/2/3 influencias, W deficiente y empates de profundidad; atributos exactos |
| Cotejo privado baseline/candidato | 160 cuadros, matrices/posiciones/salida ordenada: 113.562.880 bytes idénticos |
| Benchmark host ARM64/macOS, O2 | Mediana 0,189984 → 0,156433 ms; reducción de 17,66 % |
| ARM | SDK fijado, gate del shader y SHA-256 aprobados |
| Azahar 2126.2 ARM64/Vulkan | 90,063 s continuos a distancia 0,45; Q12 26358 → 12762 con bucles; rostro/cabello visibles |
| Controles en Azahar | SELECT, X/Y, giro, A pausa/reanuda, L reinicia, R avanza 614 en pausa, B recupera cuerpo, START sale |
| Hardware candidato | Usuario confirma 60 s por encuadre, mayor fluidez y controles; métricas abajo |

El benchmark incluye pose, deformación, ordenación y validación del
renderizador: cinco lotes de 240 evaluaciones. No incluye GPU y su porcentaje
no predice la mejora física. El cotejo compara bytes en memoria; no publica
recursos. En los extremos observados el HUD marcó 29,9 FPS submit y Azahar
30 FPS. Es observación visual, no traza por cuadro.

La automatización seleccionó inicialmente otra instancia vacía; se cargó
la ruta absoluta mediante UI y se comprobó el ID en pantalla. Ambas
instancias se cerraron; el proceso CLI terminó con código cero.
Los nuevos CTest entran en las matrices existentes host/sanitizadores/
cobertura; el job ARM ya compila el visor. No se afirma ejecución remota
de CI ni cobertura nueva medida localmente.

Recibos: `reports/local/heather-hardware-v1.json`,
`heather-performance-host-v1.json`, `heather-performance-equivalence-v1.json`,
`heather-performance-v1.json` y `heather-delivery-v3.json`.
Logs y capturas en `build/heather-performance/`; ARM en
`build/heather-performance-v1/`.

## Entrega

Paquete exclusivo: `/Users/germancontreras/sh3-private-data/heather-3ds-v3/sd-card.zip`,
18.955.345 bytes; SHA-256
`947b3203ee5a64e8229373c42957c6ab5b177fe8bd3b53c46614a2d20a999c91`.
ZIP A/B idénticos y releídos tras escribir. SRI y 13 texturas coinciden con
la entrega anterior; cambian código y guía. Entregado el 2026-10-24 en
`NO NAME/3ds/sh3_heather_probe/`: 17 archivos, 18.950.897 bytes, releídos
y verificados por tamaño y SHA-256. Se respaldaron los dos archivos
sustituidos y la SD se expulsó de forma segura. Recibo local:
`reports/local/heather-sd-delivery-8f778b6e4960.json`.
La prueba física HP-T4 fue confirmada por el usuario posteriormente.
SHA-256 `.3dsx`:
`c3c5ae8868d4cc1dee3e69b0403665cbb5c3608f21c8d6b6c22f3e8b642c8800`.

## HP-T4: resultado físico informado

El usuario confirma 60 s en cuerpo y 60 s en cara, mayor fluidez, controles,
START, tapa y HOME. Lectura aproximada conjunta, sin separación por encuadre:

| Métrica | Lectura |
|---|---:|
| FPS submit | 29,9 |
| CPU solicitada | New fast |
| Skin+sort CPU | 10,27 ms |
| Submit+wait | 23,1 ms |
| GPU previous | 6,34 ms |

Frente al baseline manual, Skin+sort y Submit+wait son menores; GPU previous
es mayor. No se calculan percentiles, FPS previos ni un factor global de
aceleración: son lecturas manuales y las etapas pueden corresponder a cuadros
distintos. `New fast` acredita la solicitud, no una frecuencia medida.
Reapertura no detallada; no bloquea la aceptación definida en HP-T4.
Recibo local: `reports/local/heather-hardware-v2.json`.

Se retoman el reloj nativo y la selección de locomoción de Heather.
