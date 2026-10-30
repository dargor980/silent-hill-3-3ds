# Preparación privada de contactos hp34 v1

2026-10-29. Formato de HM-T4b.3 para el perfil fijo
[heather-hp34-inspection-v1](heather-room-profile-v1.json), conforme a
[HR01/05/11](heather-room-profile-v1.md) y [HRC v1](heather-room-contacts-v1.md).
Implementación: [conversor](../tools/pipeline/heather_room_contacts.py) y
[custodia/publicación](../tools/pipeline/prepare_heather_room_contacts.py).

## Identidad y conversión

La entrada autoritativa es el JSON de habitación de 3585 bytes, SHA-256
`5838c4b445a0da3f4a2636ac9c9e61edfe754dc89b33d25db33284581212e531`.
Se fijan además catálogo, recibo de extracción y los tres recursos seleccionados:
mapa, CLD y textura externa. Las seis fuentes A/B deben ser archivos regulares,
sin enlaces simbólicos, de tamaño/hash exactos y con igualdad byte a byte.
Los inventarios completos de catálogo/recibo/copias deben coincidir; los
recursos seleccionados deben conservar contenedor, offset y nombre derivados.
Todo esto se verifica antes de decodificar el CLD.

El conversor exige origen/selección del perfil, grupos `[1,4,26,3,0]`, variante
1 con cuatro puntos, referencias de celda 0 completas en orden y demás celdas
vacías. XYZ deben ser finitos y estar dentro de ±1000000. El registro `(0,0)`
es un rectángulo horizontal Y=0; su erosión exacta por 176 deja área positiva.
El registro `(2,4)` es techo Y=-1600 y queda excluido solo de las consultas
planas. Los otros 32 registros generan cajas independientemente de sus flags.

Cada caja conserva `[xmin,xmax,zmin,zmax]` como palabras originales
`f32:XXXXXXXX`. En empates numéricos se usa la primera palabra de origen,
incluido el signo de cero. No se expande ni redondea la caja durante la
conversión: el núcleo aplica la expansión exacta HRC. Las coordenadas ya son
de mundo; no se vuelve a sumar el origen.

## Inventario por copia

| Archivo | Contenido | Límite de lectura |
|---|---|---:|
| `source.cld` | Recurso original íntegro, incluidos campos opacos | 65536 bytes |
| `room-profile.json` | Perfil fijado, sin reserializar | 16384 bytes |
| `polygons.json` | Vista CP completa, palabras XYZW, listas y offsets | 131072 bytes |
| `contacts.json` | Escena HRC, roles de los 34 registros y procedencia | 32768 bytes |
| `manifest.json` | Inventario con tamaños/hashes y alcance de la preparación | 16384 bytes |

`contacts.json` lleva `schema_version: 1`, `profile: heather-hp34-contacts-v1`,
`scene`, `record_roles`, `source` y `anchors`. Cada rol contiene grupo, índice,
offset y `floor`, `ceiling_excluded` o `blocker`. `scene` conserva origen,
floor_y, half_extent=175, guard=1, suelo y bloqueadores. Los anchors enlazan
el perfil, catálogo y recibo por SHA-256. El verificador reconstruye los cuatro
archivos desde CLD/perfil y exige igualdad completa de bytes; no acepta
geometría editada aunque se recalculen los hashes del manifiesto.

## Publicación y consumo

La salida está fuera del repositorio, en carpetas nuevas exclusivas 0700 y
archivos 0600. No hay sobrescritura. Se escriben y releen los cuatro archivos,
se verifica `.manifest.pending.json`, se revalidan las fuentes y se publica
`manifest.json` al final mediante un enlace duro. El lector final acepta el
pendiente conservado solo si coincide con el manifiesto final; rechaza extras,
ausencias, archivos no regulares, cambios de identidad y reconstrucciones
discordantes. También verifica que la carpeta abierta siga en su ruta.

Cada copia tiene publicación individual. La pareja se acepta solo tras
finalizar y releer ambas y revalidar todas las fuentes. Un fallo en B puede
dejar A completa; la operación devuelve error y no anuncia éxito A/B. No se
promete una transacción conjunta de dos directorios ni durabilidad ante pérdida
de alimentación. No se considera aceptado un directorio sin manifiesto final.

El preparador Python es offline y sus buffers no forman parte del presupuesto
de 4096 bytes del núcleo C++. Estos JSON son datos de preparación: su carga y
conexión al bucle gráfico se realizarán en HM-T4c. El manifiesto declara
`runtime_integration: false`, `new_vm_execution: false` y composición nativa,
sin atribuir registro PS2 ni equivalencia con la física original.

Las pruebas CI usan únicamente CLD y posiciones inventados. El cotejo privado
se ejecuta explícitamente con [el auditor local](../tests/heather_room_private_audit.py),
que conserva en memoria las cajas y solo emite hashes, conteos y resultados.
[Evidencia HM-T4b.3](../docs/execution/f06-01-heather-room-preparation.md).
