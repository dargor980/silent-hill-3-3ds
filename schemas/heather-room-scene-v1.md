# HRS v1 — Datos y preparación de render de hp34

2026-10-29. HM-T4c.1, refinamiento de [HR01–12](heather-room-profile-v1.md).
Perfil diagnóstico: **31 formas, 29 con material neutro**, Heather original
MDL522/ANM525 y dos paneles con material verificado. La cámara es propia.
El bucle Citro3D, controles y suspensión se definen en la extensión
[HRR v1](heather-room-runtime-v1.md); el empaquetado `.3dsx` corresponde a HM-T4d.

## Paquete privado

[Preparador](../tools/pipeline/prepare_heather_room_scene.py) y
[conversor](../tools/pipeline/heather_room_scene.py). Exigen los pins del perfil
HR, catálogo, recibo y MAP/CLD/TEX en A/B. El manifiesto original de Heather,
su SRI2 y sus trece RGBA se cotejan por SHA-256 en ambas copias. La referencia
de vidrio MR también tiene un SHA-256 fijo. No hay opción CLI para eludirlos.

Los **26 archivos de datos** son:

- `source.map`, `source.tex`, `map-view.json`, `map.srm`, `glass-reference.json`,
  `glass.rgba`, `render-profile.json` y `heather-source-manifest.json`.
- `heather.sri` y `texture-00.rgba` a `texture-12.rgba`, sin modificar los
  bytes del paquete SRI2 original. Conservan huesos, helpers, canales y clips.
- Los cuatro archivos del [paquete de contactos](heather-room-contacts-package-v1.md):
  `source.cld`, `room-profile.json`, `polygons.json`, `contacts.json`.

`map-view.json` retiene cabeceras, enlaces, modelo por columnas, atributos
empaquetados, UV y triángulos. Los recursos crudos preservan los campos no
interpretados. Modos 1/2 siguen siendo procedencia, no índices de matrices.
Se conservan techo y fondos; las 29 formas pendientes no reciben el vidrio.

Creación exclusiva fuera del repositorio, directorios 0700 y archivos 0600.
El manifiesto se publica tras releer/reconstruir datos y revalidar fuentes.
`read_bundle` comprueba inventario, hashes, reconstrucción, presupuesto,
archivos regulares, identidad del directorio y custodia al terminar.
Se admite el enlace `.manifest.pending.json` solo si coincide con el
manifiesto final. La pareja se acepta después de releer A y B completas.
La atomicidad es por copia: un fallo en B puede dejar A completa; no se
devuelve éxito de pareja. No se promete una transacción de dos directorios
ni durabilidad ante pérdida de energía.

## SRM1: geometría estática para el lector C++

Little endian, cabecera de 32 bytes seguida de descriptores y vértices.

| Offset | Tipo | Contenido |
| --- | --- | --- |
| 0 | 8 bytes | `S3RMv1\0\0` |
| 8 | u32 | Número de formas, 1–31 |
| 12 | u32 | Vértices expandidos, múltiplo de 3, hasta 27900 |
| 16 | u32 | Bytes de payload: `formas*16 + vértices*36` |
| 20 | u32 | CRC32 del payload |
| 24 | u32 | CRC32 de `glass.rgba` normalizado |
| 28 | u32 | Versión 1 |

Descriptor de 16 bytes: cuatro u32 `(offset_fuente, primero, cantidad, vidrio)`.
Offsets únicos no nulos; rangos consecutivos, no vacíos, sin huecos ni solapes;
cantidades múltiplos de tres; vidrio 0/1 y suma de vidrio ≤96 vértices.
El paquete privado concreto exige 31 formas y exactamente dos paneles.

Vértice de 36 bytes: nueve binary32 `(x,y,z,w,r,g,b,u,v)`. Las posiciones son
**locales originales del MAP**, XYZ finitos dentro de ±32768 y W=1. Los RGB
están en [0,1]; UV finitos en ±8. La expansión mantiene paridad y bits de
salto del strip; no elimina triángulos degenerados. Son 27900 vértices para
9300 triángulos provenientes de 15882 vértices fuente.

El [lector acotado](../engine/platform/common/room_scene.cpp) verifica tamaño,
CRC, rangos, valores, EOF y cierre. Solo carga y valida en temporales; cualquier
fallo conserva la salida anterior. CRC detecta corrupción, no autentica
procedencia: la identidad SHA-256 se exige en la preparación privada.
El consumidor gráfico deberá comparar el CRC del vidrio antes de subirlo.

## Transformación única y fotograma

O=(100000,0,140000), B=diag(1,-1,-1), escala binary32 `0.002F`.
Matrices por columnas. `room_position` evalúa `(traslación-O)*W` antes de
sumar la base lineal, con acumulación double y salida binary32; conserva W.
Así no introduce cancelación por sumar primero el origen grande.

- MAP: aplicar T(O) una vez al cargar SRM1; el resultado queda en base común.
- Heather: skin de posiciones /16 y pesos Q12 originales, pose HL local,
  seguida una vez por T(P)·Ry(yaw) y la misma base/origen/escala.
- No usar el centrado, escala individual ni giro Z del visor SRI aislado.
  No dividir por W durante skin o colocación; solo la cámara/proyección y
  la clave de profundidad necesitan su interpretación proyectiva.

[`room_frame`](../engine/domain/room_scene.cpp) recibe mapa/modelo validados,
pose y matriz rígida de instancia. Workspace y salida son distintos y
propiedad del llamador; no se reservan en la pila del paso. Valida antes
de escribir conteos, rangos o vértices publicados. No asigna heap por frame.
El scratch puede cambiar al fallar; la salida anterior permanece íntegra.

Rangos opacos: todas las formas neutras en orden de fuente, después los
materiales opacos de Heather. Vidrio y cabello forman **una sola lista de
triángulos**, ordenada de lejos a cerca por profundidad media del centroide
respecto a la cámara fija. Clave equivalente: suma `dot(q.xyz/q.w,target-eye)`;
el factor 1/3 y la resta constante del ojo no alteran el orden. Empates:
slot de material, luego índice fuente. Solo se agrupan vecinos con igual
pass y textura. El slot de vidrio sigue a los materiales de Heather.
Es un orden de diagnóstico por centroide, no OIT ni una solución general
de intersecciones transparentes.

## Estados y texturas

[`bind_room_material`](../engine/platform/3ds/render/room_material_state.cpp)
restablece explícitamente texenv, mezcla, depth test/write, culling y alpha test.
La batería comprueba las 16 transiciones entre pases.

| Pase | RGB / alpha | Mezcla | Depth write | Caras |
| --- | --- | --- | --- | --- |
| Neutro | RGB (0.55,0.58,0.62), sin textura | Reemplazo | Sí | Ambas |
| Heather opaco | Textura × blanco, alpha >0 | Reemplazo | Sí | Ambas |
| Vidrio | Textura × iluminación/fog MR, alpha ×253/255 | SrcAlpha / 1−SrcAlpha | No | Back CCW |
| Cabello | Textura × blanco, alpha >100/255 | SrcAlpha / 1−SrcAlpha | No | Ambas |

Todos usan depth test GEQUAL de Citro3D. Vidrio conserva RGB de vértice MR
(`/128 *227/256`); la paleta 0 externa se expande RGBA8 y normaliza alpha con
`(a*255+64)//128`, sin invertir filas. Heather conserva RGBA fuente y el
upload existente: inversión de filas y alpha `min(255,2*a)`. Filtro lineal y
clamp a borde deben mantenerse al integrar las texturas. No se cargan las
variantes de paletas internas pendientes. El neutro plano no muestra sus
detalles originales ni pretende reconstruir su iluminación.

## Cámara y límites

[`heather-room-render-v1.json`](heather-room-render-v1.json) fija el refinamiento:
ojo local (275,-1000,-700), objetivo (275,-300,100), FOV vertical 80°, viewport
400×240, near/far 0.02/12. El ojo permanece dentro de la habitación. El perfil
HR original, con objetivo Y=-550 y FOV70, conserva su hash; el paquete añade
el perfil de render y la evidencia del fallo de encuadre inicial.

Presupuesto contado con las capacidades máximas de los buffers, incluidos
CPU y VBO: **40190596 bytes (38.33 MiB)**. Texturas: 18350080; staging de
texturas: 2097152; mapa: 2009308; frame dinámico: 1400184; modelo/scratch y
reservas de controlador/contactos: 961864; staging de lectores: 2789096;
reserva de plataforma: 12582912. El límite es 64 MiB; texturas ≤32 MiB,
staging individual ≤2 MiB y geometría estática ≤2 MiB.

Los tamaños de estructuras se cotejaron con compilación ARM. La reserva de
12 MiB cubre comandos, shaders, targets, buffers de pantalla, código/BSS y
margen del SDK/heap. **Es un presupuesto de ingeniería, no un pico medido
en 3DS.** [HM-T4c.2](heather-room-runtime-v1.md) valida asignaciones/CRC,
conecta el draw plan a GPU y gestiona publicación, limpieza y ciclo de vida;
añade 2 MiB para el reemplazo de datos (total 40.33 MiB). HM-T4d/5 siguen
requiriendo empaquetado y medida física.

[Evidencia y reproducción](../docs/execution/f06-01-heather-room-scene.md).
