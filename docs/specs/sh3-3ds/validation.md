# Validación, trazabilidad y puertas de aceptación

Versión 1.0 · 2026-10-16. Fuente: PDF pp. 7-8, 13-30 y 32-34.

**Casos del producto completo: pendientes.** La fundación ya tiene pruebas sintéticas host y compilación 3DS, registradas en [evidencia](../../execution/foundation.md). No acreditan lógica original, rendimiento ni ejecución física.

## Protocolo común de evidencia

Cada ejecución registra: ID del caso y subcaso; criterio EARS exacto; build/commit y tipo de build; revisión/perfil del juego; modelo, launcher, firmware/entorno y configuración CPU; versiones de herramientas; estado inicial; entradas; resultado esperado; resultado observado; métricas; ubicación privada de evidencia; resumen publicable y responsable.

Estados permitidos: no ejecutado, bloqueado, fallido, aprobado y no aplicable con justificación de alcance. Una omisión obligatoria no se vuelve «no aplicable» sin una decisión de alcance. La misma evidencia puede cubrir varios criterios si enumera sus resultados por separado.

Para cada familia Vxx se crea un subcaso por criterio EARS y por variante normal/error indicada. Por ejemplo, `V01-RF01.03-hash-alterado`. Un resultado agregado de V01 no sustituye esos subcasos. Los rangos de la matriz inferior incluyen todos sus sufijos y fijan qué debe demostrarse, aunque la ejecución permanezca pendiente.

Niveles de evidencia:

| Nivel | Qué demuestra | Qué no demuestra por sí solo |
|---|---|---|
| Revisión estática | Contratos, cobertura, dependencias y condiciones documentadas | Ejecución correcta |
| Build limpio | Compilabilidad con versiones fijadas | Fidelidad ni comportamiento en consola |
| Unitarias/integración host | Casos sintéticos, dominio y fallos controlados | Costes de hardware ni todos los datos originales |
| Diferenciales privadas | Equivalencia del caso y edición observados | Toda la campaña o todas las revisiones |
| Emulador | Diagnóstico y reproducción en ese entorno | Certificación de rendimiento real |
| Hardware real | Comportamiento y métricas del perfil medido | Compatibilidad de combinaciones no probadas |
| Recorrido completo | Progreso de esa ruta sin atajos | Todas las ramas, dificultades o finales |

Severidades del PDF: P0 = pérdida/corrupción de datos o cierre general; P1 = bloqueo de progreso o sistema obligatorio roto; P2 = diferencia visible sin bloqueo; P3 = defecto menor. Ningún P0/P1 abierto se admite en el candidato final. Cada corrección de regresión conserva un caso reproductor.

## Perfiles de medición propuestos

Estas metas proceden del PDF, p. 13; siguen siendo provisionales. Los parámetros derivados del procedimiento se identifican expresamente. Se fijan antes de medir y se versionan al cambiar.

| Perfil | Procedimiento y criterio | Evidencia necesaria |
|---|---|---|
| PERF-FRAME | Tres recorridos de diez minutos por escena obligatoria. Al menos 99 % de frames alcanza 30 FPS; p99 de trabajo crítico < 33,33 ms; sin pausas inexplicadas > 100 ms fuera de transiciones registradas | Series temporales, tiempo de presentación, CPU/GPU y desglose por sistema; configuración y build de rendimiento |
| PERF-MARGEN | Meta de diseño aproximada de 26,7 ms, equivalente a reservar 20 % del intervalo nominal 1000/30 ms | Presupuesto por sistema y margen disponible; no sustituye PERF-FRAME |
| PERF-MEM | Pico_app ≤ 0,80 × B_app medido; pools lineal/GPU dentro de sus límites particulares | Pico durante coexistencia, buffers comprimidos/descomprimidos, texturas, esqueletos, audio y auxiliares; sin doble contabilidad |
| PERF-TRANS | Cien transiciones repetidas; crecimiento retenido tras calentamiento ≤ 1 MiB salvo causa aprobada | Serie por transición, línea base, medición final y causa de cualquier excepción |
| PERF-SAVE | Cien ciclos de guardado/carga y fallos inyectados en cada etapa | Comparación de estado y selección de generación válida en cada ciclo |
| PERF-EARLY | Treinta minutos de diagnóstico temprano; treinta minutos de navegación y treinta minutos de slice como recorridos distintos | Cierre limpio, estado final esperado y registros por etapa |
| PERF-STABILITY | Dos horas de estabilidad avanzada por perfil soportado, junto con corpus de cien transiciones | Ausencia de cierres, bloqueos y picos inexplicados; regresiones funcionales vigentes |
| PERF-AUDIO | Treinta minutos continuos con cero underruns y sin clipping no previsto | Contadores, loops, saturación, niveles y escucha comparativa |
| PERF-AV | Desajuste audiovisual absoluto < 100 ms | Eventos de sincronía definidos, timestamps y medición en secuencias representativas |
| PERF-LOAD | Carga fría y caliente separadas en SD identificada; máximo pendiente de F09/Q10 | Volumen, estado de caché, duración, perfil de SD y límite aprobado |

Precisiones derivadas propuestas para Q13:

1. Evaluar cada recorrido de diez minutos por separado; no ocultar un fallo promediándolo con otros recorridos o escenas.
2. Calcular p99 por rango más próximo: ordenar N muestras y usar la posición `ceil(0,99 × N)`, con posiciones desde 1. Conservar muestras y definición de trabajo crítico.
3. Definir frame que cumple como presentación en su vencimiento programado bajo el periodo de refresco observado y una tolerancia fijada antes de la prueba. Reportar periodo y tolerancia, sin reemplazar el objetivo por un promedio de FPS.
4. Marcar comienzo/fin de transiciones antes de ejecutar el caso. Excluirlas solo de la regla de pausas > 100 ms, según el texto fuente; reportar sus costes separadamente. Cualquier otra exclusión requiere una decisión explícita y un nuevo perfil.
5. Fijar calentamiento y estado quiescente comparable para memoria. Medir retención después de terminar trabajo GPU/audio pendiente. No descontar buffers residentes para mejorar artificialmente el pico.
6. Separar build de diagnóstico del de rendimiento; conservar instrumentación mínima suficiente. No sumar CPU y GPU cuando se solapan.

El corpus peor caso debe incluir máxima carga observada, transparencias, enemigos, cinemática, transición y audio simultáneo. Los límites geométricos y de entidades se obtienen de curvas medidas. El perfil CPU se vuelve a comprobar tras suspensión. No se activa `fast-math` global sin regresiones de comportamiento.

## Casos mínimos T01-T14 del PDF

| ID | Preparación/acción | Oráculo de aceptación | Nivel |
|---|---|---|---|
| T01 | Presentar revisión distinta, archivo alterado y mezcla de perfiles | Rechazo antes de aplicar offsets; causa identificada | Pipeline host |
| T02 | Paquete truncado, tamaño malicioso, overflow, solapamiento y referencias inválidas | Error controlado antes de lectura/reserva inválida; memoria acotada | Unitarias host con sanitizadores disponibles |
| T03 | Material con alpha y doble cara en corpus sintético y caso privado | Modo/material coherente con referencia; máscaras, caras y orden correctos | Host + capturas 3DS |
| T04 | Animación con raíz y entrada grabada | Un solo desplazamiento y sin deriva fuera de tolerancia | Diferencial + 3DS |
| T05 | Mismo recorrido con presentación deliberadamente lenta | Igualdad de estado discreto y velocidad/tiempos dentro del contrato | Host + 3DS |
| T06 | Entrar/salir cien veces, volver a estado comparable | Progreso preservado; memoria retenida dentro de PERF-TRANS | Integración + 3DS |
| T07 | Recoger dos veces objeto único; usar con requisito válido e inválido | Sin duplicación ni consumo incorrecto | Dominio host + circuito 3DS |
| T08 | Impacto coincidente con transición, ataque fallido y daño simultáneo | Daño único y estado final válido conforme a referencia | Diferencial + 3DS |
| T09 | Reproducir y saltar desde el mismo estado inicial | Flags y posición equivalentes donde corresponda | Host + narrativa 3DS |
| T10 | Interrumpir cada etapa de escritura usando copias de test | Selección de generación íntegra, sin destruir la única válida | Fallos host + consola controlada |
| T11 | Suspender con audio activo y reanudar | Colas, relojes y juego coherentes; sin salto temporal indebido | 3DS |
| T12 | SD ausente al inicio, memoria/almacenamiento insuficiente, lectura parcial | Mensaje, liberación parcial y estado recuperable | Host + 3DS controlado |
| T13 | Recorrer campaña sin debug | Final alcanzable para alcance declarado; al menos dos recorridos de ruta principal en QA | Hardware real |
| T14 | Motor nuevo con paquete/guardado de versión anterior | Compatibilidad/migración documentada o rechazo diagnosticado | Host + 3DS |

No se extrae la SD durante una escritura real ni se usan partidas únicas para fallos destructivos. Los fixtures malformados públicos son sintéticos. Los casos privados usan referencias identificadas sin incorporar los originales al repositorio.

## Matriz de trazabilidad EARS → diseño → tareas → prueba

Todos los criterios de cada grupo están incluidos por la columna «Criterios». Las fases remiten a las tareas con el mismo prefijo en [tasks.md](tasks.md). Las filas Vxx agregan procedimientos, no resultados aprobados.

| Caso | Criterios | Componentes | Fases/tareas | Demostración requerida además de T01-T14 |
|---|---|---|---|---|
| V01 | RF01.01-RF01.06 | C01, C06 | F00, F02, F03, F13 | Perfil completo, todos los archivos verificados, rechazo de variantes y trabajo sintético sin perfil; T01/T14 |
| V02 | RF02.01-RF02.08 | C01, C02 | F02, F03, F09 | Catálogo por entrada, desconocidos, dos ejecuciones limpias, conservación del intermedio y metadatos, recetas/pérdidas, reporte de dependencias y error ante faltante |
| V03 | RF03.01-RF03.05 | C02, C05 | F03, F05 | Landmarks, geometría, orientación, modos de material, niebla/luz/linterna, encuadre y captura comparable; T03 |
| V04 | RF04.01-RF04.06 | C04, C05, C12 | F04, F06 | Entrada/estado grabados, idle/caminar/correr/girar, raíz única, cambio de cámara y etiqueta de prototipo; T04/T05 |
| V05 | RF05.01-RF05.05 | C03, C04, C06 | F06, F07, F09 | Pared/esquina/puerta/pendiente, activación única, retorno, dependencia inválida y carga fallida recuperable; T06 |
| V06 | RF06.01-RF06.07 | C04, C10 | F04, F07 | Examinar/recoger/usar/equipar, rechazo, unicidad, puerta, orden de eventos y circuito clave/consumible/texto; T07 |
| V07 | RF07.01-RF07.06 | C04, C12 | F08, F11, F12 | Estados por enemigo/jefe soportado, impactos, reacción, recursos, muerte/continuar y registro de cambios de reglas; T08 |
| V08 | RF08.01-RF08.06 | C02, C07 | F01, F09, F10 | Metadatos y loops, prioridades/saturación, error NDSP, PERF-AUDIO y recuperación; T11 |
| V09 | RF09.01-RF09.08 | C02, C08, C10 | F10, F11 | Inventario de clases, timeline, timestamps, PERF-AV, final/salto, faltante, tildes/cadenas largas y omisiones declaradas; T09 |
| V10 | RF10.01-RF10.08 | C09, C12 | F07, F08, F13, F14 | Estado completo, dos generaciones, selección más reciente, corrupción/versiones, disco lleno y ninguna válida; PERF-SAVE; T10/T12/T14 |
| V11 | RF11.01-RF11.06 | C10 | F01, F06, F07, F10, F13 | Todas las acciones, combinaciones, reserva del sistema, combate sin táctil, legibilidad física y restauración/persistencia de opciones |
| V12 | RF12.01-RF12.05 | C03, C07-C10 | F01, F09, F10, F13 | Pausa/suspensión/reanudación/salida cruzadas con juego, combate, carga, audio, secuencia y guardado; cancelación/retoma; T11 |
| V13 | RF13.01-RF13.07 | C04, C13 | F00, F09, F11, F13 | Matriz completa, slice integrado, alpha, pruebas por unidad, dos recorridos, ramas, cobertura ponderada y puertas de expansión; T13 |
| V14 | RF14.01-RF14.06 | C11, C13 | F01, F13, F14 | Error con build/escena, saturación de log, símbolos, registro completo, anonimización y plantilla de incidencia |
| V15 | RNF01.01-RNF01.06 | C05, C07, C11 | F01, F05, F06, F09, F12 | PERF-FRAME/PERF-MARGEN, desglose sin doble suma y regresión de compilador/CPU tras suspensión |
| V16 | RNF02.01-RNF02.07 | C05-C07, C11 | F01, F05, F06, F09, F12 | B_app y pools medidos, PERF-MEM/PERF-TRANS, carga secuencial, liberación segura y límites sustentados; T06/T12 |
| V17 | RNF03.01-RNF03.06 | C03, C06, C11 | F01, F06, F09, F12, F13 | PERF-EARLY/PERF-STABILITY/PERF-LOAD, carga visible y errores de recursos; T12/T13 |
| V18 | RNF04.01-RNF04.04 | C03, C04, C12 | F01, F04 | Compilar dominio aislado, catálogo de procedencia/ABI, clasificación de dependencias y tres funciones diferenciales reales |
| V19 | RNF05.01-RNF05.05 | C01, C02, C13 | F00, F01, F02, F03, F14 | Inventario fijado con licencias, builds limpios, pasos manuales identificados, fallback host y actualización aislada |
| V20 | RNF06.01-RNF06.07 | C02, C06, C09, C12 | F02, F03, F07, F13 | Lectores adversariales, rutas confinadas, esquema endian/anchuras explícito, fixtures cruzados y overflow; T02/T14 |
| V21 | RNF07.01-RNF07.09 | C11-C13 | F00-F14 | Cierre por evidencia, stub/skip, regresión, P0/P1, builds host/3DS, cobertura por líneas/ramas, batería y artefactos identificables |
| V22 | RNF08.01-RNF08.07 | C01, C02, C13 | F00, F01, F13, F14 | Escaneo repo/CI/archivo final, datos externos/ISO local ignorada, rechazo de originales versionados, procedencia y exclusión de componentes pendientes; revisión antes de cualquier envío externo |
| V23 | RNF09.01-RNF09.04 | C04, C05, C08, C12 | F03-F12 | Diferenciales exactos/tolerancias por variable, registro de diferencias, ADR de umbrales y regresión de zonas afectadas |
| V24 | RNF10.01-RNF10.02 | C03, C09, C12 | F09, F13 | Conectividad deshabilitada: iniciar/jugar/guardar/cargar y comprobar ausencia de dependencia de cuenta/servidor/telemetría |
| V25 | RNF11.01-RNF11.09 | C03, C04, C12 | F01, F04, F05, F07, F09 | Revisión SOLID, límites de dependencias, sustitución de adaptadores, composición explícita y liberación por salida normal/error |
| V26 | RNF12.01-RNF12.05 | C11, C13 | F00, F01, F12-F14 | Matriz por combinación, `.3dsx` inicial, perfiles opcionales independientes, migración/reversión y exclusión de soporte no probado |

## Puertas F00-F14

**G00 aprobada el 2026-10-16** para identificación, alcance y custodia inicial; [evaluación por criterio](../../execution/f00-07-decisions.md). **G01-G14 pendientes**. Cada cierre necesita evidencia verificable; completar el registro de incógnitas no resuelve sus pruebas técnicas.

| Puerta | Entrada | Criterio de salida resumido del PDF | Evidencia |
|---|---|---|---|
| G00 | Copia autorizada para trabajo privado; investigación sintética libre de esa dependencia | Archivos identificados, revisión única, destino y exclusiones escritos | **Aprobada**: [perfil, manifiesto, matriz, alcance, custodia y registro de riesgos](../../execution/f00-07-decisions.md); no certifica consola ni distribución |
| G01 | G00 para originales; sintéticos pueden adelantarse | Build desde checkout limpio; geometría/controles/archivos/audio en consola treinta minutos; error con símbolos | [Build local F01.08](../../execution/f01-08-builds.md); [ensayo físico pendiente](../../compatibility/diagnostic-soak.md), diagnóstico y recursos del launcher |
| G02 | G00 y herramientas verificadas | Entradas extraídas/clasificadas/desconocidas explícitas; corpus slice localizado y extracción repetible | [Inventario ISO F02.01 completado](../../execution/f02-01-inventory.md); entradas internas, corpus y hashes de dos extracciones pendientes |
| G03 | G02 | Paquete repetible, pose/animación coherentes y ningún recurso crítico perdido silenciosamente | Intermedio, esquema binario, fixtures y reporte |
| G04 | G00 y corpus F02 | Lógica real en host y estrategia para cada dependencia crítica del slice | Movimiento, transición e inventario diferenciales; ABI/tick |
| G05 | G01 y G03 visual | Escena sin errores estructurales; memoria/frame en consola y margen medido para otros sistemas | Capturas y curvas CPU/GPU/memoria |
| G06 | G04 y G05 | Navegación treinta minutos sin penetración/atrapamiento/cambio de velocidad por FPS y estado final previsto | Recorrido, controles, colisiones, animación/cámara |
| G07 | G04 y G06 | Recoger, abrir puerta, cambiar zona, guardar, cerrar y continuar con estado esperado; rechazo sin corrupción | Circuito y guardado recuperable |
| G08 | G06 y estados de G07 | Combate, muerte y recuperación sin bloqueo/daño duplicado; estados equivalentes | Casos de combate y coste por entidad |
| G09 | G07, G08 y audio G01 | Slice treinta minutos y cien transiciones dentro de tolerancia; riesgos caracterizados, ningún éxito simulado | Informe de viabilidad: continuar, optimizar/repetir o cambiar alcance |
| G10 | G09 y corpus narrativo | Una secuencia por clase completa, sincronizada y con estado final correcto dentro de recursos | Timeline, salto/final, PERF-AV y buffers |
| G11 | G09, G10 y riesgos críticos resueltos | Cada unidad obligatoria probada y recorrido de principio a fin sin desbloqueos de debug | Matriz de campaña y recorrido alpha |
| G12 | G11; medición activa desde G01 | Corpus obligatorio cumple perfil aprobado; regresiones vigentes y sin picos/cierres inexplicados | Benchmarks por modelo/perfil y comparativas |
| G13 | G11 y G12 estabilizado | Cero P0/P1, pérdidas reproducibles de progreso o corrupción no controlada; defectos menores aceptados | Dos recorridos principales, ramas, recuperación y matriz |
| G14 | G13 y revisión de distribución | Candidato coincide con hashes/documentación; sin archivos inesperados ni soporte no probado | Build limpio final, revisión exacta del archivo y licencias |

No se confunde G09 con garantía de alcanzar todas las metas: ese gate exige que el informe declare si se cumplen y qué decisión se toma. Solo una decisión favorable con riesgos críticos resueltos habilita la expansión a F11. G04 + G05 determinan si existe una ruta técnica; G09 comprueba que los sistemas conviven.

## Hitos de comunicación

El contenido obligatorio se concreta en [scope.md v1.0](../../scope.md): primera alpha `alpha-es-normal-v1`, español, acción Normal y acertijos Normal. F00.04/Q03 cierran la definición; no constituyen un resultado aprobado de V13/T13 ni de una gate. Los informes identifican build y versión de alcance. G10/G11 se vuelven a comprobar para idiomas y variantes integrados después de esa alpha, antes de certificar M5.

| Hito del PDF | Puertas | Etiqueta y evidencia |
|---|---|---|
| M0 | G00-G01 | Entorno y edición: diagnóstico propio en consola y entradas identificadas |
| M1 | G02-G04 | Datos y lógica: paquete convertido y lógica fuera de PS2 |
| M2 | G05-G06 | Habitación jugable: animación, cámara y colisión |
| M3 | G07-G09 | Vertical slice: progreso, enemigo, audio, dos habitaciones y guardado |
| M4 | G10-G11 | Alpha: campaña declarada recorrible y diferencias registradas |
| M5 | G12-G14 | Candidato final: perfil medido, QA, compatibilidad y revisión de publicación |

No se fija fecha de port completo. Tras M1 y M3 podrá estimarse con esfuerzo observado de investigación, conversión, implementación y regresión.
