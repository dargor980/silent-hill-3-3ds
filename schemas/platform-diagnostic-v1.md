# Diagnóstico PT v2 — PD v1

Como investigador, necesito intercambiar un diagnóstico que conserve el alcance
de PT v2 sin confundirlo con IP/NC ni con un permiso de captura.

## Requisitos EARS

- **PD01:** CUANDO el lanzador configure el diagnóstico, DEBERÁ fijar localmente
  PT v2 y las tres evidencias de política/aplicación/plataforma. SI falta evidencia
  o el perfil es v1/desconocido, DEBERÁ rechazar antes de publicar una observación.
  La solicitud remota SHALL NOT seleccionar perfil, archivos o política.
- **PD02:** CUANDO se reciba una solicitud, DEBERÁ contener solamente versión de
  protocolo, desafío de 128 bits no nulo y secuencia u64 no nula ni agotada.
  Tamaño, versión, truncación o extensión incorrectos DEBERÁN rechazarse sin datos
  parciales. El desafío correlaciona; SHALL NOT autenticar al interlocutor.
- **PD03:** CUANDO se emita una observación, DEBERÁ conservar perfil, alcance,
  confianza en plataforma, nacimiento/nonce, hashes de inventario, revisión,
  conteos y las tres evidencias exactas del lanzador. Inventarios fallidos,
  incompletos, v1, contadores inválidos o conteos fuera de capacidad DEBERÁN fallar.
- **PD04:** CUANDO se incluyan hechos AP, DEBERÁ conservar los dieciocho estados
  desconocido/satisfecho/violado y su época host/generaciones PINE/VU/GS. SI ese
  alcance runtime no se observó, DEBERÁ emitir las cuatro generaciones en cero y
  todos los hechos desconocidos. Generaciones parciales DEBERÁN rechazarse.
  Valores AP internos no reconocidos DEBERÁN normalizarse a desconocido (AP07);
  valores de wire no reconocidos DEBERÁN rechazarse por formato.
- **PD05:** CUANDO se emita un rechazo, DEBERÁ conservar únicamente desafío,
  secuencia y causa tipada; inventario, evidencias, hechos y generaciones DEBERÁN
  quedar vacíos. Un fallo del encoder DEBERÁ borrar el buffer de salida.
- **PD06:** CUANDO el consumidor decodifique, DEBERÁ validar el tamaño exacto,
  versión, campos reservados, unión y correlación. Una observación DEBERÁ coincidir
  con las evidencias locales y PT v2; SHALL NOT reintentarse con otro perfil.
- **PD07:** MIENTRAS el canal/peer, estabilidad de intervalo, deadline, cancelación
  y gates del emulador no estén acreditados, el dato decodificado DEBERÁ identificarse
  como no autenticado. SHALL NOT convertirse en `Observation` IP, armar guardias,
  leer RAM ni generar capacidades, aun con todos los hechos AP satisfechos.
- **PD08:** CUANDO se valide PD, DEBERÁ usar un vector independiente C++/Python,
  probar cada truncación, campos reservados, mezcla de versiones/evidencias,
  correlación, límites, rechazo sin payload y todos los estados AP. DEBERÁ conservar
  los contratos IP/NC/PT existentes y los gates de CI host.

## Diseño y SOLID

El codec C++ puro recibe configuración del lanzador y resultados del proveedor;
no accede al emulador ni al transporte. Decodifica la solicitud y serializa una
respuesta en almacenamiento fijo. El consumidor Python mantiene tipos separados:
`UnverifiedPlatformDiagnostic` y `UnverifiedDiagnosticRejection`. Valida formato
y expectativa local, pero no puede demostrar que esos bytes provengan del proveedor.
No se conecta al `DiagnosticGuard` IP: su contrato estricto permanece intacto.

La negociación es comprobación explícita de un único contrato permitido: PD v1
con PT v2. El proveedor no aprende política del cliente; el consumidor compara
la oferta con su expectativa local. Un rechazo o discrepancia no abre fallback.
No se añade socket/comando a PCSX2. La futura sesión autenticada deberá consumir
estos tipos y volver terminales las pérdidas/replays/cambios antes de publicarlos.

La época y generaciones se leen por el futuro adaptador en una frontera CPU
válida, con identidad antes/después. El codec no acredita esa frontera ni su
coherencia. Una sonda de arranque sin VM debe usar todos esos campos en cero.
Las respuestas completas son diagnósticas, incluso con dieciocho hechos satisfechos.

## Codificación canónica

Little endian, sin padding, strings, rutas ni campos de capacidad. Solicitud de
32 bytes: ASCII `SH3PDQ01` (8), desafío (16), secuencia u64 (8).
Respuesta de 294 bytes:

| Offset | Campo | Bytes |
| ---: | --- | ---: |
| 0 | ASCII `SH3PDR01` | 8 |
| 8 | estado: observación=1, rechazo=2 | 1 |
| 9 | perfil PT: v2=2 (rechazo=0) | 1 |
| 10 | alcance application_headers=1 (rechazo=0) | 1 |
| 11 | platform_assumed=1 (rechazo=0) | 1 |
| 12 | causa: ninguna=0; rechazo 1–9 | 1 |
| 13 | reservado, siempre cero | 3 |
| 16 | desafío de la solicitud | 16 |
| 32 | secuencia u64 | 8 |
| 40 | PID u32, nacimiento ns u64, nonce del proveedor (16) | 28 |
| 68 | hashes de archivos, imágenes, política, aplicación, plataforma | 160 |
| 228 | revisión del loader u64 | 8 |
| 236 | imágenes aplicación y plataforma, dos u32 | 8 |
| 244 | dieciocho hechos AP en orden de `AdmissionCondition` | 18 |
| 262 | época host y generaciones PINE/VU/GS, cuatro u64 | 32 |

Causas: configuration=1, inventory=2, identity_changed=3, peer_lost=4,
deadline=5, cancelled=6, protocol=7, lifecycle=8, unavailable=9. El codec solo
transporta la causa suministrada; no implementa esos monitores. Rechazos exigen
ceros en 40–293. Observaciones exigen cinco hashes y nonce no nulos, PID
1..INT32_MAX, nacimiento no nulo, revisión/secuencia/generaciones observadas
1..UINT64_MAX−1. Aplicación >=1; total de imágenes <=1024. Nacimiento admite
UINT64_MAX, conforme al proveedor `ProcessBirth`; no es contador de eventos.

## Tareas

- [x] **PD-T1 / PD01–05:** implementar tipos/codec C++ de almacenamiento fijo,
  normalización AP y rechazo vacío. Preservar resultados originales por valor.
- [x] **PD-T2 / PD06–08:** implementar consumidor Python independiente, vector
  binario común y pruebas adversariales/cross-language; incorporar a CI host.
- [x] **PD-T3 / PD08:** compilar cuatro modalidades, verificar cobertura,
  compatibilidad y custodia; publicar alcance sin atribuir autenticidad al codec.
- [x] **PD-T4 / PT-T5b:** autenticar peer nativo y enlazar sesión al inventario;
  negativos de reinicio, reproducción, desconexión y retorno a identidad anterior.
- [ ] **PD-T5 / PT-T5c:** integrar ejecución/cancelación fuera del hilo CPU,
  presupuestos 5 s/2 s, callbacks tardíos y gates runtime en candidato privado.
