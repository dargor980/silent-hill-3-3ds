# Decisiones, incógnitas y riesgos

Versión 1.1 · 2026-10-16 · registro consolidado en F00.07. Fuente: PDF pp. 3-6, 11-14, 18-28 y 31-34.

Los responsables quedan asignados por función; una persona puede asumir varios roles, como permite F00.07 del PDF. Desarrollo asume las especialidades técnicas al ejecutar cada ticket; QA revisa su evidencia y el responsable de publicación revisa cada entrega. El operador de consola aporta mediciones físicas cuando se llegue a ese subcaso; el usuario decide cambios de alcance. Esto no declara personas adicionales ni pruebas ya realizadas. Una incógnita limita únicamente su trabajo dependiente; ningún dato pendiente se sustituye por una cifra, hash o resultado inventado.

## D01-D10 del PDF

| ID | Decisión de partida | Estado y condición de revisión |
|---|---|---|
| D01 | PS2 como origen de la ruta principal | Alcance solicitado; cambiar a PC exige decisión expresa |
| D02 | New Nintendo 2DS XL | Modelo confirmado por el usuario; ejecución física pendiente |
| D03 | C++17 nuevo y C para interoperabilidad | Compilado para host y ARM en la fundación; coste real del juego pendiente |
| D04 | Python para herramientas offline | Adoptado para inspección y QA host; versiones/hashes fijados y [licencias revisadas inicialmente](../../compatibility/licenses.md) |
| D05 | libctru, citro3d y citro2d | Adoptados en diagnóstico sintético con SDK fijado; build comprobado y prueba física pendiente |
| D06 | Sin estereoscopía inicial | Alcance inicial; reevaluar solo tras cumplir rendimiento |
| D07 | 30 FPS de presentación | Meta provisional; no determina el tick de simulación |
| D08 | `.3dsx` primero, CIA posterior opcional | Provisional; medir y validar cada launcher por separado |
| D09 | Paquetes por habitación/sector | Propuesta; tamaño definido por costes reales |
| D10 | Builds públicos sintéticos y originales privados | Restricción documental; revisar cada componente antes de distribuir |

Decisión de ejecución 2026-10-16: perfil europeo independiente según la [comparación de edición](../../compatibility/edition-comparison.md). La ISO permanece en `binaries` por indicación del usuario, con custodia según [política de datos](../../private-data.md); se actualiza RNF08.01.

## Registro de incógnitas

Estado al cierre de F00.07: **2 resueltas dentro de su alcance (Q02/Q03), 4 parciales (Q01/Q04/Q13/Q14) y 8 abiertas (Q05-Q12)**. Completar este registro no resuelve automáticamente las incógnitas. [Informe F00.07 y revisión de G00](../../execution/f00-07-decisions.md).

«Resuelta» exige evidencia dentro del alcance indicado. «Parcial» distingue un resultado existente de lo que falta. «Abierta» identifica trabajo todavía sin evidencia de cierre. Si una ejecución concreta no puede continuar, su ticket se marca bloqueado con causa; no se bloquea todo el proyecto. Los casos de prueba mantienen los estados y niveles de [validation.md](validation.md).

Antes de cerrar una Q, el responsable aporta resultado esperado/observado, perfil, build o manifiesto de fuentes, comando/protocolo y ubicación de evidencia. QA contrasta el criterio y actualiza Q/ticket/puerta por separado. Una diferencia, fallo o dato omitido conserva la Q abierta. Cambiar edición, herramienta, hardware, formato o alcance reabre los subcasos afectados y requiere repetir su evidencia. Las fechas no sustituyen aceptación.

<a id="q01"></a>

### Q01 — Entorno físico y compatibilidad

- **Estado:** parcial. Modelo New Nintendo 2DS XL y Homebrew Launcher confirmados; FBI es instalador para una ruta CIA futura.
- **Responsable:** desarrollo de plataforma; colaboración del operador de consola para medición y de QA para aceptación.
- **Evidencia disponible:** [target.json](../../compatibility/target.json) registra confirmaciones; firmware, versiones y CPU siguen `null`, y ejecución física `not_tested`. F00.01 cerró la selección del destino.
- **Riesgo:** anunciar soporte por un build host o por confundir FBI con el launcher del `.3dsx`.
- **Criterio de cierre:** registrar entorno/CPU/build del perfil probado y verificar arranque, gráficos, controles, archivos, tono, ciclo de vida y error simbolizado durante el diagnóstico de treinta minutos. Matriz con resultado por combinación; CIA/Old necesitan evidencia propia si se adoptan.
- **Siguiente acción y dependencias:** preparar diagnóstico en [F01.02](tasks/F01.md#f0102), completar F01.03-F01.08 y contrastar compatibilidad de campaña en [F13.01](tasks/F13.md#f1301). Limita G01 y cualquier anuncio de soporte; no mantiene G00 abierta.
- **Verificación:** V26/V12/V14 y PERF-EARLY en hardware; emulador y host registrados por separado. RNF12.01/RNF12.05 siguen pendientes para compatibilidad real.

<a id="q02"></a>

### Q02 — Edición de origen

- **Estado:** resuelta para identificación de bytes y metadatos de edición; no para formatos internos ni ejecución.
- **Responsable:** investigador de edición, con revisión QA.
- **Evidencia disponible:** [F00.02](../../execution/f00-02-edition-identification.md), [perfil separado](../../compatibility/edition-comparison.md) y manifiesto privado: Europa/PAL, SLES-51434, 1.02, 113 archivos, en/fr/de/es/it catalogados.
- **Riesgo:** mezclar revisiones o trasladar direcciones/offsets del candidato NTSC-U a Europa.
- **Criterio de cierre:** coincidencia documentada de imagen completa con catálogo y manifiesto de archivos, más perfil europeo independiente. Cumplido por F00.02/F00.03; nombre de ISO y `VER` aislados no bastan.
- **Siguiente acción y dependencias:** conservar el perfil como entrada de [F02.01](tasks/F02.md#f0201) y F04.01; comprobar identidad antes de nuevas operaciones. Cambio de bytes/perfil reabre identificación. No bloquea G00; las entradas internas siguen en Q05/G02.
- **Verificación:** V01/T01; la comparación completa es evidencia histórica de F00.02. F00.07 solo comprueba coherencia del JSON con su informe, sin volver a calcular hashes de la ISO.

<a id="q03"></a>

### Q03 — Contenido por hito

- **Estado:** resuelta como definición de alcance v1.0, no como cobertura jugable.
- **Responsable:** desarrollo mantiene el desglose; el usuario decide cambios de producto y QA verifica aceptación.
- **Evidencia disponible:** selección expresa de español y acción Normal/acertijos Normal; [scope.md](../../scope.md), categorías SC01-SC15 y [F00.04](../../execution/f00-04-scope.md).
- **Riesgo:** convertir un aplazamiento de idiomas, ramas o extras en omisión definitiva, o presentar un visor como campaña portada.
- **Criterio de cierre:** idioma/dificultad de alpha y obligaciones por M0-M5 definidos, con exclusiones visibles. Cumplido para esa definición; todas las variantes presentes en la edición siguen en M5.
- **Siguiente acción y dependencias:** identificar unidades reales en [F02.07](tasks/F02.md#f0207) y [F11.01](tasks/F11.md#f1101); registrar versión, motivo e impacto antes de cambiar alcance. No bloquea G00; no cierra G11/G13.
- **Verificación:** V13/T13 en F11/F13, incluidos recorridos y variantes. Nombres/cantidades todavía desconocidos no se inventan para completar la matriz.

<a id="q04"></a>

### Q04 — Herramientas y procedencia

- **Estado:** parcial. Entorno sintético fijado e inventario inicial completado; adopción de candidatos y verificaciones específicas pendientes.
- **Responsable:** mantenedor de herramientas; investigador de cada formato aporta compatibilidad y QA revisa reproducibilidad.
- **Evidencia disponible:** [toolchain](../../compatibility/toolchain.md), locks/digest/commits, [F00.06](../../execution/f00-06-provenance.md) y pendientes LIC01-LIC09 en la [matriz de licencias](../../compatibility/licenses.md).
- **Riesgo:** adoptar una herramienta sin procedencia o cobertura comprobadas; confundir etiqueta del paquete con licencia efectiva.
- **Criterio de cierre:** por componente adoptado, fijar identidad, entorno, términos y resultado normal/error sobre fixtures; resolver los pendientes aplicables al uso previsto. Q14 evalúa después el artefacto distribuido, incluso con herramientas ya comprobadas.
- **Siguiente acción y dependencias:** [F01.01 completada](../../execution/f01-01-toolchain.md) para ejemplo oficial reproducible, C++17 ARM y build propio; continuar F01.02 y verificar candidatos/formatos en F03.01/F04.01; [F02.02](../../execution/f02-02-mfa-candidate.md) seleccionó sondeo propio, manteniendo LIC04 abierto para el candidato GUI. Cada LIC limita el uso indicado en su fila; no impide cerrar el inventario G00 ni ejecutar pruebas sintéticas independientes.
- **Verificación:** V19/V22, build limpio, caso de dependencia ausente y comparación de salidas. No cerrar compatibilidad por leer una licencia ni presentar CI remota sin ejecutarla.

<a id="q05"></a>

### Q05 — Formatos y corpus

- **Estado:** abierta. F02.04 completó dos catálogos idénticos de 1740 recursos en 61 MFA, con IDs/offsets/SHA-256; tipos y dependencias semánticas sin inspeccionar. XBG0 mantiene codificación no resuelta. F02.05 verificó dos extracciones del conjunto aceptado y F02.06 amplió robustez con 142 casos adversos; F02.07 completó contrato/lector/inventario de candidatos, con dos manifiestos idénticos. La semántica y el corpus siguen pendientes.
- **Responsable:** investigador de assets; responsable del pipeline mantiene recetas y QA valida errores/repetibilidad.
- **Evidencia disponible:** perfil de 113 archivos y `extractor_version=none-inspection-only-v1`; [dos catálogos F02.01 idénticos](../../execution/f02-01-inventory.md), 12 cabeceras ELF, 35 candidatos AFS, una configuración y 65 desconocidos; [política de ubicación externa](../../private-data.md). [F02.04](../../execution/f02-04-asset-catalog.md) verifica 1.562.367.840 bytes de recursos sin exportarlos. [F02.05](../../execution/f02-05-repeatable-extraction.md) exportó ese conjunto dos veces en una raíz externa indicada por el usuario; listas/tamaños/hashes iguales al catálogo. Ubicación registrada en evidencia privada.
- **Riesgo:** perder entradas, huesos, alpha o metadatos sin detectarlo; identificar contenedores por extensión o asumir soporte europeo.
- **Criterio de cierre:** catálogo por entrada con identidad/dependencias/desconocidos, corpus del slice localizado, cobertura por variante y dos extracciones coincidentes; decodificación conserva metadatos requeridos con casos adversos.
- **Siguiente acción y dependencias:** [inventario inicial F02.07 completado](../../execution/f02-07-slice-corpus.md); continuar `F02.07/camera-runtime-capture-eu` tras [completar plan/contrato/validador](../../execution/f02-07-camera-observation.md), con 1435 pruebas y PCSX2 v2.8.2 instalado/perfil comprobado. [BIOS principal configurada y arranque comprobado por logs](../../execution/f02-07-ps2-boot.md); validar depurador, fijar entorno definitivo y registrar A/B según el protocolo privado. A recibe GPR4 desde GPR6 en el slot; conservación de GPR16 en B sin demostrar. No hay captura real ni identidad del recurso probada. El [sondeo de cámara](../../execution/f02-07-camera-probe.md) conserva 285 coincidencias numéricas, colas opacas y discrepancias de rango en 154 archivos. Exigir contrato/evidencia antes de clasificar o relacionar salas; después continuar formatos, dependencias y corpus, y F03.01/F03.02; nuevas exportaciones requieren fuente/herramienta verificadas y destino privado explícito. Limita G02/G03 y selección definitiva del slice.
- **Verificación:** V02/V20 y T02 con fixtures propios; evidencia privada ligada al perfil para casos reales. Un desconocido se registra, no se convierte en éxito.

<a id="q06"></a>

### Q06 — Lógica, ABI y tiempo de simulación

- **Estado:** abierta. No hay lógica real de SH3 portada ni tick observado.
- **Responsable:** investigador de comportamiento; desarrollo del dominio implementa contratos y QA compara estados.
- **Evidencia disponible:** arquitectura portable y [separación regional](../../compatibility/edition-comparison.md); el diagnóstico sintético no es evidencia de lógica del juego.
- **Riesgo:** conservar dependencias de PS2, duplicar movimiento raíz o cambiar daño/eventos al bajar FPS.
- **Criterio de cierre:** funciones y overlays identificados por edición; ABI/entradas/salidas/orden/tick documentados; movimiento, transición e inventario reales comparados en host y estrategia viable para cada dependencia crítica. Tolerancias por variable justificadas antes de aceptar diferencias.
- **Siguiente acción y dependencias:** [F04.01](tasks/F04.md#f0401)-F04.09, con corpus F02 y herramientas Q04. Limita G04 y comportamiento definitivo de F06-F08; 30 FPS de presentación no fija el tick PAL.
- **Verificación:** V18/V23, T04/T05 y diferenciales por variable; no usar precisión reducida global para ocultar divergencias.

<a id="q07"></a>

### Q07 — Contrato binario SH3P

- **Estado:** abierta. El diseño lógico no especifica aún bytes ni lector de producción.
- **Responsable:** responsable del pipeline; desarrollo de streaming implementa lector y QA aporta entradas adversas.
- **Evidencia disponible:** [modelos lógicos](design.md) y desglose de [F03.05](tasks/F03.md#f0305); no existe formato original SH3P descubierto.
- **Riesgo:** desacuerdo escritor/lector, overflow, reserva no acotada o pérdida silenciosa de referencias.
- **Criterio de cierre:** especificación versionada de anchuras, endian, offsets, integridad, compresión y límites; fixtures conocidos; escritor determinista y lector independiente que rechaza truncados, solapamientos y referencias inválidas antes de reservar/leer fuera de límites.
- **Siguiente acción y dependencias:** F03.03/F03.04 aportan convenciones/intermedio; F03.05 se ejecuta en contrato, escritor y lector adversarial; F03.07 verifica errores. Limita lector definitivo y G03; límites de memoria dependen de Q08.
- **Verificación:** V20/T02/T14, comparación byte a byte y sanitizadores host; builds 3DS no sustituyen casos adversos.

<a id="q08"></a>

### Q08 — Recursos y presupuesto medido

- **Estado:** abierta. No hay B_app, pools ni configuración CPU medidos en la consola objetivo.
- **Responsable:** responsable de rendimiento, con operador de consola y QA.
- **Evidencia disponible:** [perfiles propuestos](validation.md) y diagnóstico compilado; la RAM nominal no se usa como memoria disponible.
- **Riesgo:** agotar memoria en transiciones o consumir el margen de CPU/GPU antes de integrar lógica/audio.
- **Criterio de cierre:** medir B_app y pools por launcher/CPU, registrar picos con coexistencia y curvas de coste del corpus; fijar presupuestos por sistema y comprobarlos al suspender/reanudar. Toda cifra ligada a build, escenario y método Q13.
- **Siguiente acción y dependencias:** [F01.06](tasks/F01.md#f0106) incorpora consultas observables sin inferir B_app; medición física pendiente, F05.07/F09.04/F09.07 amplían carga y F12.06/F12.07 certifican. Requiere entorno Q01 y protocolo Q13; limita G05/G09/G12.
- **Verificación:** V15/V16, PERF-MEM/PERF-TRANS y T06. Un pool desconocido queda sin dato, nunca como cero ni como toda la RAM libre.

<a id="q09"></a>

### Q09 — Presentación y coste gráfico

- **Estado:** abierta. Encuadre, skinning, materiales y tolerancias visuales finales pendientes.
- **Responsable:** responsable gráfico; QA compara imágenes y rendimiento.
- **Evidencia disponible:** contrato visual propuesto; el patrón sintético solo prueba la ruta de dibujo al nivel del build.
- **Riesgo:** deformar encuadre/animación, perder alpha o saturar GPU por transparencias.
- **Criterio de cierre:** decisión de encuadre con capturas comparables y diferencias explícitas; políticas de material y skinning evaluadas en corpus representativo con costes y límites sustentados en hardware.
- **Siguiente acción y dependencias:** [F05.03](tasks/F05.md#f0503), F05.04-F05.08 y F06.03; requiere convenciones Q07, corpus Q05 y presupuestos Q08. Limita G05/G06 y aceptación visual posterior.
- **Verificación:** V03/V04/V23, T03/T04 y comparaciones del mismo estado/cámara; una imagen atractiva no demuestra fidelidad.

<a id="q10"></a>

### Q10 — Audio, vídeo y carga

- **Estado:** abierta. Codec, buffers, reloj maestro y límites de carga sin seleccionar ni medir.
- **Responsable:** responsable multimedia, con rendimiento y QA.
- **Evidencia disponible:** tono PCM propio en el diagnóstico y metas PERF-AUDIO/PERF-AV/PERF-LOAD; no se ha validado streaming de recursos del juego.
- **Riesgo:** underruns, desfase, saturación y cargas sin límite verificable; dependencia de conversión sin revisión.
- **Criterio de cierre:** perfil de codecs/configuración/licencias, loops/prioridades/buffers y reloj definidos; estrés representativo, sincronía, suspensión/salto y carga fría/caliente medidos en SD identificada, con máximos fijados antes de aceptación.
- **Siguiente acción y dependencias:** [F09.01](tasks/F09.md#f0901), F09.02/F09.06/F09.07 y F10.03-F10.06; requiere Q04/Q05/Q08/Q13. Limita G09/G10 y certificación audiovisual.
- **Verificación:** V08/V09/V12, T09/T11 y perfiles AUDIO/AV/LOAD; conservar fallos y no excluir pausas después de observar el resultado.

<a id="q11"></a>

### Q11 — Guardado y recuperación

- **Estado:** abierta. Esquema persistente y migraciones sin implementar.
- **Responsable:** responsable de persistencia; QA prepara copias de test y fallos controlados.
- **Evidencia disponible:** contrato lógico de dos generaciones en [diseño](design.md); no hay prueba de recuperación de progreso real.
- **Riesgo:** perder la única generación válida o cargar un estado incompatible tras actualizar.
- **Criterio de cierre:** esquema versionado de estado completo, integridad y selección de generación; interrupción por etapa, datos corruptos/versiones anteriores y disco lleno recuperan la última generación válida; migración/reversión documentadas y probadas.
- **Siguiente acción y dependencias:** [F07.06](tasks/F07.md#f0706)/F07.07, F13.03/F13.04 y F14.07; requiere estado/orden de eventos Q06 y esquema Q07 cuando se compartan identificadores de paquetes. Limita G07/G13/G14.
- **Verificación:** V10/V20, T10/T14 y PERF-SAVE. Solo copias de test; no retirar SD durante una escritura real ni usar partidas únicas.

<a id="q12"></a>

### Q12 — Pantallas, controles y texto

- **Estado:** abierta. Español inicial confirmado; mapeo final, fuente y legibilidad sin validar.
- **Responsable:** responsable de UI; QA y operador de consola verifican tamaño físico y acciones.
- **Evidencia disponible:** [alcance español Normal/Normal](../../scope.md) y entrada A/START del diagnóstico; no constituye mapeo del juego.
- **Riesgo:** acción obligatoria inaccesible, dependencia de táctil en combate o texto truncado/ilegible.
- **Criterio de cierre:** reparto de pantallas y mapa completo reasignable, acciones reservadas respetadas, combate sin táctil obligatorio, opciones restaurables y fuente con tildes/signos/cadenas largas probada en tamaño real; repetir para idiomas incorporados.
- **Siguiente acción y dependencias:** [F06.06](tasks/F06.md#f0606)/F06.07, F10.07 y F13.07; requiere Q01/Q03 y corpus de cadenas Q05. Limita G06/G10/G13.
- **Verificación:** V11/V09/V26; evidencia física por acción y cadena representativa, no solo render host.

<a id="q13"></a>

### Q13 — Protocolo de medición y peor caso

- **Estado:** parcial. [Protocolo inicial diagnostic-v1](../../compatibility/resource-contract.md) e instrumentación F01.06 disponibles; protocolo definitivo y corpus real pendientes.
- **Responsable:** QA/rendimiento; responsables de subsistema aportan contadores y escenarios.
- **Evidencia disponible:** [PERF y precisiones derivadas](validation.md), pruebas host de log en [fundación](../../execution/foundation.md). Los valores propuestos no son resultados medidos ni parámetros aprobados definitivamente.
- **Riesgo:** promediar fallos, ajustar exclusiones después de medir o perder evidencia por saturación de logs.
- **Criterio de cierre:** fijar por versión corpus, muestreo, percentil, tolerancia de refresco, calentamiento, estado comparable, fronteras de transición y política de logs antes de evaluar. Separar diagnóstico/rendimiento y CPU/GPU; documentar resultados por recorrido.
- **Siguiente acción y dependencias:** [F01.06](tasks/F01.md#f0106) implementa instrumentación inicial con ventana/p95 y estados desconocidos explícitos; F09.06/F09.07 caracterizan integración; F12.01/F12.02 fijan corpus final y builds. Q05/Q08 aportan escenarios y capacidad real. Limita evidencia definitiva de G09/G12; no impide instrumentación temprana.
- **Verificación:** V14/V15/V16, PERF-FRAME/MEM/TRANS; saturación/rotación del log y conservación de muestras, sin usar el promedio como sustituto del percentil.

<a id="q14"></a>

### Q14 — Artefactos que se comparten

- **Estado:** parcial. Procedencia inicial revisada; ningún artefacto concreto queda aprobado para publicación por ese inventario.
- **Responsable:** responsable de publicación; mantenedor aporta fuentes/avisos y QA coteja contenido/checksums.
- **Evidencia disponible:** [F00.06](../../execution/f00-06-provenance.md), LIC01-LIC09 y controles de [custodia](../../private-data.md); CI remota sin ejecutar.
- **Riesgo:** distribuir originales, dependencias o código recuperado con revisión pendiente, o anunciar soporte no probado.
- **Criterio de cierre:** para cada entrega, inventario exacto de código/objetos/libs/recursos y procedencia, términos/avisos/fuentes correspondientes, exclusión de pendientes y privados, hashes y documentación consistentes con el archivo final. Una nueva entrega requiere revisión propia.
- **Siguiente acción y dependencias:** LIC07 antes de compartir diagnósticos/artefactos CI; [F14.03](tasks/F14.md#f1403)/F14.04/F14.09 para el candidato final; LIC08 si se incluyen herramientas host. Depende de Q04 y de la evidencia que se anuncie. Limita publicación y G14; no G00 ni desarrollo local.
- **Verificación:** V22/V26, revisión del archivo exacto y de procedencia; el escaneo por extensión no reconoce todo original renombrado. Preparar candidato no ejecuta su publicación.

## Orden de resolución

[F01.01](../../execution/f01-01-toolchain.md) está completada para compilación local. F01.02-F01.08 tienen implementación/pruebas locales y conservan sus subcasos físicos pendientes. [F01.08](../../execution/f01-08-builds.md) aporta gates de build y el [ensayo prolongado](../../compatibility/diagnostic-soak.md); G01 sigue abierto. [F02.01](../../execution/f02-01-inventory.md) completó el inventario ISO. [F02.02](../../execution/f02-02-mfa-candidate.md) completó la evaluación del candidato y un sondeo propio D8: dos candidatos estructurales y 60 desconocidos, sin extracción. [F02.03](../../execution/f02-03-container-variants.md) amplió la estructura verificada a 61 contenedores/1740 entradas, con 493 pruebas. XBG0 queda desconocido con diagnóstico de codificación. La siguiente tarea es [F02.04](tasks/F02.md#f0204), catálogo interno; extracción real pendiente de raíz externa y herramienta verificada.

F02 puede avanzar al contar con G00 y herramientas verificadas para la operación; la raíz privada externa debe configurarse antes de escribir derivados. No se adelanta la expansión de campaña a G04/G05/G09 favorables. Ningún Q futuro se considera resuelto para cerrar F00: G00 evalúa identidad, destino, alcance y custodia; G01 evalúa ejecución del diagnóstico.

## Riesgos y respuesta

| Riesgo del PDF | Señal comprobable | Respuesta y puerta afectada | Incógnitas responsables |
|---|---|---|---|
| Lógica incompleta o dependiente de PS2 | Funciones críticas siguen requiriendo ensamblador/hardware | Clasificar, recuperar/adaptar o reimplementar con comparación; G04 | Q06 |
| Herramienta incompleta | Faltan huesos, alpha, animación o metadatos | Fixture y decodificador específico; G03 | Q04, Q05 |
| CPU insuficiente | Slice no deja margen para lógica y entidades | Medir por subsistema y revisar representación antes de campaña; G09 | Q08, Q13 |
| Transparencias costosas | Alto coste GPU con poca geometría | Medir overdraw, orden y pasadas por material; G05/G12 | Q09, Q08 |
| Pico de memoria | OOM solo al cambiar sector | Medir coexistencia y usar carga secuencial; G09 | Q08, Q10 |
| Deriva temporal o numérica | Daño/eventos/cámara divergen | Comparaciones por variable y revisión del orden/tick; G04/G12 | Q06, Q13 |
| Audio/video inestable | Underruns o desfase creciente | Revisar buffers, reloj y codec con benchmarks; G09/G10 | Q10 |
| Conversión manual irrepetible | Hashes distintos sin cambio de entradas | Versionar recetas y detener expansión; G03/G11 | Q05, Q07 |
| Revisiones mezcladas | IDs u offsets inconsistentes entre archivos | Perfil único verificado; G00/G02 | Q02 |
| Distribución sin revisión | Archivos inesperados o procedencia pendiente | Excluir componente y revisar candidato exacto; G14 | Q14, Q04 |
| Alcance subestimado | Visor presentado como port completo | Aplicar etiquetas de madurez y matriz de contenido; G11/G14 | Q03, Q12 |
| Actualización de dependencia rompe el entorno | Fallo sin cambio del proyecto | Fijar versiones y probar actualización aislada; G01/G14 | Q04, Q01, Q11 |

La contingencia de no alcanzar 30 FPS es informar la medición, proponer un perfil/alcance distinto y repetir la validación. Reducir enemigos, omitir secuencias o alterar dificultad no se clasifica como una optimización visual inocua.

## Plantilla de ADR

```text
ID y título:
Estado: propuesto | aprobado | reemplazado
Fecha, responsable y requisitos afectados:
Contexto y evidencia:
Opciones consideradas y costes:
Decisión y fundamento:
Consecuencias para fidelidad, datos y rendimiento:
Condición de revisión:
Pruebas/benchmarks y build/commit:
Decisión anterior reemplazada, si existe:
```

## Referencias externas conservadas

Referencias S01-S20 del PDF, p. 35. La transformación inicial a EARS conserva esas referencias. F00.06 añadió la [revisión de procedencia](../../compatibility/licenses.md), que distingue componentes ya usados, candidatos y documentos consultados. Solo las versiones/identidades expresamente fijadas se consideran adoptadas; una referencia externa no acredita compatibilidad funcional.

| ID | Referencia |
|---|---|
| S01 | [memory-of-alessa](https://github.com/dreamingmoths/memory-of-alessa) |
| S02 | [Proceso de contribución de memory-of-alessa](https://github.com/dreamingmoths/memory-of-alessa/blob/main/docs/contributing.md) |
| S03 | [devkitPro: 3ds-examples](https://github.com/devkitPro/3ds-examples) |
| S04 | [libctru](https://github.com/devkitPro/libctru) |
| S05 | [citro3d](https://github.com/devkitPro/citro3d) |
| S06 | [citro2d](https://github.com/devkitPro/citro2d) |
| S07 | [tex3ds](https://github.com/devkitPro/tex3ds) |
| S08 | [picasso](https://github.com/devkitPro/picasso) |
| S09 | [libctru: ndsp.h](https://github.com/devkitPro/libctru/blob/master/libctru/include/3ds/ndsp/ndsp.h) |
| S10 | [ghidra-emotionengine-reloaded](https://github.com/chaoticgd/ghidra-emotionengine-reloaded) |
| S11 | [Depurador de PCSX2](https://pcsx2.net/docs/advanced/debugger/) |
| S12 | [MFA Tool for Silent Hill 3 PS2](https://github.com/RayneDuarte/MFA-Tool-for-Silent-Hill-3-PS2-) |
| S13 | [Sparagas: Silent-Hill](https://github.com/Sparagas/Silent-Hill) |
| S14 | [Azahar](https://azahar-emu.org/) |
| S15 | [Luma3DS: Rosalina](https://github.com/LumaTeam/Luma3DS/wiki/Rosalina) |
| S16 | [3dbrew: NCCH Extended Header](https://3dbrew.org/wiki/NCCH/Extended_Header) |
| S17 | [sh3-nx](https://github.com/cutarev/sh3-nx) |
| S18 | [PS2Recomp](https://github.com/ran-j/PS2Recomp) |
| S19 | [Blender: Decimate](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/decimate.html) |
| S20 | [FFmpeg](https://ffmpeg.org/ffmpeg.html) |
