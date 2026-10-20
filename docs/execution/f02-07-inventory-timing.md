# F02.07 — Margen temporal del inventario (SRC128)

Fecha: 2026-10-19. Contrato: [IT01–IT05](../../schemas/runtime-inventory-timing-v1.md).
Base preservada: [SRC127](f02-07-host-callback.md). Evidencia:
[inventario temporal](../compatibility/inventory-timing-evidence.json).

## Resultado y alcance

RT-T3c.2 e IT-T1–IT-T4 completados: doce sesiones con VM pausada aceptan sus
tres respuestas cada una y cierran limpiamente. Los manifiestos consumen
94,68–95,25 % del tiempo de muestreo. El menor margen global observado antes
del cierre es 463,27 ms. No cambia código de producción, plazos, hashes,
identidades ni doble verificación. Gates y captura siguen pendientes.

La medición corresponde al PCSX2 x86_64 fijado, ejecutado en este host arm64,
con renderer Null, ISO europea y BIOS privadas ya autorizadas. No prueba
rendimiento gráfico, gameplay, consola 3DS, otro host ni estrés de todos los
núcleos. La carga añadida consiste en un único proceso SHA con búfer propio de
4 MiB; no se presume caché fría ni host inactivo. No hubo fallos de sesión en
esta matriz; los fallos de rondas anteriores permanecen preservados.

## Comparación fijada antes de ejecutar

Dos repeticiones por variante/condición; orden limpio→gruesa→fina y luego
fina→gruesa→limpio. La matriz, incluidos los dos testconfig, duró 168,03 s.
Los valores de esta tabla suman las tres duraciones registradas por el
consumidor ordinario; no incluyen arranque ni todo el cierre, y no equivalen al
plazo global medido dentro del productor.

| Condición | Variante | Repetición 1 (s) | Repetición 2 (s) | Respuestas |
| --- | --- | ---: | ---: | ---: |
| Sin carga añadida | Limpio | 4,5623 | 4,4985 | 6/6 |
| Sin carga añadida | Gruesa | 4,4890 | 4,5051 | 6/6 |
| Sin carga añadida | Fina | 4,4612 | 4,5164 | 6/6 |
| Un proceso CPU | Limpio | 4,5432 | 4,4885 | 6/6 |
| Un proceso CPU | Gruesa | 4,5324 | 4,4814 | 6/6 |
| Un proceso CPU | Fina | 4,5025 | 4,5163 | 6/6 |

El candidato limpio es exactamente SRC126, SHA-256
`716628b435ca3ee0e93cefad4646f09e742a4e443d954b137e29fa47b63788f4`.
La única copia instrumentada tiene SHA-256
`d7dfa1bb08300a7456275639d7a52dfad57838f47e70eff1c96d6badc742fabe`;
la variable del perfil selecciona sonda gruesa/fina antes de iniciar el hijo.
Se recompilaron seis unidades y reutilizaron 464 entradas de enlace: ningún
cambio funcional se incorporó al candidato limpio.

Los 36 frames pasan el consumidor estricto fijado y se vuelven a decodificar
en la auditoría. Cada uno conserva 30 imágenes de aplicación, 1.040 de caché,
revisión 1.071 y épocas `[53, 3, 1, 1]`; ninguna muestra admite captura. Se
verifican identidad del proceso, nonce estable por sesión y secuencia 1–3.
Los procesos propios de carga terminan con su wrapper; los 12 grupos de
ejecución quedan vacíos. No se crean partidas ni memory cards.

## Distribución y márgenes

Son 24 muestras instrumentadas; las fases finas tienen 12 observaciones.
Las medianas siguientes describen esta muestra pequeña, no una población.

| Intervalo | Mediana (ms) | Mínimo–máximo (ms) |
| --- | ---: | ---: |
| Preparación, una vez por sesión | 74,10 | 62,44–99,63 |
| Muestra completa | 1.445,46 | 1.420,37–1.552,21 |
| Manifiesto inicial, dos pasadas | 684,61 | 672,62–795,61 |
| Primera pasada de orígenes | 36,00 | 35,16–38,15 |
| Segunda pasada de orígenes | 35,51 | 34,68–36,87 |
| Manifiesto final, dos pasadas | 683,05 | 673,41–698,24 |
| Composición de digests finales | 2,14 | 1,90–2,47 |
| Método SHA update, inclusivo | 1.292,45 | 1.271,75–1.320,70 |
| Lecturas de archivos, inclusivas | 37,35 | 32,85–110,71 |
| Identidad de archivos, inclusiva | 43,64 | 41,71–47,61 |
| Estabilidad de orígenes, inclusiva | 51,05 | 50,26–51,64 |
| Retirada y unión desde inicio del cierre | 1,30 | 1,28–2,48 |

Las últimas cuatro fases de trabajo fino están contenidas en fases mayores;
**no se suman** a manifiestos/orígenes. La partición gruesa se valida con
duraciones, orden y límites dentro de la muestra. La preparación tampoco
forma parte del intervalo `sample`.

En cada muestra fina se leen 393.536.512 bytes, exactamente cuatro veces los
98.384.128 bytes de los 46 archivos del manifiesto. Hay 368 comprobaciones
de identidad, 6.296 llamadas de lectura y 4.280 comprobaciones de estabilidad
de orígenes. SHA recibe 393.593.963 bytes en 12.009 llamadas: incluye también
la representación canónica del inventario, además de los archivos.

El margen al comenzar el cierre fue 463,27–536,31 ms respecto a los cinco
segundos globales. Para las consultas 2 y 3, el margen tras entrega fue
463,44–576,85 ms respecto a su deadline efectivo. Este último es el mínimo
entre el plazo global y el plazo por respuesta; **no son dos segundos nuevos
independientes del global**. Los timestamps de submit usan el `now` y deadline
ya existentes; la sonda no añade llamadas a `DiagnosticBudget`.

## Coste de observación y decisión

El acumulador fijo usa menos de 8 KiB por hilo y cuatro posiciones de consulta.
No imprime en las fases medidas. DW vuelca al cerrar Work; IO, después de unir
DW. La calibración previa al servicio realiza 10.000 pares de lecturas de reloj
y registros: 60,34–63,78 ns por iteración. Es una medida básica local, no un
límite de perturbación, ni la suma de todos los costes de TLS, ramas y scheduler.

Las duraciones limpias y observadas se solapan; incluso algunas observadas son
menores. Con dos repeticiones por grupo no se puede aislar una penalización
causal de la sonda ni afirmar sobrecoste nulo. No se resta la calibración a los
tiempos, ni se infieren percentiles, garantías de tiempo real o margen bajo
cualquier carga.

La causa medida es el camino de verificación completa de archivos. El método
`MacOSSha256::update` ocupa 85,09–89,66 % de la muestra, **incluyendo sus
checkpoints**; esta sonda no separa el kernel CommonCrypto de esos controles.
No demuestra que la arquitectura x86_64 sea la causa de ese coste.

Decisión: conservar producción y todos sus controles. Optimizar ahora la
estabilidad de imágenes tendría poco efecto sobre el coste principal. Un
experimento futuro debe separar CommonCrypto/checkpoints y, si procede,
contrastar un proveedor SHA equivalente detrás de `DigestEngine`. Requiere
vectores conocidos, particiones de streaming, errores/cancelación, identidad
antes/después y cuatro verificaciones completas, más reconstrucción limpia y
la misma matriz. No se adopta caché por metadata, hash parcial, ampliación de
deadline ni cambio de arquitectura sin evidencia propia.

## Pruebas, custodia y próximos pasos

Pasan 20 pruebas del acumulador C++/RAII, parser, límites, superposición,
metadatos inválidos y resultados parciales. Las inserciones exigen anclas
únicas; las seis fuentes privadas se reproducen byte a byte con el integrador
final. Las pruebas se descubren en la batería Python del pipeline existente;
el fixture nativo se compila con Clang. No se ha ejecutado CI remoto en esta ronda.
Las 58 pruebas de repositorio/supervisor verifican además contratos y enlaces.
El primer intento bajo sandbox dio 52 éxitos y seis fallos: `/bin/ps` estaba
bloqueado y no permitía comprobar los grupos propios. Se conserva su JUnit;
la repetición autorizada con acceso a procesos pasa 58/58 sin cambiar código.

Los cambios de formato del integrador/wrapper no alteran su AST ni las fuentes
generadas. El parser recibió dos negativas adicionales de partición temporal;
los doce logs originales producen exactamente los mismos resultados con la
validación reforzada. Se preservan las versiones anteriores al formato y los
recibos originales; no se repiten sesiones para sustituir resultados.

Se verifican las 268 entradas públicas previas y las ocho etapas privadas de
SRC127, el código completo fijado, objetos reutilizados, 19 bibliotecas/390
miembros y el consumidor congelado de 92 archivos. Ambos bundles conservan 200
archivos regulares y 42 Mach-O, firma ad hoc y resolución de frameworks. Los
logs, ISO, BIOS y perfiles permanecen privados.

IT-B mantuvo inicio ≥11 GiB, suelo ≥10 GiB y uso combinado ≤512 MiB. Los 43
recibos registran un mínimo de 12,51 GiB libres y máximo combinado de 109,45 MiB. Build
incremental: 45,60 s; sesiones limitadas a 100 s, matriz a 900 s, mediciones cada
0,5 s. El presupuesto general IB02 de 20 GiB no cambia.

La siguiente tarea principal es **RT-T3c.3a**: derivar de estos frames el mapa
de hechos satisfechos, violados y desconocidos, enlazar cada bloqueo a JIT,
caché, DMA o lifecycle y definir pruebas positivas/negativas por dueño, época
y recurso. Después se implementarán gates individuales y se contrastarán en
RS-T3/RB-T3/DW-T3 antes de solicitar admisión.
