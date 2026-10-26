# HI: Heather original texturada y animada

Fecha: 2026-10-24. [Spec EARS](../specs/sh3-3ds/heather-inspection.md).
**Resultado:** el build `9719469ff6bb` presenta el modelo original de Heather,
con texturas y animación, en Azahar. La entrega privada está preparada para
Homebrew Launcher. La prueba en New Nintendo 2DS XL sigue pendiente.

No incluye desplazamiento jugable, habitación, expresiones faciales ni la
iluminación PS2. F03.02 global y los gates del juego permanecen abiertos.

**Revisión posterior HI-T6:** el primer plano detectó inversión vertical de
texturas en PICA que esta inspección lejana no había identificado. La entrega
`f25a2d9bb316`, documentada en [cámara cercana](f03-02-heather-camera.md),
reemplaza este build y corrige el upload. Los contrastes de fuentes, pose,
GS y RGBA originales conservan su alcance; la aceptación visual inicial
no debe interpretarse como verificación de orientación de textura.

## Identificación y custodia

Se respeta la elección explícita del usuario: atuendo original. El ID
`0x100` no distingue trajes. El estado del carrusel que contenía `chhcc.mdl`
se excluyó de la acreditación del modelo original.

| Entrada | Selección |
|---|---|
| ISO europea | SLES-51434, CRC 5088CCDB; 3.586.785.280 bytes |
| SHA ISO | `9a94b95e777dae426043e40df1b70d77c8f6960dbd79af10df1cd592cf99ad91` |
| Contenedor | XBG0.MFA; 544.569.344 bytes |
| SHA MFA | `6b6dcef3243e62ce36c59bf3ae01a1acf88027d0b3e7b1fee980f95c8798a25d` |
| Modelo | Ordinal 522, `data/chr/pl/chhaa.mdl`; 1.639.344 bytes |
| SHA MDL | `1aa81b56c0a079c8d98e57f17537e91b2ce20f1e46a1cc6d9816561cad03d2e9` |
| Animación elegida | Ordinal 526, `data/chr/pl/chhaa_basic1_none.anm`; 465.436 bytes |
| SHA ANM | `26c8239df5ccb251c3ec316845e6addbfdf01df2668979fb3c62037d1eb2b518` |

El MDL coincide byte a byte con los ordinales 322 (`item/chhaa.mdl`) y
576 (`pl/pl_htr_a.mdl`). La selección dedicada queda en
`reports/local/heather-selection-v1.json`, SHA
`0633ba0db92878729f0721c09650afa2bfd3bcccc82f1236db72057603649869`.
No debe confundirse con la selección histórica del caballo usada inicialmente
para localizar ISO/contenedor en el manifiesto de adquisición.

Los recursos y capturas permanecen en `/Users/germancontreras/sh3-private-data/`;
los helpers de adquisición/auditoría están en `build/heather/` y los recibos en
`reports/local/`, ignorados por Git. Los fixtures del repositorio son sintéticos.

## Decodificación y contraste PS2

El [contrato PS2](../../schemas/ps2-heather-v1.md) separa morphs, malla,
animaciones e índices/paletas. La conversión completa conserva 73 huesos,
91 helpers, 233 submallas, 21.172 vértices, 16.770 triángulos, 1.784 vértices
base morph y 25 objetivos. Los once ANM de ordinales 523–533 decodifican
1.763 muestras de 264 bytes, con 36 pistas, y reconstruyen exactamente sus
bytes. No se infieren clips nuevos a partir de ese conteo.

La captura de Heather original es una **reproducción diagnóstica**: una
restauración inicial y ninguna entre las cuatro poses; sin escrituras al
guest. Actor `0x4481D0`, MDL `0x606000`, ANM `0x798000`, máscara `0x3021`.
Los 25 pesos morph observados son cero. La selección activa contiene 79
submallas sin referencias morph, 36 huesos y 49 helpers; las otras capas
quedan conservadas en la conversión completa.

El descriptor `(101,10,307,0,9,1)` identifica clip `0x65`, muestras 0–9.
Los contadores posteriores son 614, 1228, 1842 y 2456; cada pose corresponde
al contador **anterior**. Error máximo frente a RAM: pose 0,000819056,
helpers 0,000123326; la etapa de paleta contrastada con truncamiento f32
coincide exactamente. Usar el contador posterior produce error ≈0,706,
conservado como control negativo. No se observó el wrap ni el reloj completo.

El dump GS tiene 19.862.183 bytes, SHA
`cfc51ec284b132e3d49c51cebb6d2b4e621e9d1da83112003f30a9bf9be7cc28`.
En frame 1 se asocian las 72 submallas opacas a 1.932 paquetes únicos y
las siete del cabello a 240 triángulos, sin grupos sin asociar. El cotejo
STQ acredita UV/profundidad; no es una comparación independiente de XY/raster.
El opaco prueba alfa >0 y no mezcla; el cabello prueba >50 PS2 y usa
`(Cs-Cd)*As+Cd`; profundidad GEQUAL con escritura, lineal y clamp.

Dos reproducciones software separadas del mismo dump contrastan las 13
texturas activas: índices y colores CLUT direccionables exactos. La imagen
PSMT4 usa 16 colores; se excluyen explícitamente los 240 valores residuales
no direccionables de su volcado de 256 entradas. El oráculo de direcciones
comprueba 16 tamaños y 28 paletas con tablas GS fijadas. Se corrigió la
selección CSM1: una carga de cuatro unidades permite 0,1,4,5.

PCSX2 y ambas reproducciones cerraron con código cero; el baseline de
configuración permaneció intacto. Ejecutable de captura SHA
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
No se modifican los resultados independientes de CF-T9c.

## Conversión e integración nativa

Dos conversiones desde la ISO producen manifiestos y archivos idénticos:

| Salida privada A/B | Resultado |
|---|---:|
| `heather-animation-{a,b}-v1` | 4 archivos, 28.381.506 bytes por carpeta |
| `heather-material-{a,b}-v1` | 66 archivos, 30.249.388 bytes por carpeta |
| `heather-inspection-{a,b}-v1` | 14 payloads, 18.329.472 bytes por carpeta |

Los inventarios de conversión incluyen el manifiesto y su enlace pendiente
del escritor existente; la tercera fila cuenta solo SRI/texturas.
`heather.sri` SHA
`19fb44df9fb47966a9cdfbfd42b331bd1461313ea61493257f4e5b42e29ef49d`.

El [formato SRI1](../../schemas/rig-inspection-v1.md) transporta traslaciones
y quaternions locales, helpers, pesos, vértices, índices y materiales.
La pose y la deformación se calculan en la consola. El dominio es puro;
`RigProbe` controla reproducción/ciclo de vida; `IRigScene` e `IRigTextures`
separan presentación y lectura; el adaptador Citro3D administra recursos GPU.
Se reutilizan cámara y lifecycle existentes sin acoplar el dominio al SDK.

La inspección dibuja 6.943 vértices y 5.522 triángulos con 13 texturas, luz
neutra y transparencia del cabello ordenada para su cámara. Conserva pesos
Q12 deficientes y componente W. El VBO ocupa 596.376 bytes; las texturas
17,25 MiB, cargadas con staging máximo observado de 2 MiB. No hay heap por
frame. La ordenación usa almacenamiento del presentador, no la pila.

El lector verifica límites, longitudes, reservados, CRC y cierre antes de
publicar datos. Los controles de APT conservan suspensión, regreso con
liberación de botones y START. Los errores muestran una salida recuperable.
El renderizador conserva el shader completo y la secuencia de propiedad
del VBO que corrigió el bloqueo del visor anterior.

Una comprobación nativa independiente compara 36 matrices y 6.943 vértices
en siete contadores: error máximo de pose 0,000131130 y posición 0,000197324,
bajo límite 0,001. Otros 80 puntos del bucle pasan encuadre/finitud. Esto
compara cálculo f32 con un oráculo en doble; no mide error total EE/VU/PICA.

## Batería y compilación

| Comprobación | Resultado |
|---|---|
| Python completo | 8.987 tests +56 subtests, aprobados; `full-tests-v2.log/xml` |
| Cobertura Python de ese corte | 97,76 % líneas; 95,64 % ramas; gates global e individuales aprobados |
| C++ Release completo | 351 tests aprobados |
| C++ ASan/UBSan completo | 351 tests aprobados |
| C++ tras encuadre y últimas pruebas del lector | 24 tests de rig/render aprobados en ambos presets |
| Python tras integración final del ZIP | 204 tests relacionados aprobados, incluido el nuevo caso de archivo exacto |
| Conversión A/B, GS, software y oráculo nativo | Aprobados dentro de los alcances descritos |
| ARM | Build final `9719469ff6bb`, hashes y contrato de shader comprobados |

Los gates permanentes de CI incluyen siete módulos de Heather por separado
y un job ARM que conserva únicamente `.elf/.3dsx/.smdh`, IDs y hashes.
No se afirma una ejecución remota de CI. El primer build ARM detectó una
diferencia de tipos `size_t/uint32_t` en el staging, corregida con conversión
explícita; los logs de fallo se conservan. Las pruebas del pipeline se
adaptaron para identificar su gate de colisión por módulo, sin asumir que
existirían siempre solo dos gates individuales.

El lint/formato del alcance de CI pasa, igual que arquitectura, custodia,
enlaces/specs y `git diff --check`. Una pasada ampliada a todo `tests/`
detectó 37 avisos y siete archivos sin formato en fixtures históricos fuera
del alcance de lint de CI; no se modificaron esos fixtures en esta entrega.

SDK fijado:
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
Script: `scripts/build_heather_probe.sh`; salida `build/heather-probe-v3`.
SHA `.3dsx`:
`259956ab20ba7f0d800f9c9864a741ea680ee5df8129635de32d714c1bbff44b`.

## Azahar y entrega física pendiente

Azahar 2126.2 macOS ARM64/Vulkan ejecutó el build final con el modelo
original visible de frente, texturado y animado. Intervalo continuo observado:
**64,161 s**, Q12 11052 → 14096 y muestras 2 → 3, con repetición del segmento.
Las imágenes de extremos y las acciones de UI constituyen una prueba visual,
no una traza por frame ni una medida de rendimiento físico.

A pausa/reanuda; L devuelve el contador a cero; R avanza a 614 en pausa;
cruceta, X/Y y B cambian/restablecen cámara; START vuelve a la lista de
aplicaciones. Azahar cerró con código cero. Tapa/HOME quedan para hardware.
El selector de archivos de una ejecución preliminar dejó de responder a
la automatización después de salir del visor; se cerró esa instancia y
el ensayo final se lanzó por CLI, sin atribuir el fallo al visor.

Entrega: `/Users/germancontreras/sh3-private-data/heather-3ds-v1/sd-card.zip`.
18.952.944 bytes; SHA
`2b3b9e4014701bcc1d12dbb9730bc5ba5113fb689315369ce93be116edc48b94`.
Los ZIP producidos desde A/B son idénticos; se releen y verifican entradas,
sumas y manifiesto tras publicación exclusiva. Contiene la carpeta
`3ds/sh3_heather_probe/` y guía de uso. No se ha copiado a una SD física.

Protocolo original **HI-T5b**: [protocolo en New 2DS XL](../compatibility/heather-inspection.md),
60 segundos, atuendo/texturas/animación, controles, START/tapa/HOME y tiempos.
Después: verificar el reloj nativo y seleccionar animaciones de locomoción
antes de integrar a Heather en una habitación con movimiento y colisión.

## Índice de evidencia local

En `reports/local/`: `heather-selection-v1.json`,
`heather-animation-ab-v1.json`, `heather-material-ab-v1.json`,
`heather-pose-v1.json`, `heather-gs-draw-v1.json`,
`heather-sw-textures-v2.json`, `heather-indexed-oracle-v1.json`,
`heather-inspection-ab-v1.json`, `heather-native-v2.json`,
`heather-emulator-v1.json` y `heather-delivery-v1.json`.
`heather-final-evidence-v1.json` fija hashes de esos once informes, siete
logs y las fuentes que vuelven a producir el identificador del build final.
En `build/heather/`: helpers reproducibles, logs y capturas `azahar-*.png`.
El dump, estados y recibos de captura están en `heather-runtime-v1` privado.

**Actualización 2026-10-24:** el usuario confirma la prueba funcional de la
entrega corregida `f25a2d9bb316`; véase el [registro físico](../compatibility/heather-inspection.md).
La baja fluidez reportada abre [HP](../specs/sh3-3ds/heather-performance.md)
antes del reloj nativo y la locomoción. Las menciones de prueba pendiente
anteriores describen la entrega inicial, reemplazada por ese build.
