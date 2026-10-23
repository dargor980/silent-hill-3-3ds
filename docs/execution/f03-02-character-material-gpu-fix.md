# CT-T5f — Salida completa del shader PICA

El build `3fde5682ed11` **falló en New 2DS XL**: el usuario no vio el caballo,
la consola dejó de responder y tuvo que apagarla. Se preparó el reemplazo
**`ced27c955e41`**, cuya repetición funcional **CT-T5e.1 está aprobada**:
el usuario confirma 60 segundos con texturas, avance Q12, controles, START,
tapa/HOME y sin bloqueo el 2026-10-22. Tiempos CT-T5e.2 pendientes.

## Evidencia y diagnóstico

La foto confirma build, Q12=0 y Sample=0, Skin CPU=16,53 ms,
Submit+wait=16,98 ms y GPU previous=0,00 ms. No muestra un mensaje de carga
fallida. La copia a SD de v1 había pasado lectura posterior y SHA-256.
La imagen se conserva solo en el directorio privado
`f03-02-character-material-native-check-v2/physical-failure-v1.jpg`, SHA-256
`1e3f85c05d70d2c1dd263c86d107c606d9ec357e87439ba593ac9f9d31e8e9a7`.

El SHBIN de v1 declara tres registros de salida con máscara `0xF`:
posición o0, color o1 y UV o2. Las instrucciones escriben todos los componentes
de o0/o1, pero la única escritura a o2 usa máscara de instrucción `0xC`
(XY); Z/W quedan sin escribir. El shader de escena anterior escribe el
registro UV completo. El nuevo shader cambia exclusivamente esa instrucción
a `mov out_texcoord, v2`; la máscara emitida pasa a `0xF`.

Esta diferencia es la **causa probable**, respaldada ahora por la repetición
física satisfactoria con el mismo payload de recursos.
La regla documentada de PICA exige escribir una vez los componentes de salida
configurados; el ejemplo oficial escribe el registro UV entero aunque solo
XY tenga significado de textura. El gate adopta ese contrato conservador.
El contador inicial y GPU=0 son compatibles con una cola GPU que no termina:
Citro3D devuelve desde FrameEnd después de encolarla y la siguiente llamada
FrameBegin espera su finalización. No disponemos de una traza de la GPU física
que demuestre el punto exacto de bloqueo.

Fuentes consultadas:

- [Picasso: máscaras de salida y texcoord0](https://github.com/devkitPro/picasso/blob/master/Manual.md#out).
- [Ejemplo oficial textured_cube](https://github.com/devkitPro/3ds-examples/blob/master/graphics/gpu/textured_cube/source/vshader.v.pica).
- [3dbrew: componentes de salida y bloqueos](https://www.3dbrew.org/wiki/GPU/Pitfalls).
- [ISA y máscaras, documentación de 3dbrew alojada por Mikage](https://docs.mikage.app/GPU/Shader_Instruction_Set/).
- [libctru: lectura DVLE y mapa de salida](https://github.com/devkitPro/libctru/blob/master/libctru/source/gpu/shbin.c).
- [Citro3D: cola, FrameBegin y FrameEnd](https://github.com/devkitPro/citro3d/blob/master/source/renderqueue.c).

## Corrección y prevención

No cambia el payload de malla, animación o texturas, los tres grupos de dibujo,
la transformación ni los estados del material. El verificador Python
`tools/qa/pica_shader_outputs.py` lee el **SHBIN compilado**, no busca una
cadena en el código fuente. Comprueba tablas y límites, salidas declaradas y
cuenta escrituras por componente. Admite únicamente el perfil rectilíneo
MOV/DP4/NOP/END con posición/color/UV completos. Instrucciones desconocidas,
control de flujo y layouts ajenos se rechazan: no es un verificador general.

CMake lo ejecuta antes de incluir los shaders de personaje y escena en los
ejecutables. La comprobación se vuelve a ejecutar en builds incrementales.
El job ARM existente de CI hereda este gate; no se ejecutó CI remoto.
No se añade una salida forzada ni se liberan buffers con comandos GPU en vuelo.

## Verificación local

| Comprobación | Resultado |
|---|---|
| Python, verificador + paquete + contratos | 109 casos aprobados; 35 del verificador |
| Cobertura del verificador | 98,86 % líneas, 97,92 % ramas; solo entrypoint CLI sin cubrir por coverage |
| C++ render Release / ASan+UBSan | 137 casos aprobados por configuración |
| SHBIN fallido v1 | Rechazado: `o2.z: expected one write, found 0` |
| SHBIN corregido y shader de escena | 12 componentes escritos exactamente una vez |
| Gate CMake con SHBIN v1 inyectado | Build detenido, exit=2; el ejecutable no se vuelve a enlazar |
| Gate CMake tras restaurar SHBIN corregido | Build aprobado, exit=0; 3dsx idéntico al paquete |
| ARM | Compilan personaje con material, personaje anterior y visor de vidrio |
| Paquete privado | Preparación A/B idéntica; SCM/SAN/SCT iguales a v1 |
| Azahar 2126.2 Vulkan | Malla con texturas, A/L/R, cámara/zoom/reset, reproducción y START comprobados |
| New 2DS XL | Usuario confirma texturas, Q12, controles, START, tapa/HOME y 60 s sin bloqueo; tiempos nuevos pendientes |

La prueba negativa se hizo en la copia de código para build y restauró el
SHBIN corregido. Logs y JSON de la regresión están en
`build/character-material-inspection/shader-gate-*`. El código host no ejecuta
PICA; por eso sus pruebas anteriores no detectaban esta omisión.

En Azahar, L en pausa llevó Q12 a 0 y R a 3686. Cámara y zoom cambiaron
con la pose pausada; B restauró 0,35 / 0,35 / 4,00. Tras reanudar hubo
92,231 segundos entre observaciones, con Q12 pasando de 40546 a 58112
(contador cíclico) y dibujo visible. No fue una captura continua de vídeo.
START volvió a la lista de aplicaciones. Tapa/HOME y rendimiento físico
requieren la consola. Capturas y recibo en el directorio privado de evidencia
v2; resumen en `reports/local/f03-02-character-material-gpu-fix-v2.json`.

SHA-256 SHBIN v1: `72d2e9ddb7c54bbb8ca154ab0928f6126f71e5ca8f7b9d0aa193a356653c5f78`.
SHA-256 SHBIN corregido: `9fac3d2deac79aaaff6468870b17bb3999d94b32a55b23c55edfbaf6ff8dce9c`.

## Entrega

Paquete: `/Users/germancontreras/sh3-private-data/f03-02-3ds-character-material-v2/sd-card.zip`.
Build **`ced27c955e41`**. ZIP de 3.487.279 bytes, SHA-256
`8d047e312d8598c492aec0cd938e6bc1c8aa820cf43f8290761930a8c75ae0d0`.
3dsx SHA-256 `05348599020fe31ff20f3d2ee9cac702fab33433291488b0f31124fa80f499dd`.
Manifiesto SHA-256 `26c865aacb083a4e5ecbc0f7d6db3419cc50168a2cdb79cf0dad6bcff0d87581`.

Conserva `/3ds/sh3_character_material_probe/` y el título
**SH3 textured character**. Reemplaza los seis archivos de ese visor,
conservando las aplicaciones anteriores. La SD NO NAME no estaba montada
al preparar v2. Posteriormente, el usuario la conectó y solicitó copiar
`ced27c955e41`: se reemplazaron los seis archivos (3.485.367 bytes), con
tamaños y SHA-256 verificados mediante lectura posterior. Los 30 archivos
de los otros visores conservaron sus hashes y la SD se expulsó correctamente.
Comprobante privado `f03-02-character-material-native-check-v2/sd-copy.json`,
SHA-256 `0178c975aee28140307143f97145486b13a773430a51aa388600b30bf031c3a1`.
La validación funcional del reemplazo está confirmada por el usuario.
El [protocolo físico](../compatibility/character-material-inspection.md)
exige primero que aparezca la malla y avance Q12, luego controles, ≥60 s,
START, tapa y HOME. La iluminación PS2 y daño/muerte siguen pendientes.
