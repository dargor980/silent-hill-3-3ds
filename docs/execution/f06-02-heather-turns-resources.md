# F06.02/heather-turns — HG-T4.4: recursos, pila y ARM

2026-10-30. **HG-T4.4 completada en su alcance local.** Se cierra HG-T4
con inventarios ABI, ensayo de asignaciones y pico de buffers en host,
presupuesto conservador, pila de compilador y compilación ARM.
Aplican HGT07–12 del [contrato](../../schemas/heather-turns-native-v1.md).
**Sigue HG-T5**, empaquetado A/B y protocolo de consola. El build instalado
`c3aae59d1a70` se conserva; HM-T5 adicional y pared 60 siguen aplazadas.

## Almacenamiento

Inventario de 25 cantidades con `sizeof` y constantes del código actual.
Host: Apple Clang 15, ABI de 64 bits y renderer con dobles SDK.
ARM: devkitARM GCC 16.1.0, ABI de 32 bits y cabeceras reales del SDK;
se extraen los valores de un objeto compilado con las opciones del renderer.
No se ejecuta ese objeto ARM en el host.

| Recurso, bytes | Host | ARM |
| --- | ---: | ---: |
| Transformación TR / alineación | 28 / 4 | 28 / 4 |
| `InspectionLocomotion` | 422412 | 422412 |
| Estado + workspace de locomoción | 18040 | 18040 |
| Instantánea del actor | 9252 | 9252 |
| Actor | 27960 | 27944 |
| Controlador | 28024 | 28000 |
| Bucle | 28072 | 28036 |
| `RoomAssets` | 1428296 | 1428288 |
| `RoomFrame` | 748728 | 748728 |
| `RoomWorkspace` | 535360 | 535360 |
| Renderer | 480 | 1120 |
| Controles / puerto de contactos | 64 / 560 | 64 / 556 |

Estado+workspace y controlador permanecen bajo sus límites de 32 KiB.
La capacidad TR sigue siendo 80 muestras/163520 bytes; el perfil 2 utiliza
78 muestras y 78624 bytes de TR activos. SRI2 ocupa 310356 bytes.
Se mantienen SRI1 ≤64 y perfil 1 de 58 muestras. Los arreglos grandes
residen en objetos de heap preasignados, no en variables automáticas por paso.

## Pico y presupuesto

`test_heather_turns_resources` usa el cargador, renderer, bucle, contactos y
lector de producción. Un registro fijo intercepta `new`/`delete`, incluidos
los casos alineados y `nothrow`; el doble SDK avisa al reservar/liberar buffers.
Así se mide su coexistencia, incluido el staging de texturas. No se suman
picos separados como si fueran simultáneos.

La carga y su sustitución atómica se ensayan antes de crear el renderer.
Con la escena lista, ocho objetivos recorren ambos giros, caminar, correr y
espera. Cada objetivo ejecuta 32 pares de paso normal y R pausado, además
de suspend/resume; al terminar se reinicia. Se rechaza cualquier asignación
o liberación de C++/buffers SDK durante esa fase. Son **512 actualizaciones
por ensayo**, 2048 entre A/B × Release/ASan. La conformance de CTest ejecuta
también el mismo ensayo con recursos sintéticos, aptos para CI.

Las cuatro ejecuciones privadas dan valores idénticos:

| Medida de buffers, bytes | Resultado |
| --- | ---: |
| Pico de carga C++ | 3438888 |
| Pico al reemplazar con escena anterior viva | 4867184 |
| Residente C++ + buffers SDK | 32183585 |
| Pico conjunto rastreado | 34252665 |
| Asignaciones durante pasos | 0 |
| Liberación completa al cerrar | Sí |

El pico rastreado es **32,67 MiB**. Cuenta bytes solicitados por el código y
buffers del doble SDK: no es RSS, overhead del asignador ni medición de GPU,
SDK o consola real. El presupuesto reserva esos costes explícitamente:

| Partida, bytes | Presupuesto |
| --- | ---: |
| Texturas | 27787264 |
| Staging de textura | 2097152 |
| Mapa residente | 2009704 |
| Geometría dinámica residente | 1400184 |
| Modelo y temporales | 994636 |
| Staging del cargador | 2855448 |
| Reserva de plataforma | 12582912 |
| Extra del runtime | 2097152 |
| **Total** | **51824452** |

Total **49,42/64 MiB**, idéntico al calcularlo con ABI host y ARM.
Quedan 1862639 bytes hasta el límite del 80 % de RNF02.02; se conserva más
del 20 % de margen. Frente al presupuesto HM anterior aumenta 98316 bytes.
El ensayo exige además que pico rastreado + reserva de plataforma quepan
en el total y que todos los buffers se liberen.

Las fuentes A/B se autentican contra sus manifiestos fijados. Las copias
locales de auditoría combinan el runtime de materiales hp34 con el SRI2 HG;
solo cambian `heather.sri` y su CRC en `scene.srr`. Los 26 archivos de datos
resultantes son idénticos entre copias. Son entradas de ensayo, aún no un
paquete de entrega HG-T5. Ningún recurso original se añade a git/CI.

## Pila

La opción `SH3_STACK_AUDIT` genera `.su` y, con GCC, grafos `.ci`.
El auditor exige las 24 unidades de producción de esta ruta; rechaza informes
incompletos, frames sin cota o superiores a 8192 bytes y recursión directa
inesperada en los grafos GCC. Conserva la mayor emisión de cada etiqueta y
suma todos los frames seleccionados, incluso los mutuamente excluyentes.
Añade 26 niveles de cada frame `introsort` para hasta 6032 triángulos y
**8192 bytes de reserva externa** para SDK/libc.

| Compilador | Frames | Suma | Extra de ordenación | Con reserva / 32768 |
| --- | ---: | ---: | ---: | ---: |
| Clang Release | 150 | 18448 | 5408 | 32048 |
| GCC 12 Release | 124 | 18432 | 2496 | 29120 |
| ARM GCC 16.1 | 132 | 16704 | 3120 | 28016 |

El mayor frame ARM es de 4136 bytes, asociado al buffer de CRC por bloques.
El ELF final contiene `__stacksize__ = 32768`, leído en su sección de datos.
Estos resultados son un inventario estático conservador del código propio
con una reserva adicional: **no prueban el peor caso interno de bibliotecas
externas ni sustituyen una marca de agua de pila en consola**. GCC comprueba
aristas directas; Clang no emite ese grafo. Las llamadas externas quedan
enumeradas en los informes locales, incluidos aliases de constructores.

Ocho pruebas del auditor cubren frames duplicados, límites, datos vacíos,
unidades/grafos ausentes, recursión directa/mutua y la excepción de ordenación.
Cobertura combinada líneas/ramas del auditor: 92,5 %.

## Validación y compilación

- **30/30 CTest** Release en Clang y GCC 12.2, incluidos los dos gates de pila.
- **28/28 CTest** ASan/UBSan y **28/28** GCC con cobertura; pila sin instrumentación.
- Regresiones HL/HM, vectores HG congelados, contactos, render y controles
  incluidos en la selección; no se cambian las tolerancias.
- **17 gates individuales C++ ≥80 % líneas / ≥80 % ramas**, incluidos
  reloj, poses, publicación, acciones, actor, controlador, runtime y render.
  Menores valores: probe 84,2/86,6; entrada de escena 97,6/85,8.
- Repetición privada con el binario Release actual: **70 poses/2520 matrices**,
  máximo original 0,00048828125 y oráculo independiente 0,0001598172219701155,
  ambos bajo 0,001. Los 3168 extremos crudos mantienen máximo
  5,960464477539063e-8 y se rechazan 69 controles desplazados.
- Ruff y formato del ámbito de CI, contratos/custodia del repositorio y
  `git diff --check` aprobados.

GCC Release detectó una advertencia `maybe-uninitialized` al imprimir el FPS
opcional. `FrameCadence` ahora mantiene el valor inicializado y un indicador
de medición, preservando su API opcional y comportamiento. Su prueba existente
cubre reinicio, reversión temporal, frecuencia nula y valores medidos;
gate nuevo **100/100**, incorporado a CI. No se modifica la lógica de pausa/R.

ARM Release **`0188790baedd`**, imagen devkitPro fijada:
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
ELF32 ARM EABI5, text/data/bss 214116/7640/19336 bytes.
Shader comprobado: doce componentes escritos exactamente una vez.
Se verifican seis archivos por SHA-256, identidad de fuentes y cabeceras:

| Artefacto | SHA-256 |
| --- | --- |
| ELF | `a3469e8a68bf0a8ce352c8cd6d2e1c06ed6acbb41bb15059ff1a2ba025e97000` |
| 3DSX | `8c2612a3a203cb7e6a8b1995c9d0aade0a31112e43a437b49ccaa26b016d9f2d` |
| SMDH | `6dbe9fb8092b66126292997a88dfa2adf3f32fc5a8cb7845185343717eb160bc` |

Durante el trabajo Docker agotó disco por presión de memoria/swap; esos
intentos fallidos no cuentan como validación. La reserva temporal de la VM
se redujo de 6 a 2 GiB y los ensayos finales terminaron correctamente.
El valor configurado original quedó restaurado; la VM actual conserva 2 GiB
hasta su próximo reinicio. `test.postgres12` quedó en ejecución.

## Evidencia y continuidad

Informe agregado local: `reports/local/heather-turns-resources-v1.json`.
Detalle privado: `heather-turns-resources-private-v1.json` y
`heather-turns-resources-poses-v1.json` en el mismo directorio. Este último
solo acredita poses: sus indicadores de escena/ARM son falsos por alcance;
la integración y compilación se registran por separado en el agregado.
JUnit, cobertura, ABI, pila, comandos, paquetes SDK y binarios quedan en
`build/heather-turns-resources/`. Los scripts locales `run-builds.sh`,
`run-coverage.sh`, `private_resources.py`, `recheck_poses.py` y
`collect_report.py` conservan la reproducción y relectura de la evidencia.

El JSON de vectores HG-T3 permanece intacto, SHA-256
`433811f29a1687bb5bd357d73234f7290a0cbef407df18a6dba1575c62c833ae`.
No se ejecutó este build en emulador ni consola, no se copió a SD y no se
reabrieron HM-T5 ni pared 60. HG-T5 debe identificar el paquete de entrega
y su protocolo antes de la prueba física. F06.02 global y G04/G05 siguen abiertos.
