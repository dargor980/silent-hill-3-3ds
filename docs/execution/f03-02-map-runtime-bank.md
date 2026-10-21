# F03.02 — Control del banco externo en PCSX2

2026-10-20. Avance de **MR-T4**, requisito MR07. Se ejecutó PCSX2 y se siguió
la consulta del banco externo hasta su rama de salida. **La asociación de
material de las dos formas seleccionadas no se verificó en este control**: la partida
disponible carga otro MAP y su banco externo está vacío.
Este documento conserva el control negativo inicial. La
[prueba posterior de carga y material](f03-02-map-runtime-binding.md)
completa MR-T4b/c; el [contraste posterior del dibujo](f03-02-map-draw-state.md)
completa MR-T4d para ambas formas mediante VU0, consumo GS y píxeles.

## Ejecución y resultado

Se reutilizó el ejecutable de SRC51, sin recompilar, SHA-256
`54b24d2087bc8000e1367990a2acc4b615295a94a2cfd1e1c61ca464e9714b49`.
Se creó un perfil privado aislado, con copias de BIOS y tarjetas, nuevos slots,
PINE local, MTVU desactivado y renderizador automático. Se restauró el slot 95
de la sesión anterior `acquisition-live-v1`.
Es una **reproducción de diagnóstico desde savestate**, no una captura nueva
ininterrumpida ni una admisión del observador.

Los breakpoints de ejecución se cargaron desde la configuración del depurador:
`0027B770` (recepción del banco), `001B1350` (argumentos de selección CLUT/TEX0)
y `001B25A0` (recorrido de dibujo del banco externo). Al reanudar se alcanzó el
tercero. Se guardaron estados privados mediante PINE, comprobando PID del peer
y estado pausado antes y después de cada solicitud. Los ZIP se leyeron con el
lector acotado existente y validación CRC; no se enviaron escrituras a RAM.

| Comprobación en las siete capturas | Resultado |
|---|---|
| Área del banco, `01D0B0A0` | Puntero nulo |
| Contador del banco, `01D0B0AC` | Cero |
| MAP del contexto 0, `01D0B3A0` | `01643A00` |
| MAP de los otros tres contextos | Punteros nulos |
| Lista de formas de esta ruta, contexto +`760` | Nula en los cuatro contextos |
| MAP cargado, comparación de todo el recurso | 2.546.352 bytes; SHA-256 exacto del catálogo |
| Cinco ventanas de código en RAM | Iguales al ELF europeo verificado |

El recurso observado es
`asset:90fae3ad31dd734229fc9fba5ac55dbc9eadb4ec8c7293d785446c8ad07a37ba`,
SHA-256 `2b2a8d32c0fac1d74ab3739fdc3bae0209f12b1757f60f82fce350f2e0a34bd6`.
La identificación compara todos sus bytes, no solo el nombre o la cabecera.
Difiere del MAP objetivo
`asset:464325b2533b0e0a0702d4ad52f7050d41e9a02ba308dea7bce2a3268e83d4ae`.

## Recorrido observado

| Slot | PC | Ciclo EE | Interpretación limitada |
|---|---|---|---|
| 01 | `001B25A0` | 41.511.085.920 | Entrada al recorrido |
| 02 | `001B25A0` | 41.511.085.920 | Misma pausa; no prueba avance |
| 03 | `001B25A8` | 41.511.085.922 | Avance de instrucciones |
| 04 | `001B25BC` | 41.511.085.927 | Antes de consultar el contador |
| 05 | `001B25C4` | 41.511.085.934 | Consulta retornó `v0=0` |
| 06 | `001B25D0` | 41.511.085.937 | Rama del banco vacío, `s3=0` |
| 07 | `001B266C` | 41.511.085.939 | Epílogo; resultado cero |

Los siete archivos representan seis pausas distintas y 19 ciclos EE desde
la entrada hasta el epílogo. El intento inicial de «Salir» del depurador no
avanzó la ejecución; se conservó el slot duplicado y se continuó con pasos
verificados por PC/ciclo. No se infiere avance del éxito de un clic.

La rama observada omite el bucle que llama a `001ABD20` y `001B23B0`.
Por ello **no hay textura, CLUT ni alpha observados para estas dos formas
en esta escena**. Este resultado no demuestra que el banco siempre esté vacío
ni refuta la textura candidata en el escenario objetivo.

## Evidencia y comprobaciones

Estados, registro de lanzamiento y cierre:
`/Users/germancontreras/sh3-private-data/f03-02-map-runtime-v1/`.
PCSX2 terminó normalmente con código 0; el socket desapareció y las BIOS y
tarjetas originales conservaron sus hashes. Los archivos originales, memoria
y estados permanecen fuera del repositorio.

Informe local de metadatos:
`reports/local/f03-02-map-runtime-negative-v1.json`,
11.779 bytes, SHA-256
`1c4ce03fdc5e337a51ae1fba55ee0a858d935addd4c2aa6846bd9bb72fbdda35`.
Incluye hashes individuales de las capturas y auxiliares, los resultados de
comparación con el ELF y banderas explícitas de material no verificado.

Auditoría reproducible sin abrir el emulador:

```sh
rtk proxy .venv/bin/python build/f03-02-map-runtime/audit.py
```

El auxiliar verifica las siete capturas, la monotonía de ciclos salvo el
duplicado declarado, todos los bytes del MAP, las cinco ventanas del ejecutable
y el cierre. Repetirlo exige igualdad exacta del informe existente.
Los auxiliares operativos están en `build/f03-02-map-runtime/`; no forman una
API pública ni un nuevo mecanismo de admisión.

**184 pruebas existentes aprobadas**: parser de savestates, transporte PINE
y metadatos de render. JUnit: `build/f03-02-map-runtime/tests.xml`.
También pasan las **35 comprobaciones de repositorio** y `git diff --check`;
la segunda auditoría reproduce exactamente el informe de 11.779 bytes.
No hay cambios de decoder, motor 3DS, material del visor ni pipeline de build.

## Continuación sin una partida avanzada

El usuario confirmó que no dispone de una partida avanzada. Se consultó
`gamemain.c` de la referencia pública ya fijada
[memory-of-alessa, revisión 247c7f4](https://github.com/dreamingmoths/memory-of-alessa/blob/247c7f43fd619aff8d2086ea0b0af291c283ea9d/silent-hill-3/src/gamemain.c).
Describe otra región; no proporciona por sí solo un selector de escena
europeo verificado. No se aplicaron sus direcciones ni se alteró la partida.

El requisito previo es conseguir una **carga del MAP objetivo a través de la
solicitud de escena y los cargadores del juego**. La siguiente investigación
debe identificar ese recorrido en la edición europea y, si permite una carga
controlada, registrarla como experimento desde una copia privada. Inyectar
directamente la textura candidata en el banco no probaría cuál selecciona el
juego y no satisface MR-T4.

Después de cargar el MAP correcto, la comprobación debe:

1. Capturar `a2` en `0027B770`; identificar el área recibida por tamaño y hash
   completo contra el catálogo, incluyendo la posible ausencia de coincidencia.
2. Seguir el registro en `001ABDE0` y comprobar el área, contador y entradas de
   gestor; conservar procedencia entre callback y consulta por ordinal.
3. Enlazar el contexto MAP y sus formas con el gestor que recibe `001B23B0`;
   capturar el descriptor y los argumentos reales en `001B1350`, y el resultado
   del getter `001B5F20`. Decodificar TEX0 y CLUT efectivos.
4. Seguir el paquete hasta el dibujo GS/VU y verificar alpha, visibilidad y
   transformación. Solo entonces actualizar el material y la matriz del visor.

MR-T4, MP-T4 y MG-T4 permanecen abiertas. El control negativo y la falta de
acceso al escenario son evidencia útil, pero no sustituyen esos pasos.
