# SRI1: rig de inspección animada

Contrato de HI05. Formato privado acotado de inspección; no sustituye al
intermedio general ni al contenedor SH3P. El productor puro es
`tools/pipeline/rig_inspection.py`, el lector es
`engine/platform/common/inspection_rig.cpp` y el dominio no depende del SDK.
El origen se rige por [el perfil de Heather](ps2-heather-v1.md).

## Cabecera y payload

Little endian, enteros de ancho fijo y float32 IEEE754. No hay padding
implícito. Cabecera de 64 bytes, `<8s14I>`:

| Offset | Campo | Restricción |
|---:|---|---|
| 0 | Magic, 8 bytes | `S3RIv1\0\0` |
| 8 | Huesos `B` | 1–73 |
| 12 | Muestras `F` | 2–64 |
| 16 | Helpers `H` | 0–128 |
| 20 | Vértices `V` | 3–8.192 |
| 24 | Índices `I` | 3–18.000, múltiplo de 3 |
| 28 | Materiales `M` | 1–16 |
| 32 | Clip | 1–65.535 |
| 36 | Incremento Q12 | 1–65.535, menor que `F*4096` |
| 40 | Bytes del payload | `16+4B+28BF+68H+28V+2I+28M` |
| 44 | CRC32 IEEE del payload | Misma función que los otros visores |
| 48–63 | Reservados | Cuatro uint32 cero |

Orden del payload:

1. Centro XYZ y escala: cuatro float32. Centro finito, magnitud de cada
   componente ≤100.000; escala `(0,1]`.
2. Padres: `B` int32. `-1` indica raíz; otro valor debe ser menor que el
   índice del hueso. El orden es topológico y admite varias raíces.
3. Muestras, primero frame y luego hueso: `B*F` registros de siete float32,
   traslación XYZ y quaternion XYZW local. Traslación acotada a ±100.000;
   quaternion finito, componentes ≤1,001 y norma al cuadrado a ≤0,001 de uno.
4. Helpers: uint32 del hueso destino y matriz column-major de 16 float32.
   Matriz afín, última fila `(0,0,0,1)`, valores finitos de magnitud ≤100.000.
5. Vértices: `<8h3H4BH>`, 28 bytes. Posición XYZ, normal XYZ y UV int16;
   tres pesos uint16 Q12; hueso primario, cuenta y dos helpers uint8;
   uint16 reservado cero. Cuenta 1–3; suma de pesos entre `4097-cuenta`
   y 4096. Pesos ausentes cero y helpers ausentes 255. No se renormalizan.
6. Índices: `I` uint16, todos menores que `V`.
7. Materiales: `<7I>`, primer índice, cantidad, textura, ancho, alto, blend,
   CRC32 del RGBA. Rangos consecutivos y completos, cantidades múltiplo de
   tres; textura igual al ordinal del material; blend 0/1 y todos los opacos
   antes de los transparentes. Dimensiones 128/256/512/1024, suma ≤8 Mpíxeles.

El lector comprueba longitudes, CRC, valores y cierre antes de publicar el
modelo. Rechaza bytes sobrantes. Las texturas `texture-NN.rgba` tienen
exactamente `ancho*alto*4` bytes en RGBA PS2, filas originales y CRC por
material; un error impide su uso. La carga PICA transforma una sola vez el
alfa a `min(255,2*a)`, invierte las filas para el origen V de PICA, ordena
ABGR en teselas Morton de 8×8 y vacía caché. Esta adaptación final no altera
el RGBA original, su CRC ni las UV PS2. Se corrigió al inspeccionar la cara
en HI-T6; el build inicial no había acreditado la orientación visual.

## Evaluación y presentación

El contador selecciona `frame=floor(Q12/4096)` y su fracción. La traslación
interpola linealmente y la rotación con NLERP por el arco corto. Pose modelo
`parent*local`; helper de deformación `pose[target]*helper`. Se conserva la
componente homogénea de los pesos deficientes. Normales y UV permanecen en
el paquete; esta entrega dibuja color blanco con luz neutra.

La base de inspección rota π sobre Z: `(-x,-y,+z)`, centra y escala conservando
W; no redefine las coordenadas del recurso original. El orden transparente
se calcula por profundidad media de cada triángulo en la cámara de inspección,
de lejos a cerca, con ordinal como desempate. Se ordena cada rango por
separado; Heather usa un solo rango transparente. Esto no reproduce el
orden/culling/fog exacto del GS.

El renderizador usa el shader previamente corregido, escritura de VBO solo
después de adquirir el frame, flush posterior y espera antes de liberar
memoria referenciada. La escena recibe pose y cámara mediante `IRigScene`;
las texturas entran mediante `IRigTextures`. No hay asignaciones por frame.
Los fallos de lectura o inicialización vuelven a una pantalla con START.

## Perfil Heather original de esta entrega

Máscara `0x3021`, 79 submallas sin morph activo; compacta 36 huesos y 49
helpers. Usa 6.943 vértices, 16.566 índices, 13 texturas y clip `0x65`,
muestras 0–9. La traslación local de hijos se deriva de la pose de reposo
rígida contrastada con PCSX2; las dos raíces usan sus pistas ANM. La
conversión completa conserva las otras submallas, huesos y objetivos morph.

`heather.sri` ocupa 241.536 bytes; sus 13 texturas ocupan 18.087.936 bytes
(17,25 MiB). El VBO expandido ocupa 596.376 bytes. Staging máximo observado
de textura: 2 MiB; límite admitido por el formato: 4 MiB por textura.
El buffer de ordenación es propiedad del presentador, fuera de la pila.

Reloj del visor: 25 evaluaciones/s e incremento 614, con pausa A, avance R
y reinicio L. El cierre del segmento es una política de inspección;
el wrap y la frecuencia completos del juego permanecen pendientes. El
retorno desde suspensión exige soltar controles y descarta el tiempo dormido.

## Archivo para SD

`inspection_archive(..., "sh3_heather_probe")` acepta exactamente SRI,
13 texturas numeradas 00–12, `.3dsx`, `.smdh` y `LEEME.txt`: 17 archivos.
Los ubica en `3ds/sh3_heather_probe/` y añade `SHA256SUMS` en la raíz del ZIP.
Orden y fechas son fijos; entradas adicionales o ausentes se rechazan.
El paquete se publica exclusivamente fuera del repositorio, sin sobreescribir
sesiones. CI compila y publica solamente código, nunca estos recursos privados.
