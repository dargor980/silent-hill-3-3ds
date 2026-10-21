# F03.02 — Contadores de dibujo y transformación base del MAP

2026-10-20. Completadas **MR-T1–MR-T3** del
[contrato EARS MR01–MR07](../../schemas/ps2-map-render-metadata-v1.md).
El ejecutable europeo aporta dos correcciones para la conversión: las rutas
se delimitan por contador y la palabra de forma +20 no es un índice de matriz.
El nuevo sondeo conserva estas distinciones y localiza el registro base.
MR-T4, MP-T4, MG-T4 y la fidelidad de material permanecen pendientes.

## Resultado sobre las dos copias

El MAP sigue teniendo 8 grupos, 10 mallas, 31 formas y 15.882 vértices
declarados. La jerarquía anterior era un grafo estructural; sus colas compartidas
no representaban por sí solas las listas consumidas por cada ruta.

| Slot / raíz en área | Contador en área | Grupos consumidos por cuenta |
|---|---|---|
| 0 / +28 = 0 | +66 = 0 | Ninguno |
| 1 / +32 = 304 | +70 = 1 | Solo 304 |
| 2 / +36 = 1472 | +68 = 7 | 1472, 130224, 159136, 226320, 232640, 247696, 253792 |

El enlace de 304 continúa hacia 1472, pero el contador de su ruta termina en
uno. El informe conserva esa cola como `structural_tail_excluded`. No elimina
grupos del grafo ni cambia informes anteriores.

El área +24 apunta a 80. El registro tiene desplazamiento de datos 32 y tamaño
224; la matriz está en 112 y los ocho vectores de límites en 176.
Todos sus componentes son finitos. Bajo interpretación por columnas, la matriz
es afín, con base identidad y traslación no nula. No se exportan sus componentes
ni se aplica al visor.

Las formas 448/928 tienen `mode_word_20=1` y `auxiliary_word_24=112/119`.
La palabra +20 participa en una codificación de visibilidad y en selección de
transformación según la ruta. Tratar su valor 1 como «matriz número 1» sería
incorrecto. El campo histórico `transform_index_unverified` permanece en MP/MG
para compatibilidad; este informe corrige su interpretación, sin reescribir
las evidencias anteriores.

## Evidencia estática europea

Se verificó el ELF de arranque directamente desde la ISO local:
3.395.784 bytes, SHA-256
`cb6e538bed7de8317f5333f3a56d4cd125432643950988168f901d6ede09f789`.
Su tabla `.symtab` tiene tamaño cero. Las direcciones siguientes son virtuales
del ELF europeo, obtenidas de sus instrucciones, no trasladadas desde otra región.

| Dirección / recorrido | Observación acotada |
|---|---|
| `001AEA28`–`001AEA40` | Lee los halfwords +66/+68/+70 del bloque y los conserva en el contexto +16/+20/+24. |
| `001AEA80`–`001AEAB0` | Sigue bloque +24, suma el desplazamiento relativo del registro +4 y copia su matriz base. |
| `001210A8`–`001210C8` | Copia exactamente cuatro bloques de 16 bytes; se verificaron LQ/SQ y el delay slot del retorno. |
| `001AEC44`–`001AEC6C`, `001AE8B8`–`001AE8D0` | Vincula raíz +32 con contexto +8 y recorre tantos grupos como indica contexto +24, procedente de +70. |
| `001AE7A8`–`001AE7E0` | Copia el byte de malla +16 y campos vecinos a un descriptor que se conserva con las formas de esta ruta. |
| `001ADEB0`–`001ADFA0` | Codifica la pareja de palabras de forma +20/+24. El modo 1 remapea campos de bits; no indexa una matriz. |
| `001ADDE0`–`001ADEAC` | En otra ruta, los modos 0/1/2 solicitan el registro de transformación con clave 0; el modo 3 usa +24 como clave. Esto no generaliza la semántica de todos los modos. |
| `001B23B0`–`001B2464` | La ruta de las formas seleccionadas prepara el contexto base +1896 (`0x768`), inicializado por el cargador, antes de consumir su lista. Falta reconstruir la transformación VU completa. |
| `001B1328`–`001B1354`, `001B5F20`–`001B5F9C` | El byte de CLUT del descriptor entra como argumento de selección, con modo 1, al getter de datos TEX0. Para estas mallas el candidato sigue siendo 0. |
| `0027B778` → `001ABDE0`, `001ABD20`, `001B25A0` | Localiza registro, consulta y recorrido del banco externo usado por esta ruta. No demuestra aún qué payload concreto llega al callback en esa escena. |

Se guardaron 15 ventanas con direcciones, longitudes y SHA-256:
`reports/local/f03-02-map-render-static-v1.json`, 5.957 bytes, SHA-256
`d21e28fa27d8a1e105391bc27308674a34e917d22f23a012d2de6c3885a3544f`.
El desensamblado permanece exclusivamente en la raíz privada autorizada,
`f03-02-map-render-research-v1/european-windows.txt`, 14.088 bytes, SHA-256
`06ddadd717c14adf6eabc54179cc5a21135f3e57aa08c8c7f17149a84bf2a5d3`.

Herramienta de investigación: Capstone 5.0.6 aislado en `build`, con tratamiento
explícito del subconjunto LQ/SQ, LQC2/SQC2 y POR de R5900. Las extensiones no
interpretadas no se usaron como prueba. No se añadió esa dependencia al proyecto.
El auxiliar y sus hashes están en el manifiesto de fuentes de esta ejecución.
`build/f03-02-map-binding/source-manifest.json` fija 27 archivos, incluidas
dependencias locales transitivas, contrato y fixtures; SHA-256
`f9de123c34a3a8c78766bb3b8665f8c0baf3d96b198a3eb1cb0ed91a509fb3d3`.

Como pista de búsqueda se consultó
[memory-of-alessa, revisión 247c7f4](https://github.com/dreamingmoths/memory-of-alessa/tree/247c7f43fd619aff8d2086ea0b0af291c283ea9d),
que corresponde a SLUS_206.22 estadounidense y licencia MIT. Sus encabezados
de bloques no coinciden directamente con este MAP. No se adoptaron esos layouts,
se ejecutó su proyecto ni se atribuyeron sus símbolos a direcciones europeas.
Referencias y licencia quedaron fijadas por hash en el informe local.

## Implementación y pruebas

Parser puro `map_render_probe.py`: partición por contadores, registro base,
clasificación de matriz y palabras de forma. El coordinador existente añade
`--render-metadata`, mantiene integridad y cierre del lector antes de publicar.
Solo emite metadatos; la dependencia es el puerto de lectura, sin filesystem,
emulador o SDK dentro del parser. Los informes sin la opción mantienen su contenido.

**398 pruebas aprobadas**, incluidas **50 nuevas**. Se cubren partición,
colas compartidas, duplicación, cuentas inconsistentes, selección de variante,
desalineación, huecos, truncamiento, valores no finitos en matriz/límites,
lectura corta, dos copias, publicación exclusiva y fallos posteriores al lector.
Regresión MP/MG, decodificación de textura, empaquetados TI/GI, scripts de build
y contratos del repositorio aprobada.

Cobertura de los dos módulos: **112/113 líneas (99,12 %) y 27/28 ramas
(96,43 %)**. Parser nuevo: **51/51 líneas y 12/12 ramas, 100 %**.
La línea no instrumentada es el despachador `__main__` del coordinador,
ejecutado en subprocess y en ambas lecturas reales. Gate de cobertura y Ruff
aprobados. Informes: `build/f03-02-map-binding/tests-final.xml`, `coverage.json`.
El job Python de CI descubre los tests sin originales; no se atribuye una
ejecución remota de CI ni un nuevo build ARM a este cambio de herramientas host.

Ambas copias producen informes idénticos de **43.489 bytes**, SHA-256
`5ffe8811a9ed121b5496b0242e21a0b4970163e254cb4bc4e99d3ad60cddf8d3`:
`reports/local/f03-02-map-render-{a,b}-v1.json`.
Comandos y tiempos: `build/f03-02-map-binding/real-execution.json`.
Para reproducir, usar el comando de
[MP](f03-02-map-material-candidate.md#reproducción-y-continuación), añadir
`--render-metadata` y escoger un archivo de salida nuevo.

## Siguiente comprobación

El camino está acotado a raíz +32 → descriptor de malla → selección CLUT y
banco externo. La [captura controlada de material](f03-02-map-runtime-binding.md)
ya vincula el payload completo del banco, el MAP y el gestor: ambas formas
seleccionan CLUT 0 y el mismo TEX0, con retornos capturados.
MR-T4b/c y [MR-T4d completadas](f03-02-map-draw-state.md): el contraste posterior
verifica VU0, consumo GS y transparencia de ambas formas en PCSX2 software.
El visor de 2DS XL conserva su checker de diagnóstico y su validación física
anterior. El [nuevo visor de material](f03-02-material-inspection.md) ya integra
material y transformación; el usuario confirmó ambos paneles con transparencia,
controles, START, tapa y HOME en New 2DS XL.

[Primer control en PCSX2](f03-02-map-runtime-bank.md): se alcanzó el recorrido
en vivo y se siguió su salida con banco vacío. El MAP disponible es distinto
del objetivo, por hash de todo el recurso. MR-T4a completada; se conserva
como evidencia previa, junto al nuevo control sin montaje. La carga posterior
usa los cargadores del juego con solicitudes de diagnóstico registradas,
sin necesitar una partida avanzada ni inyectar la textura.
