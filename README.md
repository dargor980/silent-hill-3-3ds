# Silent Hill 3 PS2 → Nintendo 3DS

Proyecto de adaptación nativa con origen PS2 y destino confirmado **New Nintendo 2DS XL**. Estado: F00 completada y G00 aprobada para identificación, alcance y custodia; F01/diagnóstico sintético en curso. Todavía no hay juego portado. La ISO europea del usuario permanece como entrada local ignorada en `binaries`.

**Heather original:** [HI-T1–T5a](docs/execution/f03-02-heather-inspection.md)
identifican y convierten `chhaa.mdl`, esqueleto, materiales y animaciones.
El build **`f25a2d9bb316`** presenta a Heather texturada y animada: 36 huesos
activos, 6.943 vértices, 5.522 triángulos y 13 texturas. Añade
[primer plano con SELECT](docs/execution/f03-02-heather-camera.md) y corrige
la orientación vertical de las texturas en PICA. ARM y 88 segundos
continuos en Azahar comprobados. **HI-T5b/HI-T6c funcionales confirmadas:**
60 s, rostro/SELECT/zoom/controles, START y tapa/HOME en
[New 2DS XL](docs/compatibility/heather-inspection.md). Baja fluidez reportada
con CPU/submit/GPU ≈60,7/49/4,36 ms; se prioriza
[HP: rendimiento](docs/specs/sh3-3ds/heather-performance.md).
El build **`8f778b6e4960`** prepara vértices compartidos una vez, solicita
CPU rápida en New y añade FPS submit. [HP-T1–T4](docs/execution/f03-02-heather-performance.md):
353 CTest por preset, ARM y 90 s en Azahar. **HP-T4 física confirmada:**
60 s en cuerpo y 60 s en cara, mayor fluidez y controles/START/tapa/HOME.
Lecturas conjuntas aproximadas: 29,9 FPS submit, New fast, CPU/submit/GPU
10,27/23,1/6,34 ms; sin métricas separadas por encuadre.
Reloj de inspección y luz neutra; movimiento jugable, expresiones y habitación
todavía pendientes. [Spec EARS](docs/specs/sh3-3ds/heather-inspection.md).
[HL-T1/T2](docs/execution/f03-02-heather-locomotion.md) inventarían 49
descriptores y acreditan una vuelta del clip `0x65` en PCSX2: 67 avances,
ambos canales, un reinicio y 67 poses dentro de tolerancia. Se conserva el
modelo original. HL-T3 enlaza controles normales con caminar `0x6D` y correr
`0x71` y verifica poses estables, retorno a espera, interrupción de mezcla y
un punto en cada sentido caminar↔correr. Dos intervalos de controles normales
grabados acreditan vueltas completas de caminar/correr y 54 poses, con máximo
0,000389 < 0,001. Ambos sentidos de caminar↔correr tienen transiciones completas
contrastadas en series separadas: 14 y 15 poses, máximo 0,000369. Otra serie
verifica el wrap dentro de la mezcla y su salida: 15 poses, máximo 0,000369;
HL-T3c.3 cerrada. HL-T3c.6 acredita espera↔caminar completa: 49 capturas,
47 poses y máximo 0,000416 < 0,001, con origen interpolado conservado.
La parada directa correr→espera añade 25 capturas y 24 poses, máximo 0,000413.
HL-T3 queda cerrada para el banco 525 y las cinco transiciones observadas,
con restauraciones y límites documentados.
[HL-T4a](schemas/heather-locomotion-v1.md) fija el contrato multiclips,
cinco transiciones y formato SRI2, con 30 comprobaciones sintéticas.
HL-T4b.1 implementa el planificador puro de reloj/selección: 173 actualizaciones
cotejadas, pruebas Release/ASan/UBSan y cobertura local completa del módulo.
HL-T4b.2 añade el evaluador local y la caché congelada, con 26 poses sintéticas
cotejadas y pruebas Release/ASan/UBSan. HL-T4b.3 completa la publicación conjunta
sin cambios parciales ante errores: 410 snapshots cotejados, 18.040 bytes de
estado/workspace y 31 pruebas por preset con regresiones SRI1. HL-T4c.1 añade
el productor SRI2 de 58 muestras, con mapa/canales/descriptores, verificación
de fuentes y recibo de correspondencias; 435 pruebas relacionadas aprobadas.
HL-T4c.2 añade lector SRI2 y reconstrucción independiente, con publicación
atómica tras comprobar archivo/texturas: 650 rechazos sin mutación, 542
pruebas Python y 33/33 pruebas Release y ASan/UBSan por preset. HL-T4c.3
publica A/B idénticos y coteja 245 poses/8.820 matrices con las referencias
fijadas: máximo 0,000515, dentro de 0,001. 560 pruebas Python y gates
aprobados. HL-T4d.1 conecta el presentador SRI2, selección ZL/ZR, pausa/paso,
reinicio y suspensión con el núcleo; 37/37 pruebas Release y ASan/UBSan por
preset y 356 pruebas Python de reconstrucción. HL-T4d.2 integra el gate
individual del presentador (84,2 % líneas / 86,6 % ramas), verifica 364/364
CTest por preset y 608 pruebas Python, y prepara el build ARM `4707dacec7d1`.
Paquete privado SRI2/texturas A/B idéntico; arranque, cinco cambios y controles
comprobados en Azahar. La prueba física de `4707dacec7d1` falló al abrir
SRI2; el build corregido **`7250f427ffb9`** evita la barra duplicada en la ruta.
Pasan 37 pruebas C++ por preset, 356 Python y los seis gates GCC. El usuario
confirma carga, espera/caminar/correr, controles, START, tapa y HOME en
`7250f427ffb9`: **HL-T5a/b aceptadas**, 29,9 FPS, Skin+sort 10,08 ms,
Submit+wait 23,3 ms y GPU 4,32 ms aproximados. Duración y cobertura por
encuadre/arco pendientes en [HL-T5c](docs/compatibility/heather-locomotion.md).
[HM-T1 completada](docs/execution/f06-01-heather-spatial.md): inspector
espacial, 81 capturas y ocho ventanas de código verificadas; 322 pruebas
relacionadas y cobertura completa. [HM-T2a completada](docs/execution/f06-01-heather-movement-capture.md):
primera cadena de carrera, escritura X, corrección Y y matriz verificadas en
PCSX2; 16 estados y 52 pruebas sintéticas. El resultado espacial coincide con
HL; hay +87 ciclos EE de diferencia, sin equivalencia temporal acreditada.
[HM-T2b en curso](docs/execution/f06-01-heather-movement-profiles.md): 187 estados
nuevos, caminar/parada, giro derecho, reloj PAL de 2 ticks y suelo/registro
de formas verificados en su alcance acotado; 258 pruebas sintéticas. La suma
de altura coincide con los mismos operandos por continuación y paso.
Un contacto de `tpf1.cld` enlaza candidato, corrector, posición y matriz;
el recurso completo coincide con A/B. Cuatro llamadas verifican el plano sin
normalizar y la conversión de su corrección a punto fijo. Dos sumas no nulas
al centro están aisladas; una actualización completa atribuye el microajuste
X al redondeo de dos mitades del movimiento, con cuatro retornos de corrección
cero y publicación exacta en posición/matriz. Seis paredes y sus aristas
compartidas quedan inventariadas como referencias para la captura de esquinas.
Pendientes contactos y giros
restantes, ciclos y autoridad del movimiento antes del controlador y la habitación.
[Spec HM](docs/specs/sh3-3ds/heather-movement.md).


**Nuevo corte gráfico:** `sh3_render_probe` muestra una habitación sintética
texturizada con cámara orbital y profundidad. Compilado para ARM y observado en
Azahar; el usuario confirma arranque, cámara y controles en New 2DS XL.
El recorrido físico completo sigue pendiente. [Resultados y build](docs/execution/f05-01-synthetic-render.md),
[spec EARS](docs/specs/sh3-3ds/synthetic-render.md) y
[guía de consola](docs/compatibility/synthetic-render-probe.md).

**Texturas originales:** el [sondeo F03.01](docs/execution/f03-01-texture-structure.md)
verifica la estructura de 119 recursos PS2 (321 bloques de 4/8 bits), con resultados
idénticos en ambas copias privadas. La [primera muestra de 8 bits y 256×256](docs/execution/f03-02-indexed-texture.md)
ya produce RGBA y PNG privados idénticos desde ambas copias; el direccionamiento
se contrastó con tablas GS y se inspeccionó la imagen. Su comparación con el
material original sigue pendiente. El [visor nativo de textura privada](docs/execution/f03-02-texture-inspection.md)
ya carga esa muestra desde SD y la presenta en Azahar; incluye ZIP privado para
Homebrew Launcher. El usuario confirma la [prueba de este visor en 2DS XL](docs/compatibility/texture-inspection.md):
textura visible, cruceta, controles de cámara, START y regreso tras tapa/HOME.
TI-T5 completada; identificación del material e integración de escena pendientes.
El [sondeo del mapa candidato](docs/execution/f03-02-map-material-candidate.md)
ya verifica la jerarquía y localiza dos formas con 56 vértices para investigar
su material. Su [geometría local](docs/execution/f03-02-map-geometry.md) ya
produce 32 triángulos en JSON/OBJ privados. El [visor de geometría](docs/execution/f03-02-geometry-inspection.md)
los presenta desde SD con checker propio; el usuario confirma formas
rectangulares, controles, START y tapa/HOME en New 2DS XL, build `a039c31cb262`.
El [visor de material](docs/execution/f03-02-material-inspection.md) ya integra
modelo, textura y transparencia en el build `764be66e7762`, comprobado en Azahar.
El usuario confirma ambos paneles con transparencia, controles, START, tapa
y HOME en New 2DS XL. Las [convenciones estáticas](docs/execution/f03-03-static-geometry.md)
quedan separadas en un módulo puro con fixture asimétrico, 519 pruebas y
regresión exacta de la entrega.
La [primera pareja de esqueleto/animación](docs/execution/f03-02-skeleton-animation.md)
ya produce tres huesos y 76 muestras con reconstrucción exacta y dos salidas
privadas idénticas, con 836 pruebas.
La [verificación en PCSX2](docs/execution/f03-02-skeleton-runtime.md) confirma
su selección inicial, tres clips, reloj Q12 y composición de pose modelo
con NLERP en diez evaluaciones controladas. Pasan 108 pruebas, incluidas
31 nuevas; el contraste posterior de matrices de dibujo y skinning se
registra en CM-T4, más abajo.
La [investigación de activación](docs/execution/f03-02-animation-activation.md)
localiza la ruta de `0x0209` en el carrusel (`amusement_02`, sala `0xEB`).
El arranque sin restauraciones confirma que la instancia de carga desaparece
antes de jugar.
Ya se importó y cargó una [partida europea en Fortuneteller](docs/execution/f03-02-carousel-save.md),
Normal/Normal. En `0xEB` se verificaron la selección inicial por IA y
[una vuelta continua de `0x0209`](docs/execution/f03-02-animation-continuity.md):
28 retornos, 27 avances y poses coincidentes, con 140 pruebas aprobadas.
Faltan las transiciones de daño y muerte. La restauración posterior del
combate solicitada por el usuario se investiga como reproducción separada.
La [auditoría de colisión](docs/execution/f03-02-carousel-collision.md) encuentra
geometría de escenario para los tres actores, pero ninguna colisión de
personaje asociada a ellos en las muestras; esa ruta no permite dirigirles
el daño investigado con la configuración observada.
La [revisión de alternativas](docs/execution/f03-02-carousel-alternative-routes.md)
tampoco identifica una acción normal admisible entre las rutas examinadas;
las transiciones de daño y muerte conservan su estado pendiente.
El [visor de animación 0x1449](docs/execution/f03-02-animation-inspection.md)
ya reproduce tres huesos mediante ejes propios, con pausa, avance y reinicio.
Build `a1629eeace22`: 252 pruebas C++ en Release y sanitizadores, 172 Python
y 383 poses privadas contrastadas; controles y dibujo comprobados en Azahar.
La [prueba física](docs/compatibility/animation-inspection.md) fue confirmada por el usuario
en New 2DS XL: ejes animados, A/R/L, cámara, START, tapa y HOME;
no incluye todavía malla/skinning ni transiciones de daño o muerte.
La [malla MDL de ese actor](docs/execution/f03-02-character-mesh.md) ya se
decodificó en dos salidas privadas idénticas: 15 submallas, 1.455 vértices y
1.113 triángulos candidatos, con pesos y vínculos de huesos conservados.
Se añadieron 87 pruebas sintéticas. La [verificación CM-T4 en PCSX2](docs/execution/f03-02-character-runtime.md)
contrasta 500 muestras en cuatro poses de dos submallas: matrices/helpers,
pesos sin normalizar, componente homogénea y normales coinciden con VU dentro
de tolerancias cuantificadas. También se verifica el orden de 38 paquetes GS.
Pasan 229 pruebas, incluidas 34 nuevas. La [integración CM-T5a–d](docs/execution/f03-02-character-inspection.md)
ya dibuja la malla animada con sombreado propio, build `757b48fd1746`:
486 pruebas Python, 270 C++ por preset y 77.115 comparaciones numéricas.
ARM y Azahar comprobados; el usuario confirma **caballo animado y controles
en New 2DS XL**. [Registro físico](docs/compatibility/character-inspection.md):
Skin CPU ≈14 ms, Submit+wait ≈12 ms y GPU anterior 1,1 ms; duración sin confirmar.
[CT-T1–T3](docs/execution/f03-02-character-materials.md) recuperan tres texturas
512×512 y los vínculos de las 15 submallas: dos entregas idénticas, 363 pruebas
y 786.432 píxeles contrastados.
[CT-T4](docs/execution/f03-02-character-material-runtime.md) verifica las 15
submallas y sus tres texturas en PCSX2: 428 paquetes, 519 triángulos SW y
15.112 píxeles interiores; mezcla/prueba alfa desactivadas en esta pasada,
bilineal y clamp. 427 pruebas relacionadas, incluidas 64 GS.
[CT-T5a–d](docs/execution/f03-02-character-material-inspection.md) integran las tres
texturas en el caballo animado: build `3fde5682ed11`, 298 pruebas C++ por
preset, ARM y Azahar verificados. La prueba física de ese build falló con
bloqueo inicial. [CT-T5f](docs/execution/f03-02-character-material-gpu-fix.md)
completa la salida del shader y añade un gate del SHBIN; reemplazo
`ced27c955e41`: [prueba física funcional aprobada](docs/compatibility/character-material-inspection.md),
60 segundos con texturas, avance Q12, controles, START, tapa/HOME y sin bloqueo.
Tiempos del build corregido pendientes en CT-T5e.2; el visor conserva luz neutra.
[LI-T1–T3](docs/execution/f03-02-character-lighting.md) verifican la iluminación
de la pasada PS2: cuatro poses, 500 vértices y 1.712 colores GS exactos;
210 pruebas relacionadas. [LI-T4](docs/execution/f03-02-character-lighting-inspection.md)
integra un preset fijo recalculado por pose, SELECT para comparar con luz
neutra y tiempos de iluminación separados. Build **`b27d16a1671e`**, entrega
independiente. **LI-T4f.1 aceptada** por el usuario: 60 s por modo,
iluminación, SELECT, controles y START/tapa/HOME; tiempos **LI-T4f.2 sin medir**.
[GC-T4](docs/execution/f03-03-character-world.md) verifica el perfil del caballo
en mundo: 84 observaciones y operación homogénea con pruebas. La ruta en doble
no reproduce el redondeo VU. [GC-T5a–e](docs/execution/f03-03-character-world-inspection.md)
integra tres colocaciones fijas con texturas y animación compartida; build
**`abe9a7a35464`**, ARM y Azahar verificados. El error de colocación relativa
es ≤0,000331778 frente al cálculo en doble sobre los mismos vértices f32;
no mide precisión total EE/VU. **GC-T5f.1 aceptada**: 60 s, tres caballos texturados y animados,
controles y START/tapa/HOME. **GC-T5f.2 completada** con lecturas aproximadas:
Skin 14,25 ms, Place 26,9 ms, Submit+wait 35,50 ms y GPU previous 2,39 ms;
no se infiere FPS. El [intermedio inicial F03.04](docs/execution/f03-04-character-intermediate.md)
conserva malla, esqueleto, las 76 muestras de animación y metadatos; regenera
SAN/SCM idénticos al visor físico. 167 tests y dos conversiones privadas
idénticas. [IR-T5 completada](docs/execution/f03-04-character-render-intermediate.md):
materiales, 21 archivos de textura, preset de iluminación y tres colocaciones;
regenera SAN/SCM/SCT/SCL/SCW idénticos a las entregas físicas. 231 tests,
98,46 % de cobertura y 27 archivos A/B iguales.
[IR-T6 completada](docs/execution/f03-04-map-intermediate.md): dos paneles de
`hp34.map`, material transparente y 14 adjuntos originales conservados;
SGM/STX idénticos al visor aceptado `764be66e7762`. 504 tests, cobertura
98,15 % y 17 archivos A/B iguales.
[IR-T7a/b completadas](docs/execution/f03-04-collision-inventory.md): inventario
de colisión con 30 capturas revalidadas y contrato de registros definido.
[IR-T7c completada](docs/execution/f03-04-collision-registry.md): decoder puro
de ambos bancos y propietarios, 100 pruebas sintéticas y cobertura 100 %.
[IR-T7d completada](docs/execution/f03-04-collision-intermediate.md): adaptador,
preparador privado y reconstrucción de 242 archivos; 30 capturas reales
comprobadas en memoria, 206 pruebas del perfil y 462 de regresión aprobadas.
[IR-T7e completada](docs/execution/f03-04-collision-verification.md): oráculo
independiente y 257 pruebas del perfil; fallos de publicación, concurrencia
y gate individual de cobertura en CI verificados.
[IR-T7f completada](docs/execution/f03-04-collision-publication.md): dos paquetes
privados con 242 archivos y manifiestos idénticos; cotejo contra fuentes y
reconstrucción sin acceso externo desde ambos paquetes. Se cierra el perfil de
registros; la geometría/respuesta física de colisión y cámara/audio siguen pendientes.
[CF-T1–T3 completadas](docs/execution/f03-04-collision-shapes-research.md):
`tp1e.cld`/`tp1d.cld` enlazados con las tablas del escenario, 285 recursos A/B
sondeados y 30 capturas cotejadas. Listas de índices, formas de 80/48 bytes y
solapamientos dinámicos documentados; traslación de 1.740 vértices contrastada.
[CF-T4 completada](docs/execution/f03-04-collision-polygons-contract.md):
contrato poligonal CP01–CP15, dos fixtures propios y 50 vectores sintéticos
con expectativas comprobadas.
[CF-T5a completada](docs/execution/f03-04-collision-polygons-decoder.md):
decoder poligonal puro; 69 pruebas aprobadas y 100 % de líneas/ramas del módulo,
con los 50 vectores originales también comprobados bajo `-O`.
[CF-T5b completada](docs/execution/f03-04-collision-polygons-verification.md):
oráculo independiente y batería ampliada de 3.159 pruebas; barridos, límites,
alias, aislamiento, precedencia, metamórficas y fallos controlados verificados.
[CF-T5c completada](docs/execution/f03-04-collision-polygons-ci.md): helpers y
gate individual integrados; job de calidad verificado localmente con 8.307
pruebas principales aprobadas, controles negativos del gate y artefactos cotejados.
[CF-T6 completada](docs/execution/f03-04-collision-polygons-private.md):
285 recursos por copia A/B, con 233 aceptados, 52 no soportados y cero otros
rechazos; oráculo concordante y ambos CLD del carrusel cotejados con 30 capturas
conservadas. Dieciséis controles detectados y repetición idéntica normal/`-O`.
[CF-T7a completada](docs/execution/f03-04-collision-polygons-intermediate-contract.md):
contrato CPI01–CPI14 con buffer íntegro y vista por recurso; 24 ejemplos propios
comprobados normal/`-O`, con reconstrucción sin abrir fuentes y controles de
fidelidad externa.
[CF-T7b completada](docs/execution/f03-04-collision-polygons-intermediate.md):
tres APIs puras con fuente íntegra y vistas regeneradas; 139 pruebas,
100 % de líneas/ramas y 3.416 regresiones aprobadas.
[CF-T7c completada](docs/execution/f03-04-collision-polygons-preparation.md):
preparador con pins fijos, custodia y writer exclusivo; 104 pruebas propias.
Preparación A/B en memoria: 519 archivos lógicos y manifiestos iguales,
233/52/0.
[CF-T7d completada](docs/execution/f03-04-collision-polygons-intermediate-verification.md):
oráculo independiente de paquete/fidelidad y 279 pruebas nuevas; gates
permanentes para los cinco módulos CPI. Calidad local: 8.829 pruebas y gates
aprobados.
[CF-T7e completada](docs/execution/f03-04-collision-polygons-publication.md):
dos paquetes privados con 519 archivos y manifiestos idénticos; ocho
reconstrucciones sin fuentes y cotejo externo íntegro. 233 aceptados,
52 no soportados y cero rechazados; 30 enlaces históricos conservados y
575 entradas de conversión intactas. Cierra CF-T7 para el perfil estructural CPI.
[CF-T8 completada](docs/execution/f03-04-collision-extended-research.md):
consumidor de cilindro vertical de 48 bytes contrastado con 293 registros A/B;
modelo de listas dinámicas con 20 registros procedentes de la fase anterior.
Cabecera/X/Z/W coinciden en 29 capturas; 12 controles negativos y repetición
idéntica, con 647 entradas reverificadas.
[CF-T9 parcial](docs/execution/f03-04-collision-runtime.md): consultas de
cilindro rechazadas y aceptadas; el llamador conserva el resultado más cercano.
57 capturas sin restauraciones: traslación Y no nula, transición de fase,
12 listas registradas en ambos bancos y avance que vacía el contador de uno.
Una consulta procesa una forma residual y la rechaza sin alterar el resultado;
se conservan las discrepancias de 1 ULP frente al host.
La vuelta por «Continue» captura la limpieza de 17.664 bytes del overlay.
Un diagnóstico separado con copia del estado 55 y cambio exclusivo del PC
verifica el reset 12/0→0/0 en 86 ciclos, conservando punteros y formas;
sus dos capturas no se cuentan como juego normal.
[Escritores Y de CF-T9c](docs/execution/f03-04-collision-y-writer.md): 23 capturas
de una repetición sin modificar el estado identifican cuatro instrucciones
SQC2 y dos colas de fase 5; las cuatro colas finales coinciden con las originales.
Otras 13 capturas desde estado 24 intacto verifican la llamada anterior de
fila 1/buffer 0, con Y = −25 y cola idéntica a los estados originales 25/29/54.
467 pruebas auxiliares y 5.079 entradas auditadas. Quedan pendientes la
unicidad del último escritor entre extremos y la equivalencia numérica;
el reset ocupado natural sigue sin observar.
La respuesta física permanece pendiente.
La selección de luces entre escenas sigue pendiente.
El [sondeo de rutas de dibujo](docs/execution/f03-02-map-render-metadata.md)
ya separa los grupos por contador, localiza la matriz base y distingue palabras
de modo de índices de matriz, con evidencia estática europea y 398 pruebas.
El [primer control en PCSX2](docs/execution/f03-02-map-runtime-bank.md) alcanzó
esa ruta y verificó su salida con banco vacío; el MAP cargado es distinto
del objetivo. La [carga controlada posterior](docs/execution/f03-02-map-runtime-binding.md)
ya recibió el MAP y su textura externa por los cargadores del juego, con hashes
completos coincidentes, y verificó CLUT 0/TEX0 para ambas formas.
MR-T4b/c y [MR-T4d completadas](docs/execution/f03-02-map-draw-state.md):
transformación VU0 y STQ de 56 vértices contrastados; consumo GS de los
32 triángulos por cuadro bajo cámara de inspección. La reproducción software
verifica transparencia, niebla y orientación de textura en 16.380 píxeles
interiores: alpha exacto y error RGB máximo de 1/255. Esa tolerancia corresponde
a PCSX2; la integración en PICA usa cámara de inspección, luz/niebla capturadas
y su propia precisión de filtrado/mezcla.

- [Especificaciones EARS y backlog](docs/SPEC.md).
- [Alcance M0-M5: primera alpha en español y Normal/Normal](docs/scope.md).
- [Normas SOLID, testing y CI](docs/engineering.md).
- [Cierre de F00 e incógnitas](docs/execution/f00-07-decisions.md).
- [F01.01: ejemplo oficial reproducible, C++17 y pruebas del SDK](docs/execution/f01-01-toolchain.md).
- [F01.02: diagnóstico compilado, contratos y prueba física pendiente](docs/execution/f01-02-diagnostic.md).
- [F01.03: archivos, opciones y errores de I/O](docs/execution/f01-03-files.md).
- [F01.04: tono, errores NDSP y contadores](docs/execution/f01-04-audio.md).
- [F01.05: símbolos, integridad y breakpoints en Azahar](docs/execution/f01-05-debugging.md).
- [F01.06: recursos, ventana acotada y protocolo de métricas](docs/execution/f01-06-resources.md).
- [F01.07: suspensión, reanudación y controles reservados](docs/execution/f01-07-lifecycle.md).
- [F01.08: builds, gates y protocolo de treinta minutos](docs/execution/f01-08-builds.md).
- [F02.01: inventario verificado de 113 archivos ISO](docs/execution/f02-01-inventory.md).
- [Avance y evidencia de la primera ejecución](docs/execution/foundation.md).
- [Política de datos privados](docs/private-data.md).
- [Inventario de fuentes y perfil canónico](docs/compatibility/sources.md).
- [Licencias, procedencia y pendientes de adopción](docs/compatibility/licenses.md).
- [Edición europea identificada e inspección ISO](docs/compatibility/edition-comparison.md).

## Build y pruebas host

Requiere CMake ≥3.21, compilador C++17 y Python ≥3.11. En un entorno Python aislado:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
.venv/bin/python -m ruff check tools tests/python
.venv/bin/python -m ruff format --check tools tests/python
.venv/bin/python -m tools.qa.check_repository
.venv/bin/python -m pytest --cov=tools --cov-report=json:build/python-coverage.json --cov-report=term-missing
.venv/bin/python -m tools.qa.coverage_gate build/python-coverage.json
cmake --preset host-debug
cmake --build --preset host-debug --parallel 2
ctest --preset host-debug
```

Todos los presets fallan si no encuentran pruebas y limitan cada caso a 120 segundos, salvo límites específicos menores. Las pruebas Python de automatización requieren CMake/CTest en PATH. Presets adicionales: `host-release`, `host-sanitize` (ASan/UBSan) y `host-coverage` (GCC). Ejecutar `ctest` también en Release: los checks no desaparecen con `NDEBUG`. CTest incluye 224 casos: núcleo, archivos, métricas, adaptadores y observador; 64 llevan la etiqueta render, incluidos los tres visores y sus contratos. Los contratos SDK compilan código real de plataforma contra dobles controlados y no acreditan hardware ni escucha. Los tests del observador requieren C++20. La cobertura C++ usa contadores atómicos para los tests concurrentes y se obtiene con `.venv/bin/python -m gcovr --config gcovr.cfg` tras construir y probar `host-coverage`.

Para identificar el fixture propio, sin ejecutar extracción:

```sh
.venv/bin/python -m tools.pipeline.verify \
  --profile tests/fixtures/synthetic/game-profile.json \
  --data-root tests/fixtures/synthetic
```

## Inspección local de la ISO

El [procedimiento de inspección](docs/execution/europe-iso.md) genera un manifiesto con tamaños y SHA-256 de todos los archivos sin exportarlos. La copia disponible es `SLES-51434`, PAL; `VER=1.02` es el valor de arranque observado. La imagen completa coincide con Redump 1064: versión 1.02 y lista de idiomas en/fr/de/es/it. [F00.02 completada](docs/execution/f00-02-edition-identification.md). El usuario seleccionó español y Normal/Normal para la primera alpha; [F00.04 completada](docs/execution/f00-04-scope.md). Las pruebas de ejecución siguen pendientes.

## Build 3DS aislado

Para generar la escena 3D con el mismo SDK fijado, ejecutar
`bash scripts/build_render_probe.sh` dentro del contenedor. Produce
`build/render-probe/sh3_render_probe.3dsx`, ELF, SMDH, identidad e inventario con
checksums. Se exige un directorio nuevo; puede pasarse otro como primer argumento.
La CI construye y conserva ambos ejecutables de forma independiente.

El [chequeo F01.01](docs/execution/f01-01-toolchain.md) construye el ejemplo oficial en dos directorios limpios y verifica C++17 antes del build de CI. Incluye instrucciones para repetirlo montando solo scripts y fixtures propios. F01.02 ya tiene validación local y build identificados; su [prueba física](docs/compatibility/diagnostic-startup.md) sigue pendiente. F01.03 ya incorpora lectura, opciones persistentes y errores de I/O con pruebas locales; F01.04 añade validación de NDSP, PCM, contadores y liberación. F01.05 ya alcanzó breakpoints en Azahar y rechaza símbolos mezclados; conserva pendiente la consola y una anomalía gráfica tras reconectar GDB. F01.06 añade consultas de recursos, SELECT para métricas y protocolo inicial; B_app y entorno físicos siguen pendientes. F01.07 evita entrada durante suspensión, conserva pausa/mute y exige liberar botones al volver. F01.08 verifica el conjunto completo de artefactos, rechaza presets sin tests y conserva reportes/logs. El ensayo físico de treinta minutos y G01 siguen pendientes; F02.01 completó el catálogo ISO con dos informes idénticos y desconocidos explícitos. F02.02 evaluó el candidato MFA y añadió un sondeo propio: dos informes idénticos, B0/MV0 estructuralmente válidos y 60 desconocidos; [evidencia](docs/execution/f02-02-mfa-candidate.md). F02.03 añadió B8 y diagnóstico de nombres: [61 contenedores/1740 entradas estructurales](docs/execution/f02-03-container-variants.md), 493 pruebas; XBG0 conserva codificación pendiente. F02.04 completó [dos catálogos idénticos](docs/execution/f02-04-asset-catalog.md) con IDs, offsets y SHA-256 para 1740 recursos, y 582 pruebas Python aprobadas. Tipos y dependencias semánticas siguen sin inspeccionar. [F02.05](docs/execution/f02-05-repeatable-extraction.md) extrajo dos copias privadas de esos 1740 recursos, verificadas contra el catálogo; 686 pruebas Python aprobadas. [F02.06](docs/execution/f02-06-extraction-hardening.md) añadió 142 casos adversos y corrigió propiedad/cierre de descriptores y estado posterior a confirmación: 828 pruebas aprobadas. [F02.07](docs/execution/f02-07-slice-corpus.md) completó el inventario inicial: 1740 candidatos releídos en ambas copias, dos informes idénticos y 919 pruebas aprobadas. [El sondeo de cámara](docs/execution/f02-07-camera-probe.md) examinó esos 285 candidatos y registró discrepancias con SH2 en 154 archivos; dos informes idénticos y 985 pruebas aprobadas. [La búsqueda estática del ejecutable europeo](docs/execution/f02-07-camera-consumer.md) encontró dos sitios candidatos, con dos informes idénticos y 1101 pruebas aprobadas. [El seguimiento del puntero](docs/execution/f02-07-camera-pointer.md) alcanzó una referencia externa y dos fronteras de llamada, sin vínculo de recurso probado; dos informes idénticos y 1240 pruebas aprobadas. [El análisis de fronteras](docs/execution/f02-07-camera-boundary.md) distingue el argumento de A después del slot y mantiene sin demostrar los efectos de las dos llamadas de B; dos informes idénticos y 1307 pruebas aprobadas. [El plan y validador de observación](docs/execution/f02-07-camera-observation.md) añaden 128 casos propios (1435 pruebas aprobadas) y dos planes idénticos de tres fronteras/25 puntos. [PCSX2 y BIOS europea configurados](docs/execution/f02-07-ps2-boot.md), con carga del ejecutable europeo comprobada por logs. [Primera tentativa en ejecución](docs/execution/f02-07-camera-runtime-attempt.md): nueve breakpoints cargados, seis rangos de memoria coincidentes y aviso de tarjeta verificado visualmente; dos recibos sin observaciones y 128 pruebas del validador aprobadas. [Captura posterior completada](docs/execution/f02-07-camera-runtime-capture.md): nueve eventos en tres invocaciones, seis rangos coincidentes y dos recibos idénticos `validated_observations`; lector privado de estados con contrato EARS, 82 casos nuevos y 1.517 pruebas Python aprobadas. [Búsqueda exacta de recursos completada](docs/execution/f02-07-camera-resource-link.md): diez muestras, seis hits sobre un candidato de 1.536 bytes, dos informes idénticos y 1.583 pruebas Python aprobadas. [Comparación completa del candidato](docs/execution/f02-07-camera-origin.md): los 1.536 bytes coinciden en entrada A; 40 bytes ya difieren al retornar y permanecen iguales en seis estados posteriores. Dos informes idénticos y 1.649 pruebas aprobadas. [Primera escritura observada](docs/execution/f02-07-camera-writer.md): par BEQ+SW coherente con tres bytes modificados, siete estados nuevos, dos recibos idénticos y 1.720 pruebas aprobadas. La [repetición con retorno](docs/execution/f02-07-camera-return.md) añade otra sesión: mismo par BEQ+SW y retorno completo idéntico al histórico; dos recibos iguales y 1.758 pruebas aprobadas. [El contrato de mapa efectivo y su validador](docs/execution/f02-07-effective-mapping.md) pasan 91 casos nuevos (1.849 pruebas totales). macOS denegó el puerto de lectura de PCSX2 con EPERM; la captura real requiere un build instrumentado separado. [Preparación del build](docs/execution/f02-07-pcsx2-build.md): checkout fijado y fixture C++20/x86_64 aprobado; libpng/APNG x86_64 compilada con 37 pruebas aprobadas; Xcode 26.6 y Metal instalados, con compilación/ejecución C++20 y generación/enlace Metal aprobados; CMake con Apple Clang 21 avanzó hasta JPEG en esa etapa. [Primer lote de dependencias completado](docs/execution/f02-07-pcsx2-dependencies.md): NASM (301 pruebas aprobadas, una omitida), JPEG (332/332), Zstd, LZ4 y WebP x86_64 probados e instalados; la cuarta configuración alcanzó SDL3. [SDL3 3.4.12 completada](docs/execution/f02-07-pcsx2-sdl3.md): 19 controles aplicables del proveedor, un no-op identificado y cuatro casos propios aprobados antes/después de instalar; la quinta configuración supera SDL3 y alcanza FreeType. [FreeType 2.14.3 y HarfBuzz 14.2.0 completados](docs/execution/f02-07-pcsx2-fonts.md): siete casos propios pasan contra la instalación final x86_64, con fuente geométrica original y enlace privado comprobado; la sexta configuración alcanzó PlutoVG. [PlutoVG 1.3.2 y PlutoSVG 0.0.7 completados](docs/execution/f02-07-pcsx2-pluto.md): ocho casos propios pasan contra la instalación final, incluido un glifo SVG mediante FreeType; la séptima configuración supera ambos paquetes y alcanza ryml. [RapidYAML 0.12.1 completado](docs/execution/f02-07-pcsx2-rapidyaml.md): cinco casos propios y dos programas del proveedor pasan antes/después de instalar; biblioteca x86_64 y carga privada comprobadas. La octava configuración alcanza Shaderc. [Preparación de Shaderc completada](docs/execution/f02-07-pcsx2-shaderc.md): cuatro archivos verificados, parche corregido y sintaxis C/C++ comprobada; el build quedó pendiente en esa etapa. [Shaderc 2026.2 compilado y validado](docs/execution/f02-07-pcsx2-shaderc-build.md): intento acotado documentado, catorce ejecuciones CTest aprobadas y dylib privada x86_64 instalada; CMake v9 alcanza Qt 6 y también avisa de FFmpeg ausente. [Preparación de Qt Base 6.11.1](docs/execution/f02-07-pcsx2-qtbase.md): archivo y tres parches verificados, configuración x86_64 aprobada, headers generados con syncqt y fixtures preparados; build Qt pendiente de reserva IB02. [Qt Base compilado y validado](docs/execution/f02-07-pcsx2-qtbase-build.md): intento específico vigilado, ocho casos antes/después de instalar, herramientas y plugins x86_64 verificados; CMake v10 resuelve Core/Gui/Widgets y se detiene en LinguistTools. [Qt SVG compilado y validado](docs/execution/f02-07-pcsx2-qt-svg.md): seis casos antes/después de instalar, renderer y plugins de imágenes/iconos comprobados; cuatro binarios x86_64 y prefijo anterior intacto. CMake v11 sigue en LinguistTools. [Qt imageformats compilado y validado](docs/execution/f02-07-pcsx2-qt-imageformats.md): 16 ejecuciones CTest aprobadas, WebP/TGA/WBMP/TIFF y carga privada comprobados; siete plugins x86_64 instalados, tres solo verificados estructuralmente. CMake v12 sigue en LinguistTools. [Qt Tools/LinguistTools compilado y validado](docs/execution/f02-07-pcsx2-qt-tools.md): 16 ejecuciones CTest aprobadas, traducciones/UiTools y herramientas privadas verificadas; ocho ejecutables, tres dylibs y un objeto instalados. CMake v13 supera LinguistTools y alcanza KDDockWidgets. [Qt translations generado e instalado](docs/execution/f02-07-pcsx2-qt-translations.md): 304 QM repetibles, 4.502 mensajes españoles contrastados y diez ejecuciones CTest aprobadas; prefijo preservado. CMake v14 sigue en KDDockWidgets. [QtApng corregido, compilado e instalado](docs/execution/f02-07-pcsx2-qt-apng.md): 18 ejecuciones CTest finales y ocho trazas aprobadas; composición, QMovie y errores verificados, fallos históricos conservados. Plugin privado x86_64 y prefijo intactos. CMake v15 sigue en KDDockWidgets. [KDDockWidgets 2.4.1 completado](docs/execution/f02-07-pcsx2-kddockwidgets.md): 16 ejecuciones CTest finales y seis trazas aprobadas; paneles y persistencia verificados. Se corrigió una cabecera omitida por la instalación sin cambiar C++ ni tests originales. Prefijo conservado; CMake v16 resuelve KDDockWidgets y alcanza FFmpeg. [FFmpeg 8.1 compilado e instalado](docs/execution/f02-07-pcsx2-ffmpeg.md): cinco bibliotecas x86_64, 22 ejecuciones CTest finales, diez trazas y cuatro negativos de configuración aprobados; originales y prefijo conservados. CMake v17 configura y genera PCSX2 con FFmpeg resuelto; persiste el aviso de MoltenVK ausente. [MoltenVK 1.4.1 compilado e instalado](docs/execution/f02-07-pcsx2-moltenvk.md): 25 archivos de receta y siete revisiones transitivas verificados, 16 ejecuciones CTest finales, diez trazas y siete pruebas de capacidad aprobadas; transferencia/cómputo/lectura de imagen GPU contrastados en Apple M2. CMake v18 encuentra MoltenVK y el gate queda listo con 21,47 GiB al cierre. [Baseline PCSX2 compilado y validado](docs/execution/f02-07-pcsx2-baseline.md): 113 tests originales aprobados, paquete local con 42 binarios auditados, depurador observado y cierre limpio; 1.920 pruebas Python. Firma/ID/RPATH corregidos en copias conservando originales. Se verificó la reserva inicial tras liberar espacio; debe reevaluarse antes de builds grandes. 1.920 pruebas Python en el cierre del baseline. Otros escritores, cargador, tipo y salas permanecen pendientes. XBG0, AFS, semántica/corpus y G02 siguen pendientes.

Docker debe estar iniciado. La imagen está fijada por digest; no hace falta instalar devkitARM globalmente:

```sh
image=$(cat toolchains/devkitpro-image.txt)
docker pull "$image"
docker run --rm --network none --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$PWD,dst=/work" -w /work \
  "$image" bash scripts/build_3ds.sh
```

Salida: `build/3ds/sh3_diagnostic.3dsx`, ELF con símbolos, SMDH, `probe.txt`, `build-id.txt`, `debug-bundle.json`, checksums, inventario de paquetes y `artifact-check.json`. El recibo exige los ocho archivos regulares/no vacíos, fixture/ID/checksums coherentes y cabeceras básicas; no acredita ejecución. El manifiesto vincula ELF/3DSX por SHA-256; se rechaza reutilizar una carpeta que ya contiene evidencia registrada. Conservar el build anterior y usar una copia limpia para el siguiente. En una instalación devkitPro nativa verificada se puede ejecutar directamente `bash scripts/build_3ds.sh`.

El diagnóstico usa figuras sintéticas y un tono PCM propio. `A` pausa/reanuda; `START` sale; `SELECT` alterna audio/archivos y recursos. `X` cambia y guarda el tono; `Y` restaura y guarda su valor predeterminado. Se muestran build ID, estado/etapa/Result de audio, contadores SDK y estados Probe/Load/Save. Después de suspensión o combinaciones bloqueadas, soltar todos los botones antes de una nueva acción; el aviso indica cuándo hacerlo. La escucha permanece NOT_VERIFIED hasta registrarla en la prueba física. No contiene assets del juego. Su compilación no demuestra ejecución, audio o estabilidad en consola.

Para la prueba manual actual, copiar el `.3dsx` y `probe.txt` a `/3ds/sh3_diagnostic/` de la SD y abrirlo con Homebrew Launcher. El build actual está identificado en el [informe F01.08](docs/execution/f01-08-builds.md); seguir el [ensayo de treinta minutos](docs/compatibility/diagnostic-soak.md), la [guía de ciclo de vida](docs/compatibility/lifecycle-probe.md), la [guía de recursos](docs/compatibility/resource-probe.md) y la [guía de depuración](docs/compatibility/debugging.md). La [guía de audio](docs/compatibility/audio-probe.md) conserva la identidad de F01.04: registrar el ID/hash nuevo al repetirla. La [guía de archivos/opciones](docs/compatibility/file-probe.md) conserva su build histórico; si se repite con el actual, registrar su nueva identidad. El programa escribe solo `options-a.dat` y `options-b.dat` en esa carpeta. La prueba de arranque de F01.02 sigue pendiente. FBI corresponde a una futura ruta CIA independiente; esta iteración no produce CIA.


[Observador interno preparado](docs/execution/f02-07-pcsx2-observer.md): contrato EARS,
núcleo/adaptador propios y parche privado optativo; siete objetos compilados
con headers reales. 2.027 pruebas Python y 49 CTest en Release y ASan/UBSan
aprobadas. [Build instrumentado validado](docs/execution/f02-07-pcsx2-observer-build.md):
113 tests originales, 2.072 Python y 39 casos PINE reales sin juego aprobados;
fallo SIGPIPE corregido, firma/ID/RPATH comprobados y cierre limpio con lectura
pendiente.

[Coordinador de adquisición implementado](docs/execution/f02-07-observer-acquisition.md):
conexión persistente, estado con ciclo u64, comparación de memoria/PC/CRC,
custodia privada y publicación atómica; 124 pruebas nuevas y 2.196 totales
aprobadas. El candidato exacto rechaza una sesión sin juego sin generar
estados ni recibos de aceptación.

[Sesión real MP08 completada](docs/execution/f02-07-observer-live.md): arranque
nuevo desde la ISO europea y cuatro capturas con mapa/estado/PINE coherentes;
respaldo coincidente entre las cuatro pausas y dos reimportaciones idénticas.
La entrada conserva los 1.536 bytes del candidato, el paso modifica 3 bytes y
el retorno reproduce los 40 bytes cambiados del histórico. AC11 admite la cola
variable del estado con un presupuesto explícito y mantiene intacto el lector
histórico. 37 pruebas nuevas, 2.233 totales aprobadas.

[Escrituras restantes conciliadas](docs/execution/f02-07-remaining-writers.md):
66 capturas nuevas desde una copia de la entrada SRC53, 32 pares SW y dos
reimportaciones idénticas reconstruyen los 1.536 bytes del retorno y explican
sus 40 bytes modificados. Un primer intento incompleto por plazo se conserva
rechazado. 54 casos nuevos, 2.287 pruebas Python aprobadas. Sigue
`origin/load-provenance`.

[Origen y modelo de carga preparados](docs/execution/f02-07-load-provenance-plan.md):
ISO/MFA y ambas extracciones coinciden con el candidato; 86 registros del
estado concuerdan con el índice. Modelo puro de lectura/copia/entrega con
78 casos nuevos y 2.365 pruebas Python aprobadas. Anclaje y seguimiento
estático generan dos informes idénticos cada uno. Sigue el adaptador de
evidencia y la captura anterior a la carga; procedencia real, semántica,
dos salas y port jugable continúan pendientes.

[Fronteras de carga y validadores multirrango](docs/execution/f02-07-load-frontier.md):
LP-C distingue rutas estáticas de destino directo y caché; comprueba mapas de
código/datos, argumentos y retorno de una llamada. 68 casos nuevos y 2.433
pruebas Python aprobadas. Sigue vincular el descriptor activo al archivo y
adquirir la ruta usada; una transferencia coherente aún no demuestra lectura.

[Generación de descriptores y adquisición multirrango](docs/execution/f02-07-descriptor-acquisition.md):
se rechazan descriptores cerrados o reciclados y se coordinan hasta ocho rangos
contra un único estado guardado. Nueve ventanas estáticas coincidentes y dos
informes iguales; 103 casos nuevos y 2.536 pruebas Python aprobadas. Sigue
vincular la apertura y selección de catálogo con el archivo activo antes de
la captura real de carga.

[Selección de catálogo y apertura](docs/execution/f02-07-catalog-open.md):
una entrada de 1.704 coincide con el origen ISO/MFA; nueve ventanas de código
y dos informes repetibles fijan el plan. Adaptador de cuatro pausas con 96
casos nuevos y 2.632 pruebas Python aprobadas. Sigue identificar el objeto
del driver, su posición y la ruta de lectura/caché antes de la captura real.

[Objeto del driver, despacho y posición](docs/execution/f02-07-driver-transfer.md):
14 ventanas estáticas y dos informes iguales fijan el perfil; los 16 objetos
del estado conservado están cerrados. Dos validadores puros con 99 casos nuevos
y 2.731 pruebas Python aprobadas contrastan generación, posición, retorno y
payload sin certificar una lectura. Siguen el puente con la apertura, identidad
del backend, origen de caché y captura real.

[Apertura y objeto del driver](docs/execution/f02-07-open-driver.md):
validador de tres pausas/24 rangos, con 63 casos nuevos y 2.794 pruebas Python
aprobadas. Comprueba los extremos y rechaza por defecto una continuidad aún
no demostrada. Dos análisis estáticos idénticos; siguen backend/sector, copia,
perfil conjunto de catálogo y captura real.

[Referencia backend, archivo y sector](docs/execution/f02-07-backend-sector.md):
cadena de descriptores contrastada con la extensión ISO, con 19 ventanas y dos
análisis iguales. Validador de una pausa/ocho rangos, 87 casos nuevos y 2.881
pruebas Python aprobadas. Sigue comprobar finalización, llenado del buffer,
copia al destino y continuidad mediante captura real.

[Finalización backend y buffer](docs/execution/f02-07-backend-completion.md):
contrato de tres pausas/24 rangos que comprueba aceptación, éxito, cantidad
completada y hashes del sector y recurso. Incluye 95 casos nuevos, 2.976 pruebas
Python aprobadas y dos análisis estáticos iguales. Un buffer preexistente no acredita lectura nueva;
siguen copia al destino, perfil conjunto y continuidad mediante captura real.

[Copia de buffer y retorno del driver](docs/execution/f02-07-buffer-copy.md):
validador de siete pausas/56 rangos, con 71 casos nuevos y 3.047 pruebas Python
aprobadas. Comprueba retornos,
fuente, destino y cantidades; mantiene pendientes ejecución real y continuidad.
Sigue integrar apertura, resolver progreso temprano y preparar la captura conjunta.

[Catálogo, apertura y recorrido conjunto](docs/execution/f02-07-joint-open-read.md):
once pausas/81 rangos enlazan apertura y copia sin recodificar evidencias. Incluye
49 pruebas propias y 3.096 pruebas Python aprobadas; rechaza continuidad no demostrada por defecto y permite un
diagnóstico explícito sin generar `Read`. Siguen observación de continuidad,
progreso temprano del worker y descubrimiento para la captura real.

[Núcleo de guardia de continuidad](docs/execution/f02-07-lifetime-guard.md):
contrato LG01–LG08 y núcleo C++17 que invalida escrituras protegidas, reciclaje,
huecos y restauraciones. Once escenarios nuevos; 60 pruebas host pasan en Debug,
Release y ASan/UBSan, con cobertura del núcleo del 100 % en líneas y ramas.
3.096 pruebas Python aprobadas y dos análisis estáticos iguales. La integración
de escritores y ciclo de vida de PCSX2 sigue pendiente; aún no acredita continuidad.

[Primer lote de productores VTLB](docs/execution/f02-07-physical-write-probe.md):
cuatro rutas de escritura instrumentadas en una copia privada, con ocho hooks.
Cuatro unidades reales PCSX2 x86_64 compiladas; 26 casos de funciones del proveedor
pasan con ON, OFF y sanitizadores usando memoria propia y dobles explícitos.
67 pruebas host por configuración, 3.096 Python y cobertura del puente del 100 %.
Siguen DMA, JIT/caché y ciclo de vida antes de habilitar continuidad real.

[Segundo lote: productores DMA](docs/execution/f02-07-dma-write-probe.md):
diez puntos de aviso en SPR/MFIFO/SIF/IPU y rechazo conservador del retorno GS.
26 unidades reales compiladas ON/OFF y 54 casos por modalidad ON/OFF/sanitizadores,
con los mismos efectos comprobados. LG-I1 sigue parcial; la siguiente unidad
es JIT/caché. La sincronización global, ciclo de vida y captura real siguen pendientes.

[Caché y barrera de entrada JIT](docs/execution/f02-07-jit-cache-probe.md):
devoluciones físicas de líneas observadas y rechazo conservador de escrituras
lógicas, mantenimiento y entrada JIT. Diez unidades ON/OFF y 70 casos por modalidad
ON/OFF/sanitizadores aprobados. JIT generado y armado durante ejecución siguen
sin cobertura; la siguiente unidad es escritores host, antes de época y admisión.

[Productores host](docs/execution/f02-07-host-write-probe.md): nueve puntos nuevos
en arranque y funciones auxiliares, conservando las hojas compartidas de
depurador/PINE/parches. Dieciséis objetos ON/OFF y 85 casos por modalidad,
incluida la copia anterior, con efectos equivalentes. Siguiente: ciclo de vida,
época y exclusión de escritores antes de admitir captura.

[Barrera cooperativa de PINE](docs/execution/f02-07-pine-exclusion.md): reservas
que siguen solicitudes y callbacks, incluso tras respuesta o timeout. Cierre
consultable con rechazo de nuevas entradas, cancelación y drenaje. Cinco objetos,
44 casos comunes en cuatro modos y trece casos adicionales ON/sanitizadores.
Pendiente integrar el coordinador CPU y GS/VU; no habilita captura real.

[Diagnóstico de admisión](docs/execution/f02-07-admission-profile.md): evaluador
de 18 condiciones y sampler interno del proveedor, con incompatibilidades y
desconocidos separados. Comprueba hilo CPU, reentrada, configuración y punteros;
PINE/GS/VU y otros escritores siguen sin exclusión demostrada. 34 escenarios en
cuatro modos y cuatro objetos ON/OFF. No habilita captura ni admite una VM.

[Ciclo de vida y época host](docs/execution/f02-07-lifecycle-probe.md): contador
no restaurable y 24 puntos de invalidación en reset, carga, remapeo, configuración
y cierre. Diez objetos reales, 54 escenarios por modalidad y ocho pruebas nuevas
del núcleo. Siguiente: admisión con exclusión de CPU/trabajos/PINE y validación de VM.

[Frontera CPU explícita](docs/execution/f02-07-cpu-boundary.md): el diagnóstico
exige una iteración exterior sin actividad ni reentrada. Despacho Qt y catorce
entradas VM revocan la frontera hasta la siguiente iteración. Cuatro objetos
ON/OFF, 45 casos comunes por modalidad y cinco adicionales ON/sanitizadores;
100 pruebas CTest por configuración. Sigue la coordinación PINE y el drenaje
GS/VU antes de habilitar captura real.

[Coordinación de drenaje PINE](docs/execution/f02-07-pine-coordinator.md): cierre
retenido entre iteraciones CPU, callbacks sin Execute durante drenaje y cancelación
por plazo/cambio de épocas. Seis objetos ON/OFF, 110 CTest por preset y probe con
QtCore real. La API sigue interna; quedan servidor completo, GS/VU y captura real.

[Productores y dependencias VU/GS](docs/execution/f02-07-worker-producers.md):
matriz de catorce familias, entrada UI directa a GS y esperas VU↔GS. Cinco pruebas
aisladas en normal/sanitizadores confirman que cola vacía no concede exclusión.
CQ3-A completada; sigue implementar cierre de productores y acuses de trabajadores.

[Propietario persistente del intento](docs/execution/f02-07-retained-drain.md):
PINE permanece cerrado hasta liberar la fase posterior. Diez escenarios nuevos,
120 CTest por preset, cuatro objetos ON/OFF y 26 casos adicionales con cuerpos
del proveedor. La fase GS/VU se rechaza hasta implementar sus barreras; sigue B2.

[Entradas productoras CPU](docs/execution/f02-07-producer-entry.md): 38 avisos antes
de efectos y cambio de idioma por CPU→GS. Seis objetos ON/OFF y 110 casos comunes
más seis de idioma en cuatro modos. B2 completada; sigue B3, eventos Qt restantes
y canal de control. GS/VU continúa rechazado hasta demostrar sus retenciones.

[Entradas y bombeo Qt](docs/execution/f02-07-qt-dispatch.md): B3-A completada con
48 avisos previos a efectos/despacho y 112 escenarios por modo con QtCore real.
Cancelar antes de Qt protege el intento; el drenaje real continúa pendiente.

[Canal CPU↔worker](docs/execution/f02-07-worker-control.md): B3-B1 y núcleo de
B3-B2 completos, con identidad, cancelación, acuses y avisos fuera de la cola de
datos. 138 CTest por configuración, diez escenarios TSan y tres controles
negativos. Sigue B3-B3: fijar los puntos reales VU/GS y sus esperas para integrar
el canal. El puerto productivo permanece rechazado hasta demostrar retención.

[Fronteras y despertar VU/GS](docs/execution/f02-07-worker-boundary.md): B3-B3a/b
definidas y puente de despertar probado con WorkSema real, semáforo doble y Mach.
57 ejecuciones normal/ASan-UBSan/TSan y tres negativos detectados. Sigue integrar
VU en una copia nueva y probar su bucle real; GS y captura permanecen pendientes.

[Retención MTVU integrada](docs/execution/f02-07-vu-control.md): IW-VU1–3
completadas en una copia privada corregida, con cancelación CPU y reconsulta de
cola antes del acuse. 45 ejecuciones finales con Mach y sanitizadores, seis
objetos ON/OFF y cinco negativos. El bucle MTVU usa efectos dobles en estas
pruebas; siguen GS, coordinación global y validación de la VM completa.

[Retención MTGS integrada](docs/execution/f02-07-gs-control.md): IW-GS1–3
completadas, con generación por apertura exitosa, señales antes del acuse y mutex
liberado durante held. Pasan 63 ejecuciones GS y 45 de regresión VU con sanitizadores,
seis objetos ON/OFF y seis negativos. Sigue el coordinador VU→GS; los efectos y
el worker contraparte de estos probes son dobles y la captura global sigue pendiente.

## CI y mantenimiento

[GitHub Actions](.github/workflows/ci.yml) configura calidad Python, arquitectura y trazabilidad, tests host Linux/macOS, sanitizadores, cobertura y compilación 3DS. Selecciona artefactos de desarrollo sintéticos y reportes; no crea releases. La ejecución remota está pendiente. Antes de compartir los binarios debe completarse su revisión de avisos y fuentes [LIC07](docs/compatibility/licenses.md), también cuando procedan de CI.

Conservar dependencias fijadas y un test por regresión. Cada cambio de herramientas, esquema, contrato o receta requiere repetir las pruebas afectadas. La CI no necesita originales. La ISO local de `binaries` y los informes de `reports/local` están excluidos de Git; las extracciones siguen en un directorio externo.

[Coordinador conjunto VU/GS](docs/execution/f02-07-worker-coordinator.md):
IW-COORD1–3 incorpora retención VU→GS, retiro GS→VU e identidad por intento/sesión.
154 CTest por preset, 60 ejecuciones de los bucles conjuntos con sanitizadores y
QtCore, ocho objetos ON/OFF y seis controles negativos. Sigue la validación del
frontend completo; admisión vacía y captura global deshabilitada.

[Frontend y enlace completo](docs/execution/f02-07-worker-frontend.md): nuevo
candidato privado compilado/enlazado, 113 tests originales y testconfig aprobados.
Pruebas entre hilos Qt con TSan instrumentado; una espera circular se recupera
por deadline y requiere cancelación prioritaria. Sin VM ni captura nueva.

[Cancelación ante esperas externas](docs/execution/f02-07-external-waits.md):
CPU retira el intento antes de atender una llamada bloqueante; conserva payload,
retorno y scopes concurrentes. 160 CTest por preset, 24 casos Qt con sanitizadores,
cinco negativos y nuevo build completo con 113 tests originales/testconfig.
Continúan pendientes dependencias de callbacks, PINE conjunto y VM.

[Llamadores y dependencias](docs/execution/f02-07-blocking-callers.md):
106 llamadas clasificadas y seis ensayos con mutex real. Retirar el observador
no garantiza progreso de un callback con otras esperas; siguen PINE conjunto,
locks/backend y VM. No se modifica el proveedor ni se amplía admisión.

[Servidor PINE conjunto](docs/execution/f02-07-pine-joint.md): 63 pruebas finales
con sanitizadores, tres controles negativos y dos objetos ON/OFF. Corrige
alineación, cierre concurrente y mensajes consecutivos; veintidós copias
preservadas. El [enlace SRC88](docs/execution/f02-07-pine-link.md) está completado: 113 tests
originales, firma del candidato y testconfig aprobados. No inicia VM ni habilita
capturas del juego.


[RDebug en el candidato](docs/execution/f02-07-rdebug-artifact.md): auditoría de
403 objetos, 19 archivos estáticos, 806 dependencias y 42 binarios, con siete
controles negativos. La evidencia está ligada al artefacto; falta vincularla al
proceso y completar el perfil de diagnóstico antes de habilitar capturas.

[Identidad y diagnóstico](docs/execution/f02-07-process-diagnostic.md): inventario
del proveedor, matriz de dieciocho condiciones y consumidor con 87 pruebas.
Detecta cambios o pérdida de identidad y descarta el diagnóstico permanentemente.
El adaptador nativo que vincule el proceso real continúa pendiente; las pruebas
del consumidor usan dobles y no habilitan captura ni cambian el perfil productivo.

[Nacimiento nativo del proveedor](docs/execution/f02-07-native-birth.md): adaptador
macOS con PID/nacimiento del sistema y nonce propio. 88 ensayos finales, incluidos
exec/fork reales, tres controles negativos y pipeline host dedicado. Falta ligar
esta clave a las imágenes cargadas y al canal de PCSX2; la admisión sigue cerrada.

[Mappings y eventos nativos](docs/execution/f02-07-native-images.md): vínculo de
archivo con región del kernel y registro de cargas/descargas, probado con
reemplazos reales. IP-NATIVE2 sigue abierto por manifiesto/digests y evidencia de
caché del sistema; no habilita capturas.

[Manifiesto nativo de archivos](docs/execution/f02-07-native-manifest.md): hashes
desde descriptores retenidos y dos pasadas del manifiesto; 42 binarios conservados
comprobados. Caché/AOT y composición del inventario siguen pendientes.

[Composición del inventario](docs/execution/f02-07-native-inventory.md): combina
nacimiento, manifiesto, mappings y revisión del cargador; rechaza todo el conjunto
si una imagen carece de evidencia. 476 ejecuciones finales y tres controles
negativos. La caché del sistema y AOT siguen pendientes; las pruebas positivas
usan bibliotecas propias y no habilitan la ejecución del port.

[Vínculo de páginas de caché](docs/execution/f02-07-native-pages.md): la consulta
del kernel relaciona puntos de las catorce partes x86_64/AOT y 44 bibliotecas con
archivos retenidos. 576 ejecuciones finales y cuatro negativos. Falta verificar
integridad y cobertura completa de la caché antes de integrar el proveedor.

[Integridad y rangos de caché](docs/execution/f02-07-native-cache-integrity.md):
hashes completos de catorce archivos y recorrido exhaustivo de rangos declarados,
con políticas de tamaño separadas del bundle. 664 ejecuciones y cuatro regresiones
detectadas. Una segunda sonda verificó el manifiesto local fijado; falta integrar
la cobertura de todos los segmentos del candidato y acotar la revalidación.

[Inventario de segmentos del candidato](docs/execution/f02-07-native-layout.md):
645 imágenes y 3020 segmentos enumerados en una copia privada de diagnóstico,
con revisión estable del cargador. Se amplió el inventario a 1024 imágenes sin
cambiar los límites de archivos del bundle. 756 ejecuciones y cuatro regresiones
detectadas; falta acreditar los objetos de datos transformados y todos los rangos.

[Unión de intervalos y dependencias](docs/execution/f02-07-native-range-plan.md):
el planificador conserva los 3020 segmentos del censo en 2442 intervalos disjuntos,
sin sumar aliases: 2550806551 bytes virtuales únicos. 820 ejecuciones y cuatro
regresiones detectadas. Incluye clasificación zero-fill, conflictos y límites;
siguen pendientes el origen de páginas transformadas y la enumeración AOT real.

[Mapa virtual y cobertura AOT](docs/execution/f02-07-native-region-map.md):
enumeración desde cero con dos pasadas, límites y rechazo de cambios. 880
ejecuciones finales y cuatro regresiones detectadas. El diagnóstico localiza
caché AOT y traducciones individuales fuera de los segmentos Mach-O, incluido
dyld, y un heap ejecutable de Rosetta. Falta acreditar su origen e integrar la
verificación de páginas con un coste de revalidación acotado.

[Asociación puntual de región y archivo](docs/execution/f02-07-native-region-vnode.md):
912 ejecuciones y cuatro regresiones detectadas. Las 24/27 traducciones AOT
observadas tienen vnode, pero sus archivos devuelven EPERM y no hay descriptores
retenibles en esas fases. La API de nombres puede apuntar a otro mapping y se
excluye como prueba de origen. La [dirección de confianza en la plataforma](docs/execution/f02-07-platform-trust-decision.md)
se desarrolla mediante un perfil separado; captura y admisión permanecen cerradas.

[Perfil de aplicación con plataforma asumida](docs/execution/f02-07-platform-inventory.md):
núcleo PT con tipos, evidencias y hashes propios; 1016 ejecuciones en cuatro
configuraciones, cuatro regresiones detectadas y 122 pruebas Python. Una sonda
aislada clasifica 343 de 345 cabeceras por membresía exacta en la caché de dyld
y rechaza una biblioteca que imita el nombre de otra del sistema. Sigue PT-T3:
adaptador nativo y validación dentro del candidato PCSX2. El perfil aún no está
integrado y no acredita páginas AOT ni permite captura.

[Origen nativo del perfil PT](docs/execution/f02-07-platform-origin.md): adaptador
implementado con 1096 ejecuciones, cuatro regresiones detectadas y 122 pruebas
Python. Clasifica las 557 cabeceras del arranque de PCSX2; rechaza la salida por
el mapping de `libobjc-trampolines.dylib`, cuyo slice x86_64 empieza en offset
16384. Sigue PO-T3b: contrato y vinculación de slices Mach-O universales.
Este límite queda resuelto en [Slices Mach-O y PT v2](docs/execution/f02-07-macho-slices.md):
parser y vínculo nativo con perfil explícito; 1216 ejecuciones C++, cuatro regresiones
detectadas y 153 Python. Testconfig clasifica 557 cabeceras al inicio y 647 al
cerrar, incluido el slice universal a offset 16384. PT-T3 completo; sigue PT-T4,
manifiesto esperado y medición de costes.

[Manifiesto previo y composición PT v2](docs/execution/f02-07-launch-manifest.md)
completa PT-T4: 26 archivos fijados antes de lanzar, seis muestras positivas y
cuatro controles de rechazo en PCSX2. 1292 ejecuciones C++ y 153 Python correctas.
Cada muestra relee 215,10 MiB y tarda 832–875 ms en la ejecución medida. Sigue
PT-T5: diagnóstico/peer y presupuesto con cancelación. La captura sigue deshabilitada.

[Diagnóstico tipado PT v2](docs/execution/f02-07-platform-diagnostic.md) completa
PT-T5a: mensajes acotados, evidencias locales y consumidor separado de IP.
1328 ejecuciones C++, 230 Python y seis mensajes de una copia testconfig validados.
Sigue PT-T5b: autenticar peer y vincular la sesión; después deadline/cancelación.
El codec no autentica el canal ni habilita captura.

[Peer y sesión de diagnóstico](docs/execution/f02-07-diagnostic-peer.md) completa
PT-T5b: identidad nativa del canal y rechazo terminal de replay/cambios/pérdidas.
1356 ejecuciones C++, 335 Python y nueve testconfig privados verificados. Sigue
PT-T5c: presupuesto total, cancelación fuera del hilo CPU y gates del emulador;
la captura sigue cerrada.

[Ejecutor de diagnóstico](docs/execution/f02-07-diagnostic-worker.md) completa
DW-T1 / PT-T5c.1: presupuesto único de 5 s/2 s, cancelación cooperativa y cierre
confirmado después de terminar el trabajador. 1456 ejecuciones x86_64, 24 con
ThreadSanitizer arm64 y seis regresiones detectadas. Sigue DW-T2: integrar los
adaptadores nativos y comprobarlos en PCSX2; la captura permanece deshabilitada.

[Inventario nativo con presupuesto](docs/execution/f02-07-native-diagnostic-work.md)
completa NW-T1–2 / DW-T2a–b: preparación, lectura/hash y cierre en el trabajador.
1504 ejecuciones C++ finales, cuatro regresiones detectadas y nueve casos privados
finales de PCSX2 sin VM. Sigue NW-T3 / DW-T2c, presupuesto del canal; después
DW-T3, guardias runtime. DW-T2 sigue abierto y la captura deshabilitada.

[Consumidor con plazo total](docs/execution/f02-07-budgeted-consumer.md) completa
BC-T1 / NW-T3a: 5 s/2 s desde peer hasta admisión, IO no bloqueante y cancelación
señalada al dueño. 384 pruebas Python, cuatro regresiones detectadas y ocho
escenarios de procesos nativos con payload sintético. Siguen NW-T3b, productor,
y NW-T3c, sonda conjunta PCSX2. Captura deshabilitada.

[Entrega del productor](docs/execution/f02-07-worker-delivery.md) completa
WD-T1 / NW-T3b: el plazo sigue activo hasta confirmar el envío, con escrituras
parciales y cierre del canal por su dueño. Pasan 1608 ejecuciones C++, 41 TSan
y cinco controles de regresión. Sigue NW-T3c, composición privada PCSX2.
La captura continúa deshabilitada.

[Composición privada](docs/execution/f02-07-diagnostic-composition.md) completa
NW-T3 / DW-T2: 20 casos finales de PCSX2 sin VM y diez muestras de inventario
aceptadas, con plazos por extremo, backpressure, fallos y cierres verificados.
Se conserva un intento rechazado antes de alcanzar su inyección. Sigue DW-T3,
integración de guardias runtime; la captura continúa deshabilitada.


[Vinculación runtime revocable](docs/execution/f02-07-runtime-diagnostic-binding.md)
completa RB-T1 / DW-T3a: el trabajador invalida muestras y entregas al retirar su
alcance, incluso mientras espera ocioso. Pasan 1712 ejecuciones finales, 67 TSan
y ocho controles negativos. Sigue RB-T2, conexión con el coordinador privado;
la VM y la captura todavía no se validan con esta vinculación.

[Coordinador runtime privado](docs/execution/f02-07-runtime-coordinator.md) completa
RB-T2 / DW-T3b: conserva guardias CPU/PINE/VU/GS y revoca antes de las transiciones
cubiertas. Pasan 108 pruebas privadas, 1.820 nativas, 94 TSan adicionales y diez
controles negativos; se compilan unidades completas ON/OFF. Sigue RB-T3, enlace
y validación con VM. DW-T3 y captura permanecen pendientes.

[Entrega asíncrona IO–CPU](docs/execution/f02-07-runtime-handoff.md) completa
RB-T3a: el callback conserva el plazo original, rechaza intentos tardíos y confirma
liberación antes de unir DW. Pasan 1.900 pruebas nativas, 148 de integración,
114 TSan adicionales y seis negativos. Sigue RB-T3b: socket/inventario nativo,
candidato enlazado y VM. RB-T3, DW-T3 y captura siguen pendientes.

[Sesión runtime y socket](docs/execution/f02-07-runtime-session.md) completa
RS-T1/RS-T2: vínculo exacto con DW, recepción macOS autenticada, plazos acumulados
y cierre después de retirada CPU. Agrega 42 escenarios al pipeline nativo.
Sigue RS-T3: launcher/inventario nativo válido, candidato enlazado y VM.
RB-T3, DW-T3 y captura permanecen pendientes.

[Composición nativa con runtime](docs/execution/f02-07-native-runtime-composition.md)
completa RS-T3a sin VM: 17 controles alcanzados y 11 muestras con inventario
nativo real. El último control requiere traza del loader; se conservan los
rechazos previos. Host/CPU siguen siendo dobles. Sigue RS-T3b: integración real,
candidato enlazado y validación con VM; la captura permanece pendiente.

[Servicio del candidato enlazado](docs/execution/f02-07-runtime-service.md)
completa RT-T1/RT-T2: integra IO con Host/VMManager reales, construye un candidato
firmado y repara su cierre. La ISO europea inicializa una VM pausada; el inventario
rechaza su preflight y el candidato final sale correctamente. La siguiente tarea
es diagnosticar ese rechazo. Aún no hay muestras aceptadas ni captura habilitada.

[SRC118 — Diagnóstico del preflight](docs/execution/f02-07-native-preflight.md)
completa RT-T3a: el registro se invalida ante un alta con sus 1.024 entradas
ocupadas. Pasan 198 regresiones; dos repeticiones confirman la misma causa y
cierre correcto. Falta medir la demanda completa y corregir capacidad con
presupuesto explícito; no hay inventario válido ni muestras aceptadas.

[SRC119 — Censo independiente](docs/execution/f02-07-native-census.md) completa
RT-T3b.1: el alta 1.025 es nueva y las repeticiones miden 1.067 módulos sin VM y
1.069 con VM pausada. Pasan 186 casos nativos y 27 TSan. Se propone evaluar
2.048 entradas con tamaños ABI medidos; faltan presupuesto de pila/plazo,
ajuste coordinado del contrato y validación positiva. El límite sigue en 1.024
y la captura permanece pendiente. El harness final añade 80 ejecuciones de
portabilidad en GCC/Clang y sanitizadores locales.

[SRC120 — Capacidad y almacenamiento](docs/execution/f02-07-image-capacity.md)
completa RT-T3b.2 en fuentes y pruebas: 2.048 entradas, buffers propios fuera
de pila y protocolo PD v2 coordinado con Python. Pasan 2.224 ejecuciones nativas,
48 TSan, seis GCC y 304 Python. Sigue RT-T3b.3: reconstruir los 128 objetos
afectados del candidato y verificar muestras positivas con VM y sus plazos.
El candidato anterior conserva sus bytes; la captura permanece pendiente.

[SRC121 — Candidato y componentes del host](docs/execution/f02-07-capacity-candidate.md)
reconstruye los 128 objetos afectados y verifica 390 miembros estáticos. El
manifiesto fija tres componentes Apple fuera de la caché; dos perfiles aceptan
dos muestras PD v2 cada uno. Pasan 304 pruebas Python. El cierre inmediato del
productor impide aceptar la tercera respuesta y mantiene RT-T3b.3 abierto;
la captura continúa pendiente.

[SRC122 — Liberación de la última respuesta](docs/execution/f02-07-service-release.md)
completa RT-T3b/RT-T3b.3: el productor espera el medio cierre autenticado del
consumidor y dos perfiles de confirmación aceptan tres respuestas cada uno.
Pasan 433 ejecuciones nativas, 304 Python y 58 de repositorio/supervisor.
Se conserva un intento que agotó el plazo global; el margen bajo carga sigue
pendiente. Continúa RT-T3c: cancelación/callbacks tardíos, coste del inventario
y validación independiente de escritores y ciclo de vida. Captura aún cerrada.

[SRC123 — Abandono del consumidor](docs/execution/f02-07-peer-exit.md) completa
RT-T3c.1a: ocho perfiles con VM verifican cierre antes de pedir datos, tras la
primera o tercera respuesta y rechazo de bytes adicionales. Todos terminan
limpiamente con el motivo esperado; pasan 58 pruebas de repositorio/supervisor.
El candidato se conserva sin recompilar. Siguen cancelación UI, callbacks
tardíos, margen temporal y gates de escritores.

[SRC124 — Cancelación desde la interfaz](docs/execution/f02-07-ui-cancel.md)
completa RT-T3c.1b.UI: doce perfiles observados y dos acciones visibles en el
candidato sin sonda cancelan limpiamente; IO se une antes de detener CPU.
El control normal conserva las tres respuestas. Pasan 445 ejecuciones nativas
y 58 de repositorio/supervisor. Siguen entrega parcial, Apagar VM, callbacks
tardíos, margen temporal y gates de captura.

[SRC125 — Cancelación durante entrega parcial](docs/execution/f02-07-partial-cancel.md)
completa RT-T3c.1b.partial-delivery: la señal de UI se consulta dentro del envío.
Ocho perfiles con prefijos de 1/293 bytes y contrapresión inyectada rechazan el
frame incompleto y cierran ordenadamente; el control sin sonda conserva tres
respuestas. Pasan 453 nativas y 58 de repositorio/supervisor. Siguen Apagar VM,
callbacks reales, margen temporal y gates; no se habilita captura.

[SRC126 — Apagar VM y confirmación](docs/execution/f02-07-vm-shutdown.md) completa
RT-T3c.1b: No conserva la VM y su estado de pausa; Sí vuelve a la lista de juegos
con PCSX2 abierto. Pasan dieciséis perfiles Qt, el contraste CUA sin sonda,
el control normal de tres respuestas, 465 ejecuciones nativas y 58 pruebas del
repositorio/supervisor. Siguen callbacks tardíos/duplicados en Host real, margen
temporal y gates; la captura permanece cerrada.

[SRC127 — Callbacks en Host real](docs/execution/f02-07-host-callback.md) completa
RT-T3c.1: ocho perfiles verifican rechazo tardío, ejecución única y vida útil del
handoff; no cambia producción. Se conservan los dos órdenes del duplicado y el
rechazo de un peer ya cerrado. Pasan 228 ejecuciones nativas, ocho negativas del
checker y 58 pruebas de repositorio. Sigue medir el margen temporal del inventario;
gates y captura permanecen pendientes.

[SRC128 — Margen temporal del inventario](docs/execution/f02-07-inventory-timing.md)
completa RT-T3c.2: doce sesiones aceptan 36 respuestas y cierran limpiamente.
Los manifiestos consumen alrededor del 95 % del muestreo; el margen global
mínimo observado es 463 ms. Se conserva producción y se documentan límites de
la medida; pasan 20 pruebas propias y 58 de repositorio/supervisor. Sigue el mapa
de hechos/gates de JIT, caché, DMA y lifecycle; no se habilita captura.
