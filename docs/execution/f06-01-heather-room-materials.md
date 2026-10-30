# HM-T4c.3.3 — materiales originales integrados

2026-10-30. **Build `c3aae59d1a70` instalado y verificado en SD**, con copias A/B
idénticas. Integración terminada para el perfil de inspección de hp34.
Tarjeta expulsada de forma segura. El usuario confirma funcionamiento correcto
en consola; la aceptación completa de HM-T5 sigue pendiente.

## Cambio y alcance

SRM2 añade nueve materiales y una asignación/visibilidad por forma. El
conversor autentica las escenas HRS A/B, el informe HRB v4 y el dump GS fijado;
reconstruye las nueve combinaciones originales y coteja los hashes de RGBA
y paleta antes de normalizar el alfa. No se cargan las 44 variantes posibles.
Contrato: [materiales v2](../../schemas/heather-room-materials-v2.md).

Las 31 formas y sus 27 900 vértices expandidos permanecen en el recurso.
Se dibujan 26 formas internas y se omiten `149504`, `222736`, `245648`, tal
como en la evidencia de asignación. Las nueve imágenes usan repetición U/V,
filtrado lineal, sin mipmaps ni inversión vertical. Los dos vidrios y las
trece texturas de Heather se conservan byte a byte.

Los pases internos opaco, recorte alfa >0 y mezcla alfa mantienen el orden
de origen; la mezcla **escribe profundidad** y no se desplaza al final.
Cada pase restablece explícitamente combinación de textura, alfa, profundidad
y caras. Se mantiene la cámara fija y la ordenación de vidrio/pelo del visor.

La iluminación RGB y la niebla negra se reconstruyen por vértice de origen
a partir de 239 paquetes por frame, con estado completo cotejado y cobertura
de todos los vértices, incluidos los solapamientos. Los frames 1 y 3 producen
las mismas muestras. Se almacena `RGB / 128 × fog / 256`; el renderer conserva
estos colores y no aplica la paleta diagnóstica anterior.

**Límites de fidelidad:** iluminación y visibilidad por forma corresponden
al estado capturado. La combinación previa de RGB/niebla aproxima su
interpolación GS; no es reproducción exacta por píxel ni iluminación dinámica.
Se preserva la triangulación de inspección: 9 044 triángulos internos
enviados, frente a 4 912 habilitados por el VU en la cámara de referencia.
No se trasplanta el descarte de triángulos de esa cámara a la cámara propia;
el perfil sigue siendo de dos caras. La fidelidad del descarte VU, otros
estados de visibilidad y la composición completa de escena PS2 quedan fuera
de esta entrega. Los contactos no se infieren de la visibilidad del render.

## Memoria, validación y fallos

El lector admite SRM1 y SRM2, rechaza estructura/CRC/estados/índices inválidos
y valida las nueve texturas antes de publicar la escena. La sustitución
conserva la escena anterior ante fallos de apertura, lectura o cierre.
El renderer vuelve a comprobar cada CRC antes de subir los píxeles y libera
recursos parciales ante fallos de lectura, textura o flush. No añade reservas
de heap por frame.

| Contabilidad | Bytes |
| --- | ---: |
| Texturas residentes | 27 787 264 (26.5 MiB) |
| Staging de textura | 2 097 152 |
| Mapa CPU + GPU | 2 009 704 |
| Frame dinámico CPU + GPU | 1 400 184 |
| Modelo y scratch | 961 864 |
| Staging de carga/reemplazo | 2 789 904 |
| Reserva plataforma | 12 582 912 |
| Escena | 49 628 984 |
| Extra runtime | 2 097 152 |
| **Total integrado** | **51 726 136 / 67 108 864 (49.33 / 64 MiB)** |

Es presupuesto conservador; no mide el pico físico de la consola. El nuevo
SRM2 ocupa 1 005 320 bytes, 16 más que `sizeof(RoomMap)`; el staging contabiliza
su tamaño de wire explícitamente, además del candidato.

| Validación | Resultado |
| --- | --- |
| CTest seleccionadas Release / ASan+UBSan / GCC | 5/5 en cada configuración |
| Conversor privado con datos inventados | 23/23; líneas 95.4 %, ramas 86.1 % |
| Empaquetado y despacho SRM1/SRM2 | 22/22 |
| Resto de regresión Python seleccionada | 206/206 |
| Estados de dibujo | 49 transiciones; cobertura 100/100 |
| Dominio de escena | Líneas 99.5 %, ramas 95.8 % |
| Lector SRM1/SRM2 | Líneas 100 %, ramas 99.1 % |
| Lector runtime | Líneas 96.2 %, ramas 86.5 % |
| Renderer | Líneas 99.4 %, ramas 95.6 % |
| Main / bucle | 97.6/85.8 % y 100/92.6 % |
| Auditoría privada A/B × Release/sanitizadores | 16 frames conformes |
| ZIP extraído A/B × Release/sanitizadores × 25/60/143 Hz | 12 replays de 100 pasos |
| ARM devkitPro fijado | Compilación y seis checksums aprobados |

La auditoría compara geometría, UV, cámara, colores publicados, 26 rangos
internos y textura/pase asignados, así como los rangos y vértices dinámicos
de Heather/vidrio frente a HRS. El test de subida recorre todos los píxeles
512×512 mediante un inverso independiente de la dirección Morton, incluidos
canales y alfa. Los tests sintéticos ejercitan los 23 slots de textura,
fallos de creación/flush, corrupción y limpieza sin fugas del doble SDK.

La revisión final verificó límites de arrays, publicación al final, herencia
de estados y el presupuesto con el wire SRM2. Se conservó la primera salida
privada v1: su verificación final detectó límites de lectura inconsistentes
del informe. La versión v2 corrige esa custodia y supera la relectura A/B.
Los contadores GCC previos se archivaron antes de medir esta revisión para
no mezclar sellos de compilación.

## Ejecutable observado en Azahar

Azahar 2126.2, perfil privado aislado New 3DS, Vulkan, resolución 1× y objetivo
100 %. Se comprobó visualmente el ID `c3aae59d1a70`, suelo, paredes con azulejos,
objetos y Heather texturados. La imagen permanece estable al caminar y girar.

- Arranque: `CPU: New fast`, `Load: 19144 ms`, `Error: none`, `Accounted: 49.33`.
- Una lectura estable: `FPS submit: 29.9`, `Frame: 33.4 ms`.
- A y L: PAUSED, Step 0, Clip 101, Q12 0, R raw/steps 0/0.
- R mantenido 2 s: PAUSED, Step 1, Q12 614, R raw/steps 1/1.
- Reanudar, caminar 1 s y girar 0.5 s, pausar: posición y orientación cambiadas,
  Step 250, Clip 101, Q12 3070, Error none. Incluye espera entre acciones;
  ese contador no es una medición de cadencia.
- START devuelve a la lista de aplicaciones; cierre normal del emulador confirmado.

Estas observaciones no acreditan rendimiento ni aceptación física de HM-T5.

## Entrega privada reproducible

Runtime: `heather-room-material-runtime-v2-copy-a` y `-copy-b`.
Entrega: `heather-room-3ds-materials-v1-copy-a` y `-copy-b`, todos bajo
`/Users/germancontreras/sh3-private-data`. La copia a SD se verificó el 2026-10-30.

Cada ZIP incluye 29 archivos en `/3ds/sh3_heather_room/` y `SHA256SUMS`
(30 entradas), con CRC y hashes de todas las entradas comprobados.

| Archivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `sd-card.zip` | 29 352 265 | `f59a159303f5426e9e40f8e0fc8daf086e6a8eba9f8a34dfa3fd524130d75bcf` |
| `sh3_heather_room.3dsx` | 237 140 | `809f46eb6d46c20f9ee61635fe4e5c1827a29e86aa5e3689ee41e61cd5f8a110` |

Código ARM en `build/heather-room/materials-code-v1/`. Informes locales sin
payload: `heather-room-materials-integration-v1.json`,
`heather-room-materials-package-v1.json`, `heather-room-delivery-c3aae59d1a70.json`
y `heather-room-emulator-c3aae59d1a70.json`, bajo `reports/local/`.
Guía incluida: [HM-T5](../compatibility/heather-room.md).

## Instalación en SD verificada

Entrega solicitada el 2026-10-30, registrada a las 19:20:56 UTC. Se comprobó
la identidad de la SD `NO NAME` (UUID `2B1167A8-45D2-3BF1-A4FF-4E0B1F149945`)
y la instalación anterior contra su recibo antes de escribir. Las fuentes
A/B, manifiesto, ZIP y ejecutable coincidieron con sus hashes fijados.

Los 29 archivos, 29 344 784 bytes, quedaron en `/3ds/sh3_heather_room/`;
se releyeron completos y sus SHA-256 coincidieron después de sincronizar.
El build anterior `161090bc9fd5`, incluidos sus archivos auxiliares de macOS,
se conservó y verificó en
`/sh3-room-install-c3aae59d1a70-20261030T192056Z/previous-161090bc9fd5/`.
El visor `/3ds/sh3_heather_probe/` permaneció idéntico.

Expulsión segura confirmada por `diskutil` y ausencia del volumen montado.
Recibo local: `reports/local/heather-room-sd-delivery-c3aae59d1a70.json`.
Esta entrega acredita los archivos de la SD; no acredita ejecución ni
aceptación física de HM-T5 para este build.

## Prueba física comunicada por el usuario

El 2026-10-30, tras instalar `c3aae59d1a70`, el usuario confirma:
«prueba realizada, funciona correctamente». Se registra funcionamiento general
satisfactorio de la entrega con materiales originales en consola.

La confirmación no incluye nuevas lecturas del HUD ni resultados desglosados
del protocolo. Se conserva como evidencia funcional, con HM-T5 parcial:
siguen pendientes las mediciones de rendimiento/memoria y los casos sin
resultado específico, incluido recorrido/contactos, HOME+tapa combinado,
recuperación de carga y diez aperturas/salidas. Las observaciones detalladas
de builds anteriores conservan sus propios IDs.

Recibo: `reports/local/heather-room-physical-c3aae59d1a70.json`.
Los recibos previos de empaquetado y SD mantienen su estado histórico.

Posteriormente el usuario solicita aplazar las mediciones y pruebas adicionales
de HM-T5 y continuar el proyecto. Sigue la instancia preparatoria
[F06.02/heather-turns](../specs/sh3-3ds/heather-turns.md).
