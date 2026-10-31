# F06.02/heather-turns — HG-T4.2: transporte y recursos de cinco clips

2026-10-30. **HG-T4.2 completada.** Productor y lector SRI2 del perfil 2 implementados; paquetes
privados A/B preparados y cotejados con los 70 retornos de HG-T2. Esta
unidad cubre datos y evaluación nativa. La coordinación de las cinco
acciones con HM pertenece a HG-T4.3, y el cierre de memoria/ARM a HG-T4.4.
Se conserva el build de consola `c3aae59d1a70`; HM-T5 adicional sigue aplazada.

## Formato, límites y compatibilidad

El [contrato HGT01/08/09/11/12](../../schemas/heather-turns-native-v1.md)
se aplica sin modificar sus vectores ni tolerancias:

| Límite | Valor |
|---|---:|
| SRI1 aceptado | 2–64 muestras |
| Capacidad decodificada compartida | 80 muestras |
| SRI2 perfil 1 | exactamente 3 clips / 58 muestras |
| SRI2 perfil 2 | exactamente 5 clips / 78 muestras |

El perfil 2 conserva magic, endianness y cabecera de 96 bytes. Añade
107/108 después de 101/109/113, con comienzos empaquetados 58/68. El
productor recibe `profile=2` explícito; el valor predeterminado sigue siendo
1. Los descriptores PAL se comprueban literalmente antes de decodificar
las fuentes. No se vuelve a convertir la velocidad PAL.

La cabecera nativa valida el par perfil/conteos antes de reservar memoria
o calcular el cuerpo. Rechaza identificadores desconocidos, cruces entre
perfiles, 79/80 muestras y conteos de descriptores desbordados. Después
comprueba CRC, campos reservados, bindings, tabla exacta, TR y geometría.
La publicación del rig y del paquete completo conserva la transacción
existente: solo sustituye la salida después del último cierre correcto.

SRI1 mantiene su límite tanto en productor como en validador/lector C++.
La capacidad del cuerpo compartido no cambia ese contrato. Los 58 TR
anteriores, huesos, helpers, vértices, índices, materiales y texturas del
paquete privado coinciden exactamente con HL. Las pruebas conservan el
hash sintético del formato legado.

El centro usa el frame 0 y el radio conservador incluye las 78 muestras.
La transformación compartida de hp34 no se modifica: este encuadre es
para el visor de actor y no reemplaza la transformación mundial de HM.

## Preparación privada y fidelidad

Adaptador local: `build/heather-turns-sri2/publish_and_audit.py`.
La fuente A usa MDL522/ANM525 retenidos y autenticados; B vuelve a recorrer
la ISO/MFA con la selección fijada. Se cotejan los bytes antes de producir
los dos paquetes exclusivos fuera del checkout:

- `/Users/germancontreras/sh3-private-data/heather-turns-a-v1`
- `/Users/germancontreras/sh3-private-data/heather-turns-b-v1`

Los 14 archivos y manifiestos coinciden. Cada SRI mide **310356 bytes**
(+20200 respecto al perfil 1). SHA-256 del manifiesto A/B:
`a33d89733b506a286e11c00d3f8553f7a2c179f10bc2d08e5baebadfb9f0ca30`.
La publicación verifica lectura y reconstrucción antes de publicar el
manifiesto. Por sí sola no certifica fidelidad; esta se comprueba después.

La auditoría independiente recorre todos los campos seleccionados contra
los decodificadores sin usar los cuaterniones corregidos del productor.
El dump C++ del archivo y sus muestras coincide con el oráculo SRI2. Luego
reautentica recibos, estados, RAM, recursos, código, jerarquía, ambos canales
y ordinales de HG-T2. El replay C++ comienza en una sola fase escalar de
espera; no inyecta matrices o cachés capturadas en el estado nativo.

| Comprobación | Resultado |
|---|---:|
| Retornos continuos / matrices | 70 / 2520 |
| Filas de reloj exactas | 70 |
| Error máximo C++ frente al original | 0,00048828125 |
| Error máximo C++ frente al oráculo independiente | 0,000159817222 |
| Límite conservado para matrices | 0,001 |
| Extremos crudos cotejados | 3168 |
| Error máximo de extremo | 5,96046447754e-8, límite 1e-7 |
| Controles con referencia desplazada rechazados | 69 |

Incluye ciclos completos de derecha/izquierda y las cuatro mezclas
espera↔giro, conservando la pose local fraccionaria del origen. El resultado
es idéntico desde A y B. No se vuelve a ejecutar PCSX2 ni se generan
capturas nuevas. Los recursos y matrices originales permanecen privados.

Informe local: `reports/local/heather-turns-sri2-private-v1.json`, SHA-256
`43192c467d18c5a9557b512815ce69ee5410ba458482f44a4325be1806682cb8`.
Referencia HG-T2 fijada:
`478d2c60ec9bcdc8d1f7b572847e72f9cd410a609fc61f108d4ed5fcd494567e`.

## Pruebas y memoria

[Pruebas Python](../../tests/python/test_heather_turns_sri2.py) y
[harness C++](../../tests/cpp/test_inspection_locomotion.cpp) cubren los
límites separados, todas las asignaciones nuevas, reconstrucción completa,
selección de muestras, origen de datos, publicación y corrupción.

El lector nativo verifica **5745 rechazos con salida idéntica byte a byte**.
Incluye cada byte de los dos descriptores añadidos, NaN en cada componente
de los 720 TR nuevos, cabeceras cruzadas sin asignaciones y fallos de las
tres reservas/cierres del paquete. Los callbacks observan el estado anterior;
un reintento correcto publica el nuevo modelo. Se mantienen los fallos
adversarios y las pruebas SRI1/HL anteriores.

Las 25 pruebas CTest relacionadas pasan en Clang Debug, ASan/UBSan y GCC 12:
reloj, poses, publicación, SRI1/SRI2, skinning, controles y regresiones HM.
Pasan **834 pruebas Python**. Los seis módulos de productor, preparación compartida, publicación
y oráculos alcanzan 100 % de líneas y ramas individualmente.

Gates C++ individuales, recolectados únicamente desde
`build/heather-turns-sri2/coverage` con GCC 12.2:

| Unidad | Líneas | Ramas |
|---|---:|---:|
| reloj | 111/111 — 100 % | 138/138 — 100 % |
| poses | 180/183 — 98,4 % | 197/220 — 89,5 % |
| publicación | 45/45 — 100 % | 42/42 — 100 % |
| visor HL | 123/146 — 84,2 % | 103/119 — 86,6 % |
| rig/lector de muestras SRI2 | 28/28 — 100 % | 38/38 — 100 % |
| lector de archivo/paquete SRI2 | 192/192 — 100 % | 166/168 — 98,8 % |

La imagen local fijada de devkitPro se ejecutó sin red; digest
`sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`.
Ruff, formato Python, control del repositorio y `git diff --check` pasan.
No se ejecutó GitHub Actions remoto. JUnit y cobertura están bajo
`build/heather-turns-sri2`; resumen de evidencia:
`reports/local/heather-turns-sri2-v1.json`.

Medidas de almacenamiento: TR activos **78624 bytes**; arreglo de capacidad
73×80×28 = **163520 bytes**, aumento **32704** por rig; modelo nativo
`InspectionLocomotion` **422412 bytes** en host. El archivo es 310356 bytes.
Estos valores no son el pico total del proceso ni una medición ARM.
El estado/workspace del núcleo no crece con esta unidad. HG-T4.4 deberá
medir el presupuesto final con escena, cargas y plataforma integradas.

Durante la validación se agotó espacio al escribir JUnit: una prueba de
tamaño excesivo producía un identificador de 64 MiB. Se le asignaron nombres
breves, sin cambiar datos ni expectativas. Se eliminaron caché/temporales
y objetos regenerables sanitizados, conservando ejecutables y evidencia.
La repetición terminó correctamente y su JUnit ocupa 122511 bytes. Docker
quedó bloqueado por falta de espacio; se reinició con la autorización previa
y se verificó `test.postgres12` activo antes de cerrar.

El intento alternativo con GCC 16 de Homebrew/macOS no se admite como gate:
23/25 pruebas pasaron, pero el lector rechazó el magic incluso con lectura
de 96 bytes y prefijo correcto. Queda registrada esa configuración local
por investigar; no se modifica el formato para acomodarla. Los resultados
aceptados usan Clang y GCC 12 Linux de la imagen fijada, cuyos 25/25 pasan.

## Siguiente unidad

**HG-T4.3:** cinco acciones en actor/controlador/bucle, puentes por espera,
reemplazo de intención y publicación conjunta con contactos. Después,
HG-T4.4 valida pico/pila, ARM y gates finales; HG-T5 empaqueta y entrega.
F06.02 global, G04/G05 y la investigación de navegación de pared 60
permanecen abiertos; HM-T5 adicional continúa aplazada.
